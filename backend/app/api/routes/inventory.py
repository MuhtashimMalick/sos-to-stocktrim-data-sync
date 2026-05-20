from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.api.routes.stocktrim import client

router = APIRouter(prefix="/inventory", tags=["inventory"])


# ---------------------------------------------------------------------------
# SOS Models
# ---------------------------------------------------------------------------

class SOSNamedRef(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None


class SOSStockItem(BaseModel):
    """One SKU's stock levels — from SOS /item or /inventorylevel endpoint."""
    id: int
    sku: str
    name: Optional[str] = None
    quantityOnHand: Optional[float] = 0
    quantityOnOrder: Optional[float] = 0
    # If location is None → values are treated as aggregate across all locations.
    # MeretUSA: confirm per-location or aggregate with the client.
    location: Optional[SOSNamedRef] = None


class SOSInventorySyncRequest(BaseModel):
    items: List[SOSStockItem]


# ---------------------------------------------------------------------------
# Mapper
# ---------------------------------------------------------------------------

def map_sos_stock_to_stocktrim(item: SOSStockItem) -> dict:
    """
    StockTrim stores stock on the Product record.
    POST to Products with just productId + stock fields performs an upsert.
    """
    payload: dict = {"productId": item.sku}

    if item.location:
        # Per-location: StockTrim merges into the stockLocations array
        payload["stockLocations"] = [{
            "locationCode": str(item.location.id) if item.location.id else item.location.name,
            "stockOnHand": float(item.quantityOnHand or 0),
            "stockOnOrder": float(item.quantityOnOrder or 0),
        }]
    else:
        # Aggregate totals
        payload["stockOnHand"] = float(item.quantityOnHand or 0)
        payload["stockOnOrder"] = float(item.quantityOnOrder or 0)

    return payload


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/sync-stock-levels")
async def sync_stock_levels(data: SOSInventorySyncRequest):
    """
    Push current stock-on-hand and stock-on-order from SOS into StockTrim.
    Send location=null on each item for aggregate, or a location object for per-location.
    """
    try:
        results = []
        for item in data.items:
            payload = map_sos_stock_to_stocktrim(item)
            result = await client.create_resource(
                method="POST",
                endpoint="Products",
                payload=payload,
            )
            results.append({
                "sku": item.sku,
                "location": item.location.name if item.location else "aggregate",
                "result": result,
            })
        return {"total_synced": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-single-sku")
async def sync_single_sku(item: SOSStockItem):
    """Single-SKU sync — useful for real-time webhook-driven updates."""
    try:
        payload = map_sos_stock_to_stocktrim(item)
        result = await client.create_resource(
            method="POST",
            endpoint="Products",
            payload=payload,
        )
        return {
            "sku": item.sku,
            "location": item.location.name if item.location else "aggregate",
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))