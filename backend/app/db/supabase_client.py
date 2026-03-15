"""
Async Supabase client using direct httpx calls.
Replaces the sync supabase-py client which blocks FastAPI's async event loop.
"""
import httpx
from datetime import datetime, timezone
from app.config import settings

# ── Base headers for all Supabase requests ────────────────────────────────────
def _headers() -> dict:
    return {
        "apikey": settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

BASE_URL = f"{settings.SUPABASE_URL}/rest/v1"


# ── Raw insert (always first, before any parsing) ──────────────────────────────

async def insert_raw_sms(sender: str, raw_sms: str) -> dict:
    """Insert raw SMS immediately on receipt. Never lose a payment."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{BASE_URL}/sms_transactions",
            headers=_headers(),
            json={"sender": sender, "raw_sms": raw_sms, "status": "UNMATCHED"},
        )
        resp.raise_for_status()
        return resp.json()[0]


# ── Update after Groq parsing ──────────────────────────────────────────────────

async def update_parsed(row_id: str, bank: str, amount: float, txn_id: str):
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.patch(
            f"{BASE_URL}/sms_transactions",
            headers=_headers(),
            params={"id": f"eq.{row_id}"},
            json={"bank": bank, "amount": amount, "txn_id": txn_id},
        )
        resp.raise_for_status()


async def mark_parse_failed(row_id: str):
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.patch(
            f"{BASE_URL}/sms_transactions",
            headers={**_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{row_id}"},
            json={"status": "PARSE_FAILED"},
        )
        resp.raise_for_status()


# ── Verification helpers ───────────────────────────────────────────────────────

async def lookup_txn(txn_id: str) -> dict | None:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{BASE_URL}/sms_transactions",
            headers=_headers(),
            params={"txn_id": f"eq.{txn_id}", "limit": "1", "select": "*"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data[0] if data else None


async def mark_verified(row_id: str, student_id: str):
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.patch(
            f"{BASE_URL}/sms_transactions",
            headers={**_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{row_id}"},
            json={
                "status": "VERIFIED",
                "student_id": student_id,
                "verified_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        resp.raise_for_status()


async def mark_used(row_id: str):
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.patch(
            f"{BASE_URL}/sms_transactions",
            headers={**_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{row_id}"},
            json={"status": "USED"},
        )
        resp.raise_for_status()


# ── Watchdog ───────────────────────────────────────────────────────────────────

async def get_last_sms_received_at() -> datetime | None:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{BASE_URL}/sms_transactions",
            headers=_headers(),
            params={"select": "received_at", "order": "received_at.desc", "limit": "1"},
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            return datetime.fromisoformat(data[0]["received_at"])
        return None


# ── Admin alert log ───────────────────────────────────────────────────────────

async def log_admin_alert(alert_type: str, message: str):
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{BASE_URL}/admin_alerts",
            headers={**_headers(), "Prefer": "return=minimal"},
            json={"alert_type": alert_type, "message": message},
        )
        resp.raise_for_status()


# ── Admin: list parse-failed rows ─────────────────────────────────────────────

async def get_parse_failed_rows(limit: int = 50) -> list[dict]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{BASE_URL}/sms_transactions",
            headers=_headers(),
            params={
                "status": "eq.PARSE_FAILED",
                "order": "received_at.desc",
                "limit": str(limit),
                "select": "*",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def manual_resolve(row_id: str, txn_id: str, amount: float, bank: str):
    """Admin manually enters txn details for a PARSE_FAILED row."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.patch(
            f"{BASE_URL}/sms_transactions",
            headers={**_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{row_id}"},
            json={"txn_id": txn_id, "amount": amount, "bank": bank, "status": "UNMATCHED"},
        )
        resp.raise_for_status()