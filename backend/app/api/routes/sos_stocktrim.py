from typing import Any, Dict, Literal

from fastapi import APIRouter, HTTPException

from app.api.routes.supplier import sync_supplier_to_stocktrim
from app.api.routes.stocktrim import sync_items_to_stocktrim
from app.api.routes.salesorder import sync_sales_orders_to_stocktrim
from app.api.routes.purchaseorder import sync_purchase_orders_to_stocktrim
from app.api.routes.location import sync_location_to_stocktrim
from app.api.routes.customer import sync_customer_to_stocktrim
from app.api.deps import CurrentUser, SessionDep
from app.sos_stocktrim_sync.utils import api_get

router = APIRouter(prefix="/sos-stocktrim", tags=["sos-stocktrim"])


async def sync_all_data_to_stocktrim() -> None:
    """
    Fetches all required data sequentially from the API and syncs each
    to StockTrim in the appropriate order. Raises an exception immediately
    if any API call fails.
    """

    # ------------------------------------------------------------------ #
    # 1. Fetch data sequentially (order matters – fail fast on any error) #
    # ------------------------------------------------------------------ #

    fetch_targets = [
        ("locations",       "/api/v2/location"),
        ("vendors",         "/api/v2/vendor"),
        ("customers",       "/api/v2/customer"),
        ("items",           "/api/v2/item"),
        ("sales_orders",    "/api/v2/salesorder"),
        ("purchase_orders", "/api/v2/purchaseorder"),
    ]

    results: Dict[str, Any] = {}

    for name, endpoint in fetch_targets:
        response = await api_get(endpoint)

        if response is None:
            raise ValueError(
                f"API call to '{endpoint}' returned no data (None). "
                f"Cannot proceed with sync."
            )

        # If your api_get surfaces HTTP errors as dicts with status/message
        # keys rather than raising, catch them explicitly here.
        if isinstance(response, dict):
            status_code = response.get("status_code") or response.get("status")
            if status_code and int(status_code) >= 400:
                message = response.get("message") or response.get(
                    "detail", "Unknown error")
                raise Exception(
                    f"[HTTP {status_code}] Failed to fetch '{name}' "
                    f"from '{endpoint}': {message}"
                )

        results[name] = response

    # Unpack for readability
    locations = results["locations"]
    vendors = results["vendors"]
    customers = results["customers"]
    items = results["items"]
    sales_orders = results["sales_orders"]
    purchase_orders = results["purchase_orders"]

    # ------------------------------------------------------------------ #
    # 2. Sync to StockTrim in dependency order                            #
    # ------------------------------------------------------------------ #

    sync_steps = [
        ("locations",       sync_location_to_stocktrim,        locations),
        ("vendors",         sync_supplier_to_stocktrim,        vendors),
        ("customers",       sync_customer_to_stocktrim,        customers),
        ("items",           sync_items_to_stocktrim,           items),
        ("purchase_orders", sync_purchase_orders_to_stocktrim, purchase_orders),
        ("sales_orders",    sync_sales_orders_to_stocktrim,    sales_orders),
    ]

    for name, sync_fn, data in sync_steps:
        try:
            await sync_fn(data)
        except Exception as exc:
            raise RuntimeError(
                f"Sync step failed for '{name}' "
                f"via {sync_fn.__name__}: {exc}"
            ) from exc


@router.get("/sync/{type}/")
async def read_sos_inventory_data(
    session: SessionDep, current_user: CurrentUser, type: Literal["item", "customer", "vendor", "salesorder", "purchaseorder", "location"]
) -> Any:
    """
    Read inventory data from SOS.
    """
    data = await api_get(f"/api/v2/{type}")
    return data


@router.post("/sync-all-data-to-stocktrim/")
async def sync_sos_inventory_to_stocktrim():
    """
    Sync all relevant data from SOS to StockTrim.
    """
    try:
        await sync_all_data_to_stocktrim()
        return {"status": "Sync completed successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
