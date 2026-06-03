import asyncio
import logging

from typing import Any, Optional

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from tenacity import RetryError

from app.api.routes.stocktrim import client
from app.sos_stocktrim_sync.utils import api_get
from app.logging_config import get_jsonl_logger, build_jsonl_entry

router = APIRouter(prefix="/location", tags=["location"])


# ---------------------------------------------------------------------------
# SOS Inventory Models
# ---------------------------------------------------------------------------

class SOSLocationRequest(BaseModel):
    """
    SOS Inventory location record.
    SOS does not expose a dedicated /location endpoint in the public API —
    location data comes embedded in items, POs, and sales orders.

    Fields:
        id       → StockTrim locationCode + externalId  (both use SOS id as string)
        name     → StockTrim locationName
        archived → used to skip archived locations in bulk sync
    """
    id: int
    name: str
    archived: Optional[bool] = False


# ---------------------------------------------------------------------------
# Mapper
#
# SOS field   →  StockTrim field
# ────────────────────────────────
# id          →  locationCode   (SOS id as string — unique key StockTrim matches on)
# name        →  locationName
# id          →  externalId     (store SOS id for traceability / re-sync)
#
# Note: StockTrim does NOT support bin locations.
#       Only warehouse/store level locations are mapped.
# ---------------------------------------------------------------------------

def map_sos_location_to_stocktrim(data: SOSLocationRequest) -> dict:
    return {
        # unique key — StockTrim upserts on this
        "locationCode": str(data.id),
        "locationName": data.name,
        "externalId": str(data.id),         # store SOS id for traceability
    }


STOCKTRIM_CONCURRENCY = 10
logger = logging.getLogger(__name__)
jsonl_logger = get_jsonl_logger()

async def sync_location_to_stocktrim(locations: dict[str, Any | list]):
    semaphore = asyncio.Semaphore(STOCKTRIM_CONCURRENCY)

    async def process_location(location):
        verified_location = SOSLocationRequest.model_validate(location)
        payload = map_sos_location_to_stocktrim(verified_location)

        try:
            async with semaphore:
                result = await client.create_resource(
                    method="POST",
                    endpoint="Locations",
                    # ⚠️ no list here (as per your API design)
                    payload=payload,
                )

            return {
                "status": "success",
                "result": result,
            }

        except RetryError as re:
            cause = re.last_attempt.exception()
            error_msg = f"{type(cause).__name__}: {cause}"
            logger.error(
                f"Failed to sync location to StockTrim after retries: {error_msg}",
                extra={
                    "error": error_msg,
                    "payload": payload,
                    "location_code": location.get("locationCode"),
                },
            )

            return {
                "status": "failed",
                "error": error_msg,
                "payload": payload,
                "location_code": location.get("locationCode"),
            }

        except Exception as e:
            logger.error(
                f"Failed to sync location to StockTrim: {str(e)}",
                extra={
                    "error": str(e),
                    "payload": payload,
                    "location_code": location.get("locationCode"),
                },
            )

            return {
                "status": "failed",
                "error": str(e),
                "payload": payload,
                "location_code": location.get("locationCode"),
            }

    tasks = [process_location(l) for l in locations["data"]]

    results = await asyncio.gather(*tasks)

    success = sum(1 for r in results if r["status"] == "success")
    failed_results = [r for r in results if r["status"] == "failed"]
    failed = len(failed_results)
    failed_details = [
        {
            "location_code": r["location_code"],
            "reason": r["error"],
        }
        for r in failed_results
    ]

    jsonl_logger.info(
        build_jsonl_entry(
            action_type=f"Sync locations from SOS Inventory to StockTrim",
            action_variant=f"sync-locations-from-sos-to-stocktrim",
            status="Info",
            message=f"Synced {success} locations successfully, {failed} failed.",
            failed_details=failed_details if failed_details else None,
        )
    )

    return {
        "success": success,
        "failed": failed,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/create-location")
async def create_location():
    """
    Upsert SOS locations into StockTrim concurrently.
    """

    try:
        locations = await api_get("/api/v2/location")

        sync_result = await sync_location_to_stocktrim(locations)

        return {
            "location_sync_result": sync_result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
