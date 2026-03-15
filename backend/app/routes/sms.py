import logging
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.config import settings
from app.db.supabase_client import insert_raw_sms, update_parsed, mark_parse_failed
from app.services.groq_parser import parse_sms_with_groq, fallback_parse, is_known_sender

router = APIRouter(tags=["SMS Ingestion"])
logger = logging.getLogger(__name__)


class SMSPayload(BaseModel):
    # HTTP SMS app sends these fields — match exactly
    from_number: str    # sender number e.g. "8785"
    message: str        # raw SMS body
    sent_at: str = ""   # ISO timestamp from phone (optional)


@router.post("/sms/ingest", summary="Receive forwarded SMS from HTTP SMS app")
async def ingest_sms(
    payload: SMSPayload,
    background_tasks: BackgroundTasks,
    x_sms_secret: str = Header(default=""),
):
    # 1. Validate shared secret — blocks anyone who discovers your URL
    if x_sms_secret != settings.SMS_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    # 2. Ignore non-bank senders before touching the DB
    if not is_known_sender(payload.from_number):
        logger.debug(f"Ignored SMS from unknown sender: {payload.from_number}")
        return {"status": "ignored", "reason": "unknown sender"}

    # 3. ALWAYS store raw SMS first — even before parsing
    #    This guarantees zero payment loss if Groq or anything else fails
    row = insert_raw_sms(
        sender=payload.from_number,
        raw_sms=payload.message,
    )
    row_id = row["id"]
    logger.info(f"Raw SMS stored: id={row_id} sender={payload.from_number}")

    # 4. Parse asynchronously so webhook returns immediately to HTTP SMS app
    background_tasks.add_task(
        _parse_and_update,
        row_id=row_id,
        raw_sms=payload.message,
        sender=payload.from_number,
    )

    return {"status": "received", "id": row_id}


async def _parse_and_update(row_id: str, raw_sms: str, sender: str):
    """Background task: parse SMS with Groq, fall back to regex, update DB."""
    parsed = await parse_sms_with_groq(raw_sms)

    # Fallback to regex if Groq fails
    if parsed is None:
        logger.warning(f"Groq failed for {row_id} — trying regex fallback")
        parsed = fallback_parse(raw_sms, sender)

    if not parsed:
        logger.error(f"All parsing failed for {row_id} — marking PARSE_FAILED")
        mark_parse_failed(row_id)
        return

    if parsed.get("status") != "success":
        logger.info(f"Non-payment SMS discarded: {raw_sms[:80]}")
        mark_parse_failed(row_id)
        return

    txn_id = str(parsed.get("transaction_id", "")).strip()
    if not txn_id:
        logger.warning(f"No transaction_id extracted for {row_id}")
        mark_parse_failed(row_id)
        return

    try:
        update_parsed(
            row_id=row_id,
            bank=parsed.get("bank", "Unknown"),
            amount=float(parsed.get("amount", 0)),
            txn_id=txn_id,
        )
        logger.info(f"Parsed OK: row={row_id} txn={txn_id} amount={parsed.get('amount')}")
    except Exception as e:
        # txn_id unique constraint hit — duplicate SMS
        logger.warning(f"Duplicate txn_id {txn_id}: {e}")
        mark_parse_failed(row_id)
