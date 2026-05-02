from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.api.routes.stocktrim import client

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
        "locationCode": str(data.id),       # unique key — StockTrim upserts on this
        "locationName": data.name,
        "externalId": str(data.id),         # store SOS id for traceability
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/create-location")
async def create_location(data: SOSLocationRequest):
    """
    Upsert a single SOS location into StockTrim.
    StockTrim matches on locationCode — re-syncing the same location
    will update rather than duplicate.
    """
    try:
        payload = map_sos_location_to_stocktrim(data)
        result = await client.create_resource(
            method="POST",
            endpoint="Locations",
            payload=payload,
        )
        return {
            "location_id": data.id,
            "location_name": data.name,
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-sync")
async def bulk_sync_locations(locations: List[SOSLocationRequest]):
    """
    Bulk upsert all SOS locations into StockTrim.
    Archived locations are skipped automatically.
    Use for initial setup or full re-sync.
    """
    try:
        results = []
        skipped = []

        for location in locations:
            if location.archived:
                skipped.append({
                    "location_id": location.id,
                    "location_name": location.name,
                })
                continue

            payload = map_sos_location_to_stocktrim(location)
            result = await client.create_resource(
                method="POST",
                endpoint="Locations",
                payload=payload,
            )
            results.append({
                "location_id": location.id,
                "location_name": location.name,
                "result": result,
            })

        return {
            "total_synced": len(results),
            "total_skipped_archived": len(skipped),
            "results": results,
            "skipped": skipped,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))