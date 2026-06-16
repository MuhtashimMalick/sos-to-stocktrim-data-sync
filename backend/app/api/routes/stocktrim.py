import asyncio
import httpx
import json
import logging

from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
from typing import Dict, Any, Optional

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.sos_stocktrim_sync.utils import api_get
from app.logging_config import get_jsonl_logger, build_jsonl_entry
from app.utils import generate_scan_complete_email, send_email

router = APIRouter(prefix="/stocktrim", tags=["stocktrim"])


class StockTrimClient:
    def __init__(self, auth_id: str, auth_signature: str, base_url: str):
        self.auth_id = auth_id
        self.auth_signature = auth_signature
        self.base_url = base_url
        self.http = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(
                max_keepalive_connections=5,
                keepalive_expiry=30  # seconds — drop idle connections after 30s
            )
        )

    def _build_headers(self, method: str, endpoint: str, body: str = ""):
        return {
            "api-auth-id": self.auth_id,
            "api-auth-signature": self.auth_signature,
            # "Auth-Timestamp": timestamp,
            "Content-Type": "application/json"
        }

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3)
    )
    async def create_resource(self, method: str, endpoint: str, payload: Dict[str, Any] = None):
        url = f"{self.base_url}/{endpoint}"
        body_str = json.dumps(payload) if payload else ""

        headers = self._build_headers(method, endpoint, body_str)

        response = await self.http.request(
            method=method.upper(),
            url=url,
            json=payload if method.upper() in [
                "POST", "PUT", "PATCH"] else None,
            params=payload if method.upper() == "GET" else None,
            headers=headers
        )

        if response.status_code >= 400:
            raise Exception(f"{response.status_code}: {response.text}")

        return response.json()


client = StockTrimClient(
    auth_id=settings.ST_AUTH_ID,
    auth_signature=settings.ST_AUTH_SIGNATURE,
    base_url=settings.ST_BASE_URL
)


class VendorInfo(BaseModel):
    id: int
    name: str


class CategoryInfo(BaseModel):
    id: int
    name: str


class SOSItemRequest(BaseModel):
    id: int
    sku: str
    name: str
    barcode: Optional[str] = None
    leadTime: Optional[int] = 0
    onhand: Optional[float] = 0
    onPO: Optional[float] = 0
    purchaseCost: Optional[float] = 0
    salesPrice: Optional[float] = 0
    vendor: Optional[VendorInfo] = None
    vendorPartNumber: Optional[str] = None
    category: Optional[CategoryInfo] = None
    reorderPoint: Optional[float] = 0
    maxStock: Optional[float] = 0
    archived: Optional[bool] = False
    weight: Optional[float] = 0


def map_sos_to_stocktrim(data: SOSItemRequest) -> dict:
    return {
        "productId": data.id,
        "productCodeReadable": data.sku,
        "name": data.name,
        "category": data.category.name if data.category else None,
        "subCategory": None,
        "leadTime": data.leadTime or 0,
        "stockOnHand": float(data.onhand or 0),
        "stockOnOrder": float(data.onPO or 0),
        "cost": float(data.purchaseCost or 0),
        "price": float(data.salesPrice or 0),
        "supplierCode": data.vendor.name if data.vendor else None,
        "suppliers": [
            {
                "supplierId": str(data.vendor.id) if data.vendor else None,
                "supplierName": data.vendor.name if data.vendor else None,
                "supplierSkuCode": data.vendorPartNumber,
            }
        ] if data.vendor else [],
        "barcode": data.barcode,
        "discontinued": data.archived or False,
        "minimumShelfLevel": float(data.reorderPoint or 0),
        "maximumShelfLevel": float(data.maxStock or 0),
        "weight": float(data.weight or 0),
        # Fields not available in SOS — set to defaults
        # "serviceLevel": 0,
        # "forecastPeriod": 0,
        # "manufacturingTime": 0,
        # "orderFrequency": 0,
        # "minimumOrderQuantity": 0,
        # "batchSize": 0,
        # "unstocked": False,
        # "stockLocations": [],
    }


logger = logging.getLogger(__name__)
jsonl_logger = get_jsonl_logger()
STOCKTRIM_CONCURRENCY = 10


async def sync_items_to_stocktrim(items: dict[str, Any | list]):
    semaphore = asyncio.Semaphore(STOCKTRIM_CONCURRENCY)

    async def process_item(item):
        try:
            verified_item = SOSItemRequest.model_validate(item)

            payload = map_sos_to_stocktrim(verified_item)

            async with semaphore:
                result = await client.create_resource(
                    method="POST",
                    endpoint="Products",
                    payload=payload,
                )

            return {
                "status": "success",
                "identifier": item.get("id"),
                "sku": payload.get("code"),
                "result": result,
            }

        except RetryError as re:
            cause = re.last_attempt.exception()
            error_msg = f"{type(cause).__name__}: {cause}"
            logger.error(
                f"Failed to sync product to StockTrim after retries: {error_msg}",
                extra={
                    "error": error_msg,
                    "payload": item,
                    "identifier": item.get("id"),
                },
            )

            return {
                "status": "failed",
                "error": error_msg,
                "identifier": item.get("id"),
                "payload": item,
            }

        except Exception as e:
            logger.error(
                f"Failed to sync product to StockTrim: {str(e)}",
                extra={
                    "error": str(e),
                    "payload": item,
                    "identifier": item.get("id"),
                },
            )

            return {
                "status": "failed",
                "error": str(e),
                "identifier": item.get("id"),
                "payload": item,
            }

    tasks = [
        process_item(item)
        for item in items["data"]
    ]

    results = await asyncio.gather(*tasks)

    success = sum(
        1 for r in results if r["status"] == "success"
    )

    failed_results = [r for r in results if r["status"] == "failed"]
    failed = len(failed_results)
    failed_details = [
        {
            "identifier": r["identifier"],
            "reason": r["error"],
        }
        for r in failed_results
    ]

    jsonl_logger.info(
        build_jsonl_entry(
            action_type=f"Sync products from SOS Inventory to StockTrim",
            action_variant=f"sync-products-from-sos-to-stocktrim",
            status="Info",
            message=f"Synced {success} products successfully, {failed} failed.",
            failed_details=failed_details if failed_details else None,
        )
    )

    return {
        "success": success,
        "failed": failed,
    }


@router.post("/create-item")
async def create_item():
    """
    Sync SOS items into StockTrim concurrently.
    """

    try:
        started_at = datetime.utcnow()
        items = await api_get("/api/v2/item")

        # Count total items fetched
        total_fetched = len(items.get("data", []))
        
        sync_result = await sync_items_to_stocktrim(items)

        completed_at = datetime.utcnow()
        
        # Build entities array for email template
        entities = [
            {
                "name": "Items",
                "fetched": total_fetched,
                "synced": sync_result["success"],
                "failed": sync_result["failed"],
            }
        ]
        
        # Build summary text
        summary_text = f"Synced {sync_result['success']} item(s) successfully. {sync_result['failed']} failed."
        
        email_data = generate_scan_complete_email(
            email_to=settings.RECIPIENTS_LIST,
            started_at=started_at,
            completed_at=completed_at,
            summary_text=summary_text,
            entities=entities,
            total_failed=sync_result["failed"],
        )
        send_email(
            email_to=settings.RECIPIENTS_LIST,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
        return {
            "item_sync_result": sync_result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
