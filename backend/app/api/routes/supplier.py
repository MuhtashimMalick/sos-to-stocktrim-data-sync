import asyncio

import logging
from typing import Any, Optional

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.api.routes.stocktrim import client
from app.sos_stocktrim_sync.utils import api_get

router = APIRouter(prefix="/supplier", tags=["supplier"])

STOCKTRIM_CONCURRENCY = 5

# ---------------------------------------------------------------------------
# SOS Inventory Models — mirrors the full SOS vendor/supplier response
# ---------------------------------------------------------------------------


class SOSNamedRef(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None


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


class SOSSupplierRequest(BaseModel):
    id: int
    name: str                                   # vendor name  e.g. "ABC Plastics"
    companyName: Optional[str] = None           # legal company name
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    altPhone: Optional[str] = None
    fax: Optional[str] = None
    website: Optional[str] = None
    contact: Optional[SOSContact] = None
    # SOS vendor address is top-level (not nested in billing)
    address: Optional[SOSAddress] = None
    terms: Optional[SOSNamedRef] = None
    currency: Optional[SOSNamedRef] = None
    taxCode: Optional[SOSNamedRef] = None
    accountNumber: Optional[str] = None
    notes: Optional[str] = None
    archived: Optional[bool] = False
    # fields we receive but don't map
    starred: Optional[int] = None
    syncToken: Optional[int] = None
    showOnForms: Optional[bool] = None
    summaryOnly: Optional[bool] = None


# ---------------------------------------------------------------------------
# Mapper
#
# SOS field              →  StockTrim field
# ──────────────────────────────────────────
# id                     →  supplierCode      (string)
# name                   →  supplierName
# email                  →  email
# phone                  →  phone
# companyName            →  included in supplierName if different from name
# contact.firstName/Last →  contactName
# address (flattened)    →  address           (comma-joined string)
# accountNumber          →  externalId        (closest StockTrim field)
# archived               →  (used to skip archived vendors in bulk sync)
# ---------------------------------------------------------------------------

def map_sos_supplier_to_stocktrim(data: SOSSupplierRequest) -> dict:
    payload: dict = {
        # StockTrim requires supplierCode not supplierId
        "supplierCode": str(data.id),
        "supplierName": data.name,
    }

    # Email and phone
    if data.email:
        payload["email"] = data.email
    if data.phone:
        payload["phone"] = data.phone
    elif data.mobile:
        payload["phone"] = data.mobile

    # Contact person full name
    if data.contact:
        parts = filter(None, [
            data.contact.firstName,
            data.contact.lastName,
        ])
        full_name = " ".join(parts).strip()
        if full_name:
            payload["contactName"] = full_name

    # Flatten address into a single string — StockTrim stores address as text
    if data.address:
        addr = data.address
        payload["address"] = ", ".join(
            filter(None, [
                addr.line1,
                addr.line2,
                addr.line3,
                addr.city,
                addr.stateProvince,
                addr.postalCode,
                addr.country,
            ])
        )

    # Account number stored as externalId — closest StockTrim field
    if data.accountNumber:
        payload["externalId"] = data.accountNumber

    return payload


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


async def sync_supplier_to_stocktrim(vendors: dict[str, Any | list]):
    semaphore = asyncio.Semaphore(STOCKTRIM_CONCURRENCY)

    async def process_vendor(vendor):
        verified_vendor = SOSSupplierRequest.model_validate(vendor)
        payload = map_sos_supplier_to_stocktrim(verified_vendor)

        try:
            async with semaphore:
                result = await client.create_resource(
                    method="POST",
                    endpoint="Suppliers",
                    payload=[payload],
                )

            return {"status": "success", "result": result}

        except Exception as e:
            # 🔥 IMPORTANT: log full context
            logger.error(
                "Failed to sync supplier to StockTrim",
                extra={
                    "error": str(e),
                    "payload": payload,
                    "vendor_id": vendor.get("id"),
                },
            )

            return {
                "status": "failed",
                "error": str(e),
                "payload": payload,
                "vendor_id": vendor.get("id"),
            }

    tasks = [process_vendor(v) for v in vendors["data"]]

    results = await asyncio.gather(*tasks)

    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")

    return {
        "success": success,
        "failed": failed,
    }


@router.post("/create-supplier")
async def create_supplier():
    """
    Receive SOS vendors and upsert them into StockTrim concurrently.
    """
    try:
        vendors = await api_get("/api/v2/vendor")
        sync_result = {"supplier_sync_result": await sync_supplier_to_stocktrim(vendors)}
        return sync_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
