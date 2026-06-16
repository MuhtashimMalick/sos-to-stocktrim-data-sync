import logging

from datetime import datetime
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
from app.utils import generate_scan_complete_email, send_email

router = APIRouter(prefix="/sos-stocktrim", tags=["sos-stocktrim"])

logger = logging.getLogger(__name__)


async def sync_all_data_to_stocktrim() -> None:
    """
    Fetches all required data sequentially from the API and syncs each
    to StockTrim in the appropriate order. Raises an exception immediately
    if any API call fails.
    """

    # ------------------------------------------------------------------ #
    # 1. Fetch data sequentially (order matters – fail fast on any error) #
    # ------------------------------------------------------------------ #
    started_at = datetime.utcnow()
    fetch_targets = [
        ("locations",       "/api/v2/location"),
        ("vendors",         "/api/v2/vendor"),
        ("customers",       "/api/v2/customer"),
        ("items",           "/api/v2/item"),
        ("sales_orders",    "/api/v2/salesorder"),
        ("purchase_orders", "/api/v2/purchaseorder"),
    ]

    results: Dict[str, Any] = {}

    try:

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
            ("Locations", sync_location_to_stocktrim, locations),
            ("Vendors", sync_supplier_to_stocktrim, vendors),
            ("Customers", sync_customer_to_stocktrim, customers),
            ("Items", sync_items_to_stocktrim, items),
            ("Purchase Orders", sync_purchase_orders_to_stocktrim, purchase_orders),
            ("Sales Orders", sync_sales_orders_to_stocktrim, sales_orders),
        ]

        sync_results = {}
        for display_name, sync_fn, data in sync_steps:
            try:
                result = await sync_fn(data)
                sync_results[display_name] = {
                    "result": result,
                    "fetched": len(data.get("data", [])),
                }
            except Exception as exc:
                raise RuntimeError(
                    f"Sync step failed for '{display_name}' "
                    f"via {sync_fn.__name__}: {exc}"
                ) from exc
        
        completed_at = datetime.utcnow()
        
        # Build entities array for email template
        entities = []
        total_failed = 0
        total_synced = 0
        for display_name, sync_data in sync_results.items():
            sync_result = sync_data["result"]
            fetched = sync_data["fetched"]
            synced = sync_result["success"]
            failed = sync_result["failed"]
            
            entities.append({
                "name": display_name,
                "fetched": fetched,
                "synced": synced,
                "failed": failed,
            })
            total_synced += synced
            total_failed += failed
        
        # Build summary text
        summary_text = f"Synced {total_synced} records successfully. {total_failed} failed."
        
        email_data = generate_scan_complete_email(
            email_to=["muhtashim@segwayz.com", "muhammadhamzatalat@gmail.com"],
            started_at=started_at,
            completed_at=completed_at,
            summary_text=summary_text,
            entities=entities,
            total_failed=total_failed,
        )
        send_email(
            email_to=["muhtashim@segwayz.com", "muhammadhamzatalat@gmail.com"],
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    except Exception as e:
        # Log the error with as much context as possible before re-raising
        logger.error(f"Error during SOS to StockTrim sync: {str(e)}")




@router.get("/sync/{type}/")
async def read_sos_inventory_data(
    session: SessionDep, type: Literal["item", "customer", "vendor", "salesorder", "purchaseorder", "location"]
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
