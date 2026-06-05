import logging

from app.models import UserPreference
import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from app.api.main import api_router
from app.core.config import settings
from app.core.scheduler import register_job, start_scheduler, shutdown_scheduler
from app.api.routes.sos_stocktrim import sync_all_data_to_stocktrim
from app.api.deps import get_db

def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

session: Session = get_db().__next__()

# Register all scheduled jobs
def setup_scheduled_jobs(minutes: int = 60*24*7) -> None:
    """Register all scheduled sync jobs."""
    register_job(
        job_id="sync_all_data",
        func=sync_all_data_to_stocktrim,
        minutes=minutes,
        name="Sync all data from SOS to StockTrim"
    )
    
    # Uncomment below when customer, purchase order, and inventory sync are ready
    # register_job(
    #     job_id="sync_customer",
    #     func=sync_customers,
    #     minutes=10,
    #     name="Sync Customers from SOS to StockTrim"
    # )
    # 
    # register_job(
    #     job_id="sync_purchaseorder",
    #     func=sync_purchase_orders,
    #     minutes=10,
    #     name="Sync Purchase Orders from SOS to StockTrim"
    # )
    # 
    # register_job(
    #     job_id="sync_inventory",
    #     func=sync_inventory_items,
    #     minutes=15,
    #     name="Sync Inventory Items from SOS to StockTrim"
    # )

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    user_preferences = session.exec(select(UserPreference)).first()

    if user_preferences is None or user_preferences.enable_auto_sync:
        minutes = user_preferences.sync_after_mins if user_preferences else 4320
        logger.info(f"Auto-sync enabled. Syncing every {minutes} minutes.")
        setup_scheduled_jobs(minutes=minutes)
        await start_scheduler()
        yield
        await shutdown_scheduler()
    else:
        if user_preferences and not user_preferences.enable_auto_sync:
            logger.info("Auto-sync is disabled in user preferences. Scheduler will not start.")
        yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
