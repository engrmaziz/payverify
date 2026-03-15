import logging
from fastapi import APIRouter
from pydantic import BaseModel

from app.db.supabase_client import lookup_txn, mark_verified, mark_used
from app.services.email_service import send_verification_email, send_admin_payment_alert

router = APIRouter(tags=["Payment Verification"])
logger = logging.getLogger(__name__)


class VerifyRequest(BaseModel):
    transaction_id: str
    student_id: str
    student_email: str = ""   # optional — send receipt if provided


class VerifyResponse(BaseModel):
    status: str
    message: str
    amount: float | None = None
    bank: str | None = None
    transaction_id: str | None = None


@router.post("/verify", response_model=VerifyResponse, summary="Student submits transaction ID")
async def verify_payment(req: VerifyRequest):
    txn_id = req.transaction_id.strip()

    if not txn_id:
        return VerifyResponse(
            status="ERROR",
            message="Transaction ID cannot be empty.",
        )

    row = lookup_txn(txn_id)

    # ── Case 1: Not in DB yet ──────────────────────────────────────────────────
    if not row:
        logger.info(f"Txn not found: {txn_id}")
        return VerifyResponse(
            status="NOT_FOUND",
            message="Transaction not received yet. Wait 2 minutes and try again.",
        )

    # ── Case 2: Already claimed by someone ────────────────────────────────────
    if row["status"] == "USED":
        logger.warning(f"Duplicate claim attempt: txn={txn_id} student={req.student_id}")
        return VerifyResponse(
            status="ALREADY_USED",
            message="This transaction ID has already been used.",
        )

    # ── Case 3: Needs manual review ───────────────────────────────────────────
    if row["status"] == "PARSE_FAILED":
        return VerifyResponse(
            status="PENDING_REVIEW",
            message="Your payment was received but needs manual review. Please contact admin.",
        )

    # ── Case 4: Already verified (idempotent re-submit) ───────────────────────
    if row["status"] == "VERIFIED":
        return VerifyResponse(
            status="SUCCESS",
            message="Payment already verified.",
            amount=float(row["amount"] or 0),
            bank=row["bank"],
            transaction_id=txn_id,
        )

    # ── Case 5: Fresh UNMATCHED — claim it ────────────────────────────────────
    mark_verified(row["id"], req.student_id)
    logger.info(f"Payment verified: txn={txn_id} student={req.student_id} amount={row['amount']}")

    # Fire emails in background (don't block the response)
    amount = float(row["amount"] or 0)
    bank = row["bank"] or "Unknown"

    if req.student_email:
        import asyncio
        asyncio.create_task(
            send_verification_email(
                student_email=req.student_email,
                student_id=req.student_id,
                amount=amount,
                bank=bank,
                txn_id=txn_id,
            )
        )

    asyncio.create_task(
        send_admin_payment_alert(
            amount=amount,
            bank=bank,
            txn_id=txn_id,
            student_id=req.student_id,
        )
    )

    return VerifyResponse(
        status="SUCCESS",
        message="Payment verified successfully!",
        amount=amount,
        bank=bank,
        transaction_id=txn_id,
    )
