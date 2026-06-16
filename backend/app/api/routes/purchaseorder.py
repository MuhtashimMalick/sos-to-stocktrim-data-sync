import asyncio
import logging

from datetime import datetime
from typing import Any, Optional, List

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query

from app.api.routes.stocktrim import client
from app.sos_stocktrim_sync.utils import api_get
from app.logging_config import get_jsonl_logger, build_jsonl_entry
from app.utils import generate_scan_complete_email, send_email
from tenacity import RetryError
from app.core.config import settings


router = APIRouter(prefix="/purchaseorder", tags=["purchaseorder"])


# ---------------------------------------------------------------------------
# SOS Inventory Models  — mirrors the full SOS PO response structure
# ---------------------------------------------------------------------------

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


class SOSPOLine(BaseModel):
    id: int
    lineNumber: int
    # item.name = SKU / productId in StockTrim
    item: Optional[SOSNamedRef] = None
    vendorPartNumber: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = 0
    # SOS field name is 'unitprice' (lowercase p)
    unitprice: Optional[float] = 0
    amount: Optional[float] = 0
    received: Optional[float] = 0
    uom: Optional[SOSNamedRef] = None
    tax: Optional[SOSTax] = None
    duedate: Optional[str] = None


class SOSLinkedReceipt(BaseModel):
    id: int
    transactionType: Optional[str] = None     # e.g. "IR"
    refNumber: Optional[str] = None
    lineNumber: Optional[int] = None


class SOSPurchaseOrderRequest(BaseModel):
    id: int
    number: str                             # PO reference number  e.g. "IR-12345"
    date: str                               # PO creation date     e.g. "2019-05-08T09:13:00"
    vendor: Optional[SOSNamedRef] = None
    location: Optional[SOSNamedRef] = None
    billing: Optional[SOSAddressBlock] = None
    shipping: Optional[SOSAddressBlock] = None
    currency: Optional[SOSNamedRef] = None
    expectedDate: Optional[str] = None     # expected delivery date
    trackingNumber: Optional[str] = None
    confirmed: Optional[bool] = False
    closed: Optional[bool] = False
    archived: Optional[bool] = False
    pendingApproval: Optional[bool] = False
    subTotal: Optional[float] = 0
    total: Optional[float] = 0
    lines: Optional[List[SOSPOLine]] = []
    receivedStatus: Optional[str] = None
    openAmount: Optional[float] = 0
    linkedReceipts: Optional[List[SOSLinkedReceipt]] = []


# ---------------------------------------------------------------------------
# StockTrim → SOS  (write direction: create draft PO in SOS)
# ---------------------------------------------------------------------------

class STLineItem(BaseModel):
    productId: str
    quantity: float
    unitCost: Optional[float] = 0
    expectedDate: Optional[str] = None


class STCreatePORequest(BaseModel):
    orderNumber: Optional[str] = None
    orderDate: str
    supplierName: Optional[str] = None
    supplierId: Optional[str] = None
    locationCode: Optional[str] = None
    locationName: Optional[str] = None
    currency: Optional[str] = "USD"
    lines: List[STLineItem] = []


# ---------------------------------------------------------------------------
# Mapper:  SOS PO  →  StockTrim PurchaseOrders
#
# StockTrim PO schema:
# {
#   "orderDate":              SOS date
#   "supplier": {
#     "supplierCode":         SOS vendor.id  (as string)
#     "supplierName":         SOS vendor.name
#   },
#   "externalId":             SOS id         (as string)
#   "referenceNumber":        SOS number     (e.g. "IR-12345")
#   "location": {
#     "locationCode":         SOS location.id  (as string)
#     "locationName":         SOS location.name
#   },
#   "status":                 "Draft" when not confirmed, "Approved" when confirmed
#   "purchaseOrderLineItems": [
#     {
#       "productId":          SOS line.item.name  (SKU)
#       "quantity":           SOS line.quantity
#       "unitPrice":          SOS line.unitprice
#       "receivedDate":       SOS expectedDate  (closest match)
#     }
#   ]
# }
# ---------------------------------------------------------------------------
def map_sos_po_to_stocktrim(data: SOSPurchaseOrderRequest) -> dict:
    """
    Map a full SOS Purchase Order to the StockTrim PurchaseOrders payload.
    Returns a single StockTrim PO dict (one PO with all its line items).
    """

    # Determine status from SOS flags
    if data.closed and data.receivedStatus == "All" and data.openAmount == 0:
        status = "Received"
    elif data.confirmed and (data.openAmount > 0 or bool(data.linkedReceipts)):
        status = "Sent"
    elif data.pendingApproval:
        status = "Draft"
    else:
        status = "Approved"

    # Build line items
    line_items = []
    for line in data.lines or []:
        if not line.item or not line.item.id:
            continue
        st_line = {
            "productId": line.item.id if line.item else None,   # SKU stored in item.name
            "quantity": float(line.quantity or 0),
            "unitPrice": float(line.unitprice or 0),
        }
        # Use line duedate if available, else fall back to PO expectedDate
        received_date = line.duedate or data.expectedDate
        if received_date:
            st_line["receivedDate"] = received_date

        line_items.append(st_line)

    payload = {
        "orderDate": data.date,
        "createdDate": data.date,
        "fullyReceivedDate": data.date,
        "referenceNumber": str(data.number),
        "externalId": data.id,
        "status": status,
        "purchaseOrderLineItems": line_items,
    }

    # Supplier
    if data.vendor:
        payload["supplier"] = {
            "supplierCode": str(data.vendor.id) if data.vendor.id else None,
            "supplierName": data.vendor.name,
        }

    # Location
    if data.location:
        payload["location"] = {
            "locationCode": str(data.location.id) if data.location.id else None,
            "locationName": data.location.name,
        }

    # Tracking number stored as clientReferenceNumber (closest StockTrim field)
    # if data.trackingNumber:
    payload["clientReferenceNumber"] = data.number
    # else:

    return payload


# ---------------------------------------------------------------------------
# Mapper:  StockTrim PO  →  SOS Inventory  (write-back direction)
# ---------------------------------------------------------------------------

def map_stocktrim_po_to_sos(data: STCreatePORequest) -> dict:
    """
    Build the SOS Inventory purchaseorder POST payload from a StockTrim PO.
    Only include fields that have actual values — SOS returns 500 on unexpected nulls.
    """
    sos_lines = []
    for i, line in enumerate(data.lines, start=1):
        if not line.productId:
            continue
        sos_line = {
            "lineNumber": i,
            "item": {"name": line.productId},
            "quantity": line.quantity,
            "cost": line.unitCost or 0,
        }
        if line.expectedDate:
            sos_line["duedate"] = line.expectedDate
        sos_lines.append(sos_line)

    payload = {
        "date": data.orderDate,
        "approved": False,      # scope of work: always create as not-approved draft
        "lines": sos_lines,
    }

    if data.orderNumber:
        payload["number"] = data.orderNumber

    if data.supplierId or data.supplierName:
        payload["vendor"] = {
            "id": int(data.supplierId) if data.supplierId and data.supplierId.isdigit() else None,
            "name": data.supplierName,
        }

    if data.locationName:
        payload["location"] = {"name": data.locationName}

    # SOS defaults to USD — only send if different to avoid rejection
    if data.currency and data.currency != "USD":
        payload["currency"] = data.currency
    print(payload)
    return payload


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


STOCKTRIM_CONCURRENCY = 1
logger = logging.getLogger(__name__)
jsonl_logger = get_jsonl_logger()


async def sync_purchase_orders_to_stocktrim(
    purchase_orders: dict[str, Any | list]
):
    semaphore = asyncio.Semaphore(STOCKTRIM_CONCURRENCY)

    async def process_purchase_order(purchase_order):
        verified_po = SOSPurchaseOrderRequest.model_validate(
            purchase_order
        )

        payload = map_sos_po_to_stocktrim(verified_po)

        try:
            async with semaphore:
                result = await client.create_resource(
                    method="POST",
                    endpoint="PurchaseOrders",
                    payload=payload,
                )

            return {
                "status": "success",
                "identifier": payload.get("purchaseOrderNumber"),
                "stocktrim_status": payload.get("status"),
                "result": result,
            }

        except RetryError as re:
            cause = re.last_attempt.exception()  # fixed: was `e.last_attempt`
            error_msg = f"{type(cause).__name__}: {cause}"
            print(payload)
            print(f"Failed to sync purchase order to StockTrim: {error_msg}")
            logger.error(
                f"Failed to sync purchase order to StockTrim after retries: {error_msg}",
                extra={
                    "error": error_msg,
                    "payload": payload,
                    "identifier": payload.get("purchaseOrderNumber"),
                },
            )

            return {
                "status": "failed",
                "error": error_msg,  # now contains the real cause, not RetryError string
                "payload": payload,
                "identifier": payload.get("purchaseOrderNumber"),
            }

        except Exception as e:
            print(payload)
            print(f"Failed to sync purchase order to StockTrim: {str(e)}")
            logger.error(
                f"Failed to sync purchase order to StockTrim {str(e)}",
                extra={
                    "error": str(e),
                    "payload": payload,
                    "identifier": payload.get("purchaseOrderNumber"),
                },
            )

            return {
                "status": "failed",
                "error": str(e),
                "payload": payload,
                "identifier": payload.get("purchaseOrderNumber"),
            }

    tasks = [
        process_purchase_order(po)
        for po in purchase_orders["data"]
    ]

    results = await asyncio.gather(*tasks)

    success = sum(1 for r in results if r["status"] == "success")

    # Collect failed results with their reasons
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
            action_type=f"Sync purchase orders from SOS Inventory to StockTrim",
            action_variant=f"sync-purchase-orders-from-sos-to-stocktrim",
            status="Info",
            message=f"Synced {success} purchase orders successfully, {failed} failed.",
            failed_details=failed_details if failed_details else None,  # only include if there are failures
        )
    )

    return {
        "success": success,
        "failed": failed,
    }

@router.post("/sync-from-sos")
async def sync_purchase_order_from_sos(
    archived: bool = Query(False),
    from_date: Optional[str] = Query(
        None, description="Filter purchase orders from this date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(
        None, description="Filter purchase orders to this date (YYYY-MM-DD)"),
):
    """
    Sync SOS purchase orders into StockTrim concurrently.
    """

    try:
        started_at = datetime.utcnow()
        params = {
            "archived": "yes" if archived else "no",
            "from": f"{from_date}T00:00:00" if from_date else None,
            "to": f"{to_date}T23:59:59" if to_date else None
        }
        purchase_orders = await api_get("/api/v2/purchaseorder", params=params)
        
        # Count total purchase orders fetched
        total_fetched = len(purchase_orders.get("data", []))
        
        # Limit to purchase orders
        purchase_orders["data"] = purchase_orders["data"]
        sync_result = await sync_purchase_orders_to_stocktrim(purchase_orders)

        completed_at = datetime.utcnow()
        
        # Build entities array for email template
        entities = [
            {
                "name": "Purchase Orders",
                "fetched": total_fetched,
                "synced": sync_result["success"],
                "failed": sync_result["failed"],
            }
        ]
        
        # Build summary text
        summary_text = f"Synced {sync_result['success']} purchase order(s) successfully. {sync_result['failed']} failed."
        
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
            "purchase_order_sync_result": sync_result
        }

    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))


# @router.post("/create-in-sos")
# async def create_purchase_order_in_sos(data: STCreatePORequest):
#     """Create a StockTrim-generated PO as a not-approved draft in SOS Inventory."""
#     try:
#         sos_payload = map_stocktrim_po_to_sos(data)
#         result = api_post("/api/v2/purchaseorder", sos_payload)
#         return {
#             "po_number": data.orderNumber,
#             "supplier": data.supplierName,
#             "lines": len(data.lines),
#             "result": result,
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
