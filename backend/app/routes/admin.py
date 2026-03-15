import logging
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.db.supabase_client import get_parse_failed_rows, manual_resolve

router = APIRouter(tags=["Admin"])
logger = logging.getLogger(__name__)


def _require_admin(api_key: str):
    if api_key != settings.SMS_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Admin access denied")


@router.get("/admin/parse-failed", summary="List all SMS that failed to parse")
async def list_parse_failed(x_admin_key: str = Header(default="")):
    _require_admin(x_admin_key)
    rows = await get_parse_failed_rows(limit=100)
    return {"count": len(rows), "rows": rows}


class ManualResolveRequest(BaseModel):
    row_id: str
    txn_id: str
    amount: float
    bank: str


@router.post("/admin/resolve", summary="Manually fix a PARSE_FAILED row")
async def resolve_parse_failed(
    req: ManualResolveRequest,
    x_admin_key: str = Header(default=""),
):
    _require_admin(x_admin_key)
    await manual_resolve(
        row_id=req.row_id,
        txn_id=req.txn_id,
        amount=req.amount,
        bank=req.bank,
    )
    logger.info(f"Admin resolved row {req.row_id} → txn={req.txn_id}")
    return {"status": "resolved", "row_id": req.row_id}