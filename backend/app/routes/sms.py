import logging
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel

from app.config import settings
from app.db.supabase_client import insert_raw_sms, update_parsed, mark_parse_failed
from app.services.groq_parser import parse_sms_with_groq, fallback_parse, is_known_sender

router = APIRouter(tags=["SMS Ingestion"])
logger = logging.getLogger(__name__)


class SMSPayload(BaseModel):
    # Our original format (manual testing)
    from_number: str = ""
    message: str = ""
    sent_at: str = ""

    # httpsms.com format
    owner: str = ""        # the phone number that owns the SIM
    contact: str = ""      # the sender of the SMS
    content: str = ""      # the SMS body

    @property
    def sender(self) -> str:
        """Get sender number from whichever format was used."""
        return self.from_number or self.contact or self.owner or "unknown"

    @property
    def body(self) -> str:
        """Get SMS body from whichever format was used."""
        return self.message or self.content or ""


@router.post("/sms/ingest", summary="Receive forwarded SMS from HTTP SMS app")
async def ingest_sms(
    payload: SMSPayload,
    background_tasks: BackgroundTasks,
    request: Request,
    x_sms_secret: str = Header(default=""),
    x_httpsms_signature: str = Header(default=""),
):
    # 1. Auth — accept either our secret OR httpsms.com's signature header
    valid = (
        x_sms_secret == settings.SMS_WEBHOOK_SECRET or
        x_httpsms_signature == settings.SMS_WEBHOOK_SECRET
    )

    # Also allow if no secret is configured yet (first-time setup)
    if settings.SMS_WEBHOOK_SECRET and not valid:
        logger.warning(
            f"Rejected request — bad secret. "
            f"x_sms_secret='{x_sms_secret[:6]}...' "
            f"x_httpsms_signature='{x_httpsms_signature[:6]}...'"
        )
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    # 2. Log raw request for debugging
    sender = payload.sender
    body = payload.body

    logger.info(f"SMS received — sender={sender} body_preview={body[:60]}")

    # 3. If body is empty, log and ignore
    if not body.strip():
        logger.warning(f"Empty SMS body received from sender={sender}")
        return {"status": "ignored", "reason": "empty body"}

    # 4. ALWAYS store raw SMS first — zero payment loss guarantee
    row = insert_raw_sms(
        sender=sender,
        raw_sms=body,
    )
    row_id = row["id"]
    logger.info(f"Raw SMS stored: id={row_id} sender={sender}")

    # 5. Parse in background — webhook returns immediately
    background_tasks.add_task(
        _parse_and_update,
        row_id=row_id,
        raw_sms=body,
        sender=sender,
    )

    return {"status": "received", "id": row_id}


async def _parse_and_update(row_id: str, raw_sms: str, sender: str):
    """Background task: parse SMS with Groq AI, fall back to regex if needed."""

    # Try Groq AI first
    parsed = await parse_sms_with_groq(raw_sms)

    # Fall back to regex if Groq fails
    if parsed is None:
        logger.warning(f"Groq failed for row {row_id} — trying regex fallback")
        parsed = fallback_parse(raw_sms, sender)

    # Both failed
    if not parsed:
        logger.error(f"All parsing failed for row {row_id} — marking PARSE_FAILED")
        mark_parse_failed(row_id)
        return

    # Non-payment SMS (e.g. promotional, OTP)
    if parsed.get("status") != "success":
        logger.info(f"Non-payment SMS for row {row_id} — marking PARSE_FAILED")
        mark_parse_failed(row_id)
        return

    # No transaction ID extracted
    txn_id = str(parsed.get("transaction_id", "")).strip()
    if not txn_id:
        logger.warning(f"No transaction_id extracted for row {row_id}")
        mark_parse_failed(row_id)
        return

    # Save parsed data
    try:
        update_parsed(
            row_id=row_id,
            bank=parsed.get("bank", "Unknown"),
            amount=float(parsed.get("amount", 0)),
            txn_id=txn_id,
        )
        logger.info(
            f"Parsed OK: row={row_id} txn={txn_id} "
            f"amount={parsed.get('amount')} bank={parsed.get('bank')}"
        )
    except Exception as e:
        # Unique constraint violation = duplicate transaction ID
        logger.warning(f"Could not save parsed data for row {row_id}: {e}")
        mark_parse_failed(row_id)