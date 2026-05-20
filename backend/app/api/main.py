from fastapi import APIRouter


from app.api.routes import items, login, private, users, utils, sos_stocktrim, stocktrim, customer, salesorder, purchaseorder, supplier, inventory, location, logs
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(sos_stocktrim.router)
api_router.include_router(stocktrim.router)
api_router.include_router(customer.router)
api_router.include_router(salesorder.router)
api_router.include_router(logs.router)
api_router.include_router(purchaseorder.router)
api_router.include_router(supplier.router)
api_router.include_router(inventory.router)
api_router.include_router(location.router)
 


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
