import json
import logging
import re
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

# ── Known Pakistani bank sender numbers ───────────────────────────────────────
KNOWN_SENDERS = {
    "8785",           # Easypaisa
    "6060",           # JazzCash
    "14250",          # Meezan Bank
    "EASYPAISA",      # some devices show name not number
    "JAZZCASH",
    "MEEZAN",
    "03000786805",    # Meezan fallback long number
}

# ── Groq prompt ───────────────────────────────────────────────────────────────
GROQ_PROMPT = """\
You are a bank SMS parser for Pakistani banks and payment services.

Extract the following fields from the SMS text below:
- transaction_id: the unique TXN ID, TID, Ref#, SM number, or transaction reference (string, required)
- amount: the payment amount as a plain number — look for PKR, Rs, or any number near words like "received", "credited", "transferred" (float, required)
- bank: detect from context using these rules:
  * "JazzCash" if SMS mentions JazzCash, JAZZ, or sender is 6060
  * "Easypaisa" if SMS mentions Easypaisa or sender is 8785
  * "Meezan" if SMS mentions Meezan, Raast, UAN:021111111425, or sender is 14250
  * "HBL" if SMS mentions HBL
  * "UBL" if SMS mentions UBL
  * "Allied" if SMS mentions Allied Bank
  * "MCB" if SMS mentions MCB
  * "Sadapay" if SMS mentions Sadapay
  * "Nayapay" if SMS mentions Nayapay
  * Otherwise "Unknown"
- status: "success" if money was received/credited/deposited, "failed" otherwise

Rules:
- transaction_id is the MOST important field — look for TXN ID, TID, Ref#, SM followed by alphanumerics
- For amount: PKR 1.00 means amount is 1.0, Rs.500 means 500.0 — always return as a number not a string
- If the SMS is not a payment confirmation (e.g. promotional, OTP, alerts), set status to "failed"
- Return ONLY a valid JSON object. No explanation. No markdown. No code fences. No extra text.

SMS: {sms_text}"""


async def parse_sms_with_groq(raw_sms: str) -> dict | None:
    """
    Sends raw SMS to Groq AI for extraction.
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

        # Strip accidental markdown fences if model misbehaves
        if content.startswith("```"):
            parts = content.split("```")
            content = parts[1] if len(parts) > 1 else content
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        parsed = json.loads(content)

        # Ensure amount is always a float not a string
        if "amount" in parsed:
            try:
                parsed["amount"] = float(str(parsed["amount"]).replace(",", ""))
            except (ValueError, TypeError):
                parsed["amount"] = 0.0

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

FALLBACK_PATTERNS = {
    "Easypaisa": re.compile(
        r"(?:TID|Txn\s*ID|Transaction\s*ID)[:\s#]*([A-Z0-9]{8,20})", re.IGNORECASE
    ),
    "JazzCash": re.compile(
        r"(?:Ref\s*#|Reference)[:\s]*([A-Z0-9]{8,20})", re.IGNORECASE
    ),
    "Meezan": re.compile(
        r"(?:TXN\s*ID|TXN)[:\s#]*([A-Z0-9]{8,20})", re.IGNORECASE
    ),
}

# Generic fallback pattern — catches SM + alphanumeric (Meezan Raast format)
GENERIC_TXN_PATTERN = re.compile(
    r"(?:TXN\s*ID|TID|Ref#|Reference|Transaction\s*ID|SM)[:\s#]*([A-Z0-9]{8,20})",
    re.IGNORECASE
)

# Amount pattern — handles PKR, Rs, plain numbers near received/credited
AMOUNT_PATTERN = re.compile(
    r"(?:PKR|Rs\.?)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE
)


def fallback_parse(raw_sms: str, sender: str) -> dict | None:
    """
    Minimal regex fallback. Only used when Groq is unavailable.
    Less accurate than Groq — prefer Groq always.
    """
    raw_lower = raw_sms.lower()

    # Detect bank
    bank = "Unknown"
    if "easypaisa" in raw_lower or sender == "8785":
        bank = "Easypaisa"
    elif "jazzcash" in raw_lower or sender == "6060":
        bank = "JazzCash"
    elif "meezan" in raw_lower or "raast" in raw_lower or sender in ("14250", "03000786805"):
        bank = "Meezan"
    elif "hbl" in raw_lower:
        bank = "HBL"
    elif "ubl" in raw_lower:
        bank = "UBL"

    # Try bank-specific pattern first, then generic
    pattern = FALLBACK_PATTERNS.get(bank, GENERIC_TXN_PATTERN)
    txn_match = pattern.search(raw_sms) or GENERIC_TXN_PATTERN.search(raw_sms)
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
#push force