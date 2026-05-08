from typing import Optional, List
from app.sos_stocktrim_sync.utils import api_get
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.api.routes.stocktrim import client

router = APIRouter(prefix="/supplier", tags=["supplier"])


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
    address: Optional[SOSAddress] = None        # SOS vendor address is top-level (not nested in billing)
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
        "supplierCode": str(data.id),   # StockTrim requires supplierCode not supplierId
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

@router.post("/create-supplier")
async def create_supplier():
    """
    Receive a single SOS vendor and upsert it in StockTrim.
    StockTrim Suppliers endpoint requires a JSON array — single item is wrapped in [].
    """
    try:
        vendors = api_get("/api/v2/vendor")
        for vendor in vendors["data"]:
            verified_vendor = SOSSupplierRequest.model_validate(vendor)
            payload = map_sos_supplier_to_stocktrim(verified_vendor)
            result = await client.create_resource(
                method="POST",
                endpoint="Suppliers",
                payload=[payload],          # StockTrim requires array even for single supplier
            )
        return {
            # "supplier_id": data.id,
            # "supplier_name": data.name,
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-sync")
async def bulk_sync_suppliers(suppliers: List[SOSSupplierRequest]):
    """
    Bulk upsert all SOS vendors into StockTrim.
    Skips archived vendors automatically.
    Use for initial data load or full re-sync.
    """
    try:
        results = []
        skipped = []

        for supplier in suppliers:
            if supplier.archived:
                skipped.append({"supplier_id": supplier.id, "supplier_name": supplier.name})
                continue

            payload = map_sos_supplier_to_stocktrim(supplier)
            result = await client.create_resource(
                method="POST",
                endpoint="Suppliers",
                payload=[payload],
            )
            results.append({
                "supplier_id": supplier.id,
                "supplier_name": supplier.name,
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