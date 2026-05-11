from pydantic import BaseModel
from typing import Optional, List

from fastapi import APIRouter, HTTPException

from app.api.routes.stocktrim import client
from app.sos_stocktrim_sync.utils import api_get

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


async def sync_salesorders_job():
    """
    Core logic to sync sales orders from SOS to StockTrim.
    This function can be called by both the endpoint and scheduler.
    """
    sales_orders = api_get(f"/api/v2/salesorder")
    saleorder = sales_orders["data"][0]
    print(saleorder)
    verified_saleorder = SOSSalesOrderRequest.model_validate(saleorder)
    stocktrim_payloads = map_sos_order_to_stocktrim(verified_saleorder)
    print(stocktrim_payloads)

    results = []
    for payload in stocktrim_payloads:
        result = await client.create_resource(
            method="POST",
            endpoint="SalesOrders",
            payload=payload
        )
        print(result)
        results.append(result)

    return {
        "lines_created": len(results),
        "results": results
    }


# --- Endpoint ---

@router.post("/create-sales-order")
async def create_sales_order():
    try:
        result = await sync_salesorders_job()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
