import json
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

# ── Known Pakistani bank sender numbers ───────────────────────────────────────
KNOWN_SENDERS = {
    "8785",         # Easypaisa
    "6060",         # JazzCash
    "EASYPAISA",    # some devices show name not number
    "JAZZCASH",
    "MEEZAN",
    "03000786805",  # Meezan fallback long number
}

# ── Groq prompt ───────────────────────────────────────────────────────────────
GROQ_PROMPT = """\
You are a bank SMS parser for Pakistani payment services.

Extract the following fields from the SMS text below:
- transaction_id: the unique transaction/reference/TID number (string, required)
- amount: payment amount as a plain number with no commas or currency symbols (float)
- bank: exactly one of: Easypaisa | JazzCash | Meezan | Unknown
- status: "success" if this is a received/credit/payment confirmation, "failed" otherwise

Rules:
- If the SMS is not a payment confirmation, set status to "failed"
- transaction_id is the most important field — look for TID, Txn ID, Ref#, Transaction ID
- Return ONLY a valid JSON object. No explanation. No markdown. No code fences.

SMS: {sms_text}"""


async def parse_sms_with_groq(raw_sms: str) -> dict | None:
    """
    Sends raw SMS to Groq for AI extraction.
    Returns dict: { transaction_id, amount, bank, status }
    Returns None on any failure — caller must handle gracefully.
    """
    prompt = GROQ_PROMPT.format(sms_text=raw_sms)

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama3-8b-8192",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,   # deterministic — critical for parsing
                    "max_tokens": 200,
                },
            )
            resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"].strip()

        # Strip accidental markdown fences
        if content.startswith("```"):
            parts = content.split("```")
            content = parts[1] if len(parts) > 1 else content
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        parsed = json.loads(content)
        logger.info(f"Groq parsed: {parsed}")
        return parsed

    except httpx.HTTPStatusError as e:
        logger.error(f"Groq HTTP error {e.response.status_code}: {e.response.text}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Groq returned non-JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Groq unexpected error: {e}")
        return None


# ── Fallback regex parser (used if Groq is down) ──────────────────────────────
import re

FALLBACK_PATTERNS = {
    "Easypaisa": re.compile(
        r"(?:TID|Txn\s*ID|Transaction\s*ID)[:\s#]*([A-Z0-9]{8,20})", re.IGNORECASE
    ),
    "JazzCash": re.compile(
        r"(?:Ref\s*#|Reference)[:\s]*([A-Z0-9]{8,20})", re.IGNORECASE
    ),
    "Meezan": re.compile(
        r"(?:TXN|Transaction)[:\s#]*([A-Z0-9]{8,20})", re.IGNORECASE
    ),
}
AMOUNT_PATTERN = re.compile(r"Rs\.?\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)


def fallback_parse(raw_sms: str, sender: str) -> dict | None:
    """
    Minimal regex fallback. Only used when Groq is unavailable.
    Less accurate — prefer Groq always.
    """
    bank = "Unknown"
    if "easypaisa" in raw_sms.lower() or sender == "8785":
        bank = "Easypaisa"
    elif "jazzcash" in raw_sms.lower() or sender == "6060":
        bank = "JazzCash"
    elif "meezan" in raw_sms.lower():
        bank = "Meezan"

    txn_match = FALLBACK_PATTERNS.get(bank, re.compile(r"([A-Z0-9]{10,20})")).search(raw_sms)
    amount_match = AMOUNT_PATTERN.search(raw_sms)

    if not txn_match:
        return None

    amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0

    return {
        "transaction_id": txn_match.group(1),
        "amount": amount,
        "bank": bank,
        "status": "success",
        "_source": "fallback_regex",
    }


def is_known_sender(sender: str) -> bool:
    return sender.strip() in KNOWN_SENDERS
