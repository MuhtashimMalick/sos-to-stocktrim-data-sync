import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.scheduler import register_job, start_scheduler, shutdown_scheduler
from app.core.sync_jobs import sync_salesorders, sync_customers, sync_purchase_orders, sync_inventory_items


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)


# Register all scheduled jobs
def setup_scheduled_jobs():
    """Register all scheduled sync jobs."""
    register_job(
        job_id="sync_salesorder",
        func=sync_salesorders,
        minutes=60,
        name="Sync Sales Orders from SOS to StockTrim"
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Setup and start the scheduler
    setup_scheduled_jobs()
    await start_scheduler()
    yield
    # Shutdown: Shutdown the scheduler
    await shutdown_scheduler()


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
