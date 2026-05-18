import asyncio
import logging

from typing import Any, Optional

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.api.routes.stocktrim import client
from app.sos_stocktrim_sync.utils import api_get
from app.logging_config import get_jsonl_logger, build_jsonl_entry

router = APIRouter(prefix="/customer", tags=["customer"])
# --- SOS Nested Model


class SOSContact(BaseModel):
    title: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    suffix: Optional[str] = None


class SOSAddress(BaseModel):
    line1: Optional[str] = None
    line2: Optional[str] = None
    line3: Optional[str] = None
    line4: Optional[str] = None
    line5: Optional[str] = None
    city: Optional[str] = None
    stateProvince: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None


class SOSNamedRef(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None


# --- SOS Customer Request Model ---

class SOSCustomerRequest(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    companyName: Optional[str] = None
    contact: Optional[SOSContact] = None
    billing: Optional[SOSAddress] = None
    shipping: Optional[SOSAddress] = None
    archived: Optional[bool] = False


# --- Mapper ---

def map_sos_customer_to_stocktrim(data: SOSCustomerRequest) -> dict:
    billing = data.billing or SOSAddress()

    return {
        "code": str(data.id),
        "name": data.name,
        "streetAddress": billing.line1,
        "addressLine1": billing.line1,
        "addressLine2": billing.line2,
        "city": billing.city,
        "state": billing.stateProvince,
        "country": billing.country,
        "postCode": billing.postalCode,
        "emailAddress": data.email,
        "phone": data.phone or data.mobile,
    }


STOCKTRIM_CONCURRENCY = 5

logger = logging.getLogger(__name__)
jsonl_logger = get_jsonl_logger()


async def sync_customer_to_stocktrim(customers: dict[str, Any | list]):
    semaphore = asyncio.Semaphore(STOCKTRIM_CONCURRENCY)

    async def process_customer(customer):
        verified_customer = SOSCustomerRequest.model_validate(customer)
        payload = map_sos_customer_to_stocktrim(verified_customer)

        try:
            async with semaphore:
                result = await client.create_resource(
                    method="PUT",
                    endpoint="Customers",
                    payload=payload,
                )

            return {
                "status": "success",
                "result": result,
                "customer_id": customer.get("id"),
            }

        except Exception as e:
            logger.error(
                "Failed to sync customer to StockTrim",
                extra={
                    "error": str(e),
                    "payload": payload,
                    "customer_id": customer.get("id"),
                },
            )

            return {
                "status": "failed",
                "error": str(e),
                "payload": payload,
                "customer_id": customer.get("id"),
            }

    tasks = [process_customer(c) for c in customers["data"]]

    results = await asyncio.gather(*tasks)

    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")

    jsonl_logger.info(
        build_jsonl_entry(
            action_type=f"Sync customers from SOS Inventory to StockTrim",
            action_variant=f"sync-customers-from-sos-to-stocktrim",
            status="Info",
            message=f"Synced {success} customers successfully, {failed} failed.",
        )
    )

    return {
        "success": success,
        "failed": failed,
    }


# --- Endpoint ---

@router.put("/create-customer")
async def create_customer():
    """
    Sync SOS customers into StockTrim concurrently.
    """

    try:
        customers = await api_get("/api/v2/customer")

        sync_result = await sync_customer_to_stocktrim(customers)

        return {
            "customer_sync_result": sync_result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
