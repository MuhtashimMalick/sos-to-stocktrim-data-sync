from app.core.config import settings
import time
import hashlib
import hmac
from typing import Dict, Any
import httpx
from typing import Optional
from app.sos_stocktrim_sync.utils import api_get
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json

from fastapi import APIRouter, HTTPException
router = APIRouter(prefix="/stocktrim", tags=["stocktrim"])


class StockTrimClient:
    def __init__(self, auth_id: str, auth_signature: str, base_url: str):
        self.auth_id = auth_id
        self.auth_signature = auth_signature
        self.base_url = base_url

    def _build_headers(self, method: str, endpoint: str, body: str = ""):
        return {
            "api-auth-id": self.auth_id,
            "api-auth-signature": self.auth_signature,
            # "Auth-Timestamp": timestamp,
            "Content-Type": "application/json"
        }

    async def create_resource(self, method: str, endpoint: str, payload: Dict[str, Any] = None):
        url = f"{self.base_url}/{endpoint}"
        body_str = json.dumps(payload) if payload else ""

        headers = self._build_headers(method, endpoint, body_str)

        async with httpx.AsyncClient() as client:
            response = await client.request(
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


@router.post("/create-item")
async def create_item():
    items = api_get(f"/api/v2/item")
    for item in items["data"]:
        if item["id"] == 88:
            try:
                print(item)
                verified_item = SOSItemRequest.model_validate(item)
                print(verified_item)
                stocktrim_payload = map_sos_to_stocktrim(verified_item)
                print(stocktrim_payload)
                result = await client.create_resource(
                    method="POST",
                    endpoint="Products",
                    payload=stocktrim_payload
                )
            except Exception as e:
                print(str(e))
    return result
