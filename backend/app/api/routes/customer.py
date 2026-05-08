from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from app.api.routes.stocktrim import client
from app.sos_stocktrim_sync.utils import api_get

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


# --- Endpoint ---

@router.put("/create-customer")
async def create_customer():
    try:
        customers = api_get(f"/api/v2/customer")
        for customer in customers["data"]:
            verified_customer = SOSCustomerRequest.model_validate(customer)
            stocktrim_payload = map_sos_customer_to_stocktrim(
                verified_customer)

            result = await client.create_resource(
                method="PUT",
                endpoint="Customers",
                payload=stocktrim_payload
            )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
