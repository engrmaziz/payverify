from datetime import datetime, timezone
from supabase import create_client, Client
from app.config import settings

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


# ── Raw insert (always first, before any parsing) ──────────────────────────────

def insert_raw_sms(sender: str, raw_sms: str) -> dict:
    """Insert raw SMS immediately on receipt. Never lose a payment."""
    result = (
        supabase.table("sms_transactions")
        .insert({"sender": sender, "raw_sms": raw_sms, "status": "UNMATCHED"})
        .execute()
    )
    return result.data[0]


# ── Update after Groq parsing ──────────────────────────────────────────────────

def update_parsed(row_id: str, bank: str, amount: float, txn_id: str):
    supabase.table("sms_transactions").update({
        "bank": bank,
        "amount": amount,
        "txn_id": txn_id,
    }).eq("id", row_id).execute()


def mark_parse_failed(row_id: str):
    supabase.table("sms_transactions").update(
        {"status": "PARSE_FAILED"}
    ).eq("id", row_id).execute()


# ── Verification helpers ───────────────────────────────────────────────────────

def lookup_txn(txn_id: str) -> dict | None:
    result = (
        supabase.table("sms_transactions")
        .select("*")
        .eq("txn_id", txn_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def mark_verified(row_id: str, student_id: str):
    supabase.table("sms_transactions").update({
        "status": "VERIFIED",
        "student_id": student_id,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", row_id).execute()


def mark_used(row_id: str):
    supabase.table("sms_transactions").update(
        {"status": "USED"}
    ).eq("id", row_id).execute()


# ── Watchdog: check for recent SMS ────────────────────────────────────────────

def get_last_sms_received_at() -> datetime | None:
    result = (
        supabase.table("sms_transactions")
        .select("received_at")
        .order("received_at", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return datetime.fromisoformat(result.data[0]["received_at"])
    return None


# ── Admin alert log ───────────────────────────────────────────────────────────

def log_admin_alert(alert_type: str, message: str):
    supabase.table("admin_alerts").insert({
        "alert_type": alert_type,
        "message": message,
    }).execute()


# ── Admin: list parse-failed rows ─────────────────────────────────────────────

def get_parse_failed_rows(limit: int = 50) -> list[dict]:
    result = (
        supabase.table("sms_transactions")
        .select("*")
        .eq("status", "PARSE_FAILED")
        .order("received_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


def manual_resolve(row_id: str, txn_id: str, amount: float, bank: str):
    """Admin manually enters txn details for a PARSE_FAILED row."""
    supabase.table("sms_transactions").update({
        "txn_id": txn_id,
        "amount": amount,
        "bank": bank,
        "status": "UNMATCHED",
    }).eq("id", row_id).execute()
