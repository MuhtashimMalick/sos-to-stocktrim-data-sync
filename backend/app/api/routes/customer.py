import asyncio
import logging

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from tenacity import RetryError

from app.api.routes.stocktrim import client
from app.sos_stocktrim_sync.utils import api_get
from app.logging_config import get_jsonl_logger, build_jsonl_entry
from app.utils import generate_scan_complete_email, send_email

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


STOCKTRIM_CONCURRENCY = 10

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
                "identifier": customer.get("id"),
            }

        except RetryError as re:
            cause = re.last_attempt.exception()
            error_msg = f"{type(cause).__name__}: {cause}"
            logger.error(
                f"Failed to sync customer to StockTrim after retries: {error_msg}",
                extra={
                    "error": error_msg,
                    "payload": payload,
                    "identifier": customer.get("id"),
                },
            )

            return {
                "status": "failed",
                "error": error_msg,
                "payload": payload,
                "identifier": customer.get("id"),
            }

        except Exception as e:
            logger.error(
                f"Failed to sync customer to StockTrim: {str(e)}",
                extra={
                    "error": str(e),
                    "payload": payload,
                    "identifier": customer.get("id"),
                },
            )

            return {
                "status": "failed",
                "error": str(e),
                "payload": payload,
                "identifier": customer.get("id"),
            }

    tasks = [process_customer(c) for c in customers["data"]]

    results = await asyncio.gather(*tasks)

    success = sum(1 for r in results if r["status"] == "success")
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
            action_type=f"Sync customers from SOS Inventory to StockTrim",
            action_variant=f"sync-customers-from-sos-to-stocktrim",
            status="Info",
            message=f"Synced {success} customers successfully, {failed} failed.",
            failed_details=failed_details if failed_details else None,
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
        started_at = datetime.utcnow()
        customers = await api_get("/api/v2/customer")

        # Count total customers fetched
        total_fetched = len(customers.get("data", []))
        
        sync_result = await sync_customer_to_stocktrim(customers)

        completed_at = datetime.utcnow()
        
        # Build entities array for email template
        entities = [
            {
                "name": "Customers",
                "fetched": total_fetched,
                "synced": sync_result["success"],
                "failed": sync_result["failed"],
            }
        ]
        
        # Build summary text
        summary_text = f"Synced {sync_result['success']} customer(s) successfully. {sync_result['failed']} failed."
        
        email_data = generate_scan_complete_email(
            email_to=["muhtashim@segwayz.com", "muhammadhamzatalat@gmail.com"],
            started_at=started_at,
            completed_at=completed_at,
            summary_text=summary_text,
            entities=entities,
            total_failed=sync_result["failed"],
        )
        send_email(
            email_to=["muhtashim@segwayz.com", "muhammadhamzatalat@gmail.com"],
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
        return {
            "customer_sync_result": sync_result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
