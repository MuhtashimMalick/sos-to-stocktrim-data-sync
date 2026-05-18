import asyncio
import logging

from typing import Any, Optional, List

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.api.routes.stocktrim import client
from app.sos_stocktrim_sync.utils import api_get
from app.logging_config import get_jsonl_logger, build_jsonl_entry

router = APIRouter(prefix="/salesorder", tags=["salesorder"])
# --- SOS Nested Model


class SOSNamedRef(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None


class SOSAddress(BaseModel):
    line1: Optional[str] = None
    line2: Optional[str] = None
    city: Optional[str] = None
    stateProvince: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None


class SOSAddressBlock(BaseModel):
    company: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[SOSAddress] = None


class SOSTax(BaseModel):
    taxable: Optional[bool] = False
    taxCode: Optional[SOSNamedRef] = None


class SOSOrderLine(BaseModel):
    id: int
    lineNumber: int
    item: Optional[SOSNamedRef] = None
    description: Optional[str] = None
    quantity: Optional[float] = 0
    unitprice: Optional[float] = 0
    amount: Optional[float] = 0
    cost: Optional[float] = 0
    duedate: Optional[str] = None
    uom: Optional[SOSNamedRef] = None


# --- SOS Sales Order Request Model ---

class SOSSalesOrderRequest(BaseModel):
    id: int
    number: str
    date: str
    customer: Optional[SOSNamedRef] = None
    location: Optional[SOSNamedRef] = None
    billing: Optional[SOSAddressBlock] = None
    shipping: Optional[SOSAddressBlock] = None
    subTotal: Optional[float] = 0
    total: Optional[float] = 0
    closed: Optional[bool] = False
    archived: Optional[bool] = False
    lines: Optional[List[SOSOrderLine]] = []


# --- Mapper ---

def map_sos_order_to_stocktrim(data: SOSSalesOrderRequest) -> List[dict]:
    """
    Flattens SOS order lines into individual StockTrim sales order records.
    One StockTrim record is created per line item.
    """
    records = []

    for line in data.lines or []:
        records.append({
            "productId": str(line.item.id) if line.item else None,
            "externalReferenceId": data.number,
            "orderDate": data.date,
            "quantity": float(line.quantity or 0),
            "unitPrice": float(line.unitprice or 0),
            "locationCode": str(data.location.id) if data.location else None,
            "locationName": data.location.name if data.location else None,
            "customerCode": str(data.customer.id) if data.customer else None,
            "customerName": data.customer.name if data.customer else None,
        })

    return records


STOCKTRIM_CONCURRENCY = 5
logger = logging.getLogger(__name__)
jsonl_logger = get_jsonl_logger()


async def sync_sales_orders_to_stocktrim(
    sales_orders: dict[str, Any | list]
):
    semaphore = asyncio.Semaphore(STOCKTRIM_CONCURRENCY)

    async def process_sales_order(saleorder):

        try:
            verified_saleorder = SOSSalesOrderRequest.model_validate(
                saleorder
            )

            stocktrim_payloads = map_sos_order_to_stocktrim(
                verified_saleorder
            )

            payload_results = []

            # One SOS sales order may create multiple StockTrim payloads
            for payload in stocktrim_payloads:

                try:
                    async with semaphore:
                        result = await client.create_resource(
                            method="POST",
                            endpoint="SalesOrders",
                            payload=payload,
                        )

                    payload_results.append({
                        "status": "success",
                        "result": result,
                        "sales_order_number": payload.get("salesOrderNumber"),
                    })

                except Exception as e:
                    logger.error(
                        "Failed to sync sales order payload to StockTrim",
                        extra={
                            "error": str(e),
                            "payload": payload,
                            "sales_order_number": payload.get("salesOrderNumber"),
                        },
                    )

                    payload_results.append({
                        "status": "failed",
                        "error": str(e),
                        "payload": payload,
                        "sales_order_number": payload.get("salesOrderNumber"),
                    })

            return {
                "status": "completed",
                "results": payload_results,
            }

        except Exception as e:
            logger.error(
                "Failed to process sales order",
                extra={
                    "error": str(e),
                    "sales_order": saleorder,
                },
            )

            return {
                "status": "failed",
                "error": str(e),
                "sales_order": saleorder,
            }

    tasks = [
        process_sales_order(saleorder)
        for saleorder in sales_orders["data"]
    ]

    results = await asyncio.gather(*tasks)

    success = 0
    failed = 0

    for order in results:

        if order["status"] == "failed":
            failed += 1
            continue

        for r in order["results"]:
            if r["status"] == "success":
                success += 1
            else:
                failed += 1

    jsonl_logger.info(
        build_jsonl_entry(
            action_type=f"Sync sales orders from SOS Inventory to StockTrim",
            action_variant=f"sync-sales-orders-from-sos-to-stocktrim",
            status="Info",
            message=f"Synced {success} sales orders successfully, {failed} failed.",
        )
    )

    return {
        "success": success,
        "failed": failed,
    }


# --- Endpoint ---


@router.post("/create-sales-order")
async def create_sales_order():

    try:
        sales_orders = await api_get("/api/v2/salesorder")

        result = await sync_sales_orders_to_stocktrim(
            sales_orders
        )

        return {
            "sales_order_sync_result": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
