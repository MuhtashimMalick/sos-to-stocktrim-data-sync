from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.sos_stocktrim_sync.utils import api_get

router = APIRouter(prefix="/sos-stocktrim", tags=["sos-stocktrim"])


@router.post("/sync/{type}/")
async def sync_sos_to_stocktrim(
    session: SessionDep, current_user: CurrentUser, type: Literal["item", "customer", "vendor", ]
) -> Any:
    """
    Sync items from SOS to StockTrim.
    """
    data = api_get(f"/api/v2/{type}")
    return data
