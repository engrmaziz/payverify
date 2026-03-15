# School Payment Verification

SMS-based fee payment verification for Pakistani schools.
Students pay via **Easypaisa / JazzCash / Meezan** as usual — the system
automatically captures the bank SMS, extracts the Transaction ID using
**Groq AI**, and lets students verify instantly on your website.

**Zero transaction fees. No merchant account needed.**

---

## Architecture

```
Bank SMS arrives on admin phone
  └── HTTP SMS app (Android, open-source, free)
        └── POST /api/v1/sms/ingest  ← this server
              └── Raw SMS stored in Supabase immediately
                    └── Groq AI extracts TxnID + Amount + Bank
                          └── status = UNMATCHED

Student enters Transaction ID on website
  └── POST /api/v1/verify
        └── Lookup in Supabase
              ├── MATCH  → status = VERIFIED, email sent
              └── NOT FOUND → "try again in 2 min"
```

---

## Quick Start

### 1. Clone & install

```bash
git clone <your-repo>
cd school-payments
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your Groq, Supabase, and Resend keys
```

### 3. Set up Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Open **SQL Editor** and run `app/db/schema.sql`
3. Copy your project URL and anon key into `.env`

### 4. Run locally

```bash
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

### 5. Configure HTTP SMS app

1. Install **[HTTP SMS](https://httpsms.com/)** on the admin's Android phone
2. Set webhook URL: `https://your-domain.com/api/v1/sms/ingest`
3. Add header: `X-SMS-Secret: your-long-random-secret-here`
4. Enable for senders: `8785` (Easypaisa), `6060` (JazzCash), `MEEZAN`

---

## API Reference

### `POST /api/v1/sms/ingest`
Receives forwarded SMS from HTTP SMS app.

**Headers:** `X-SMS-Secret: <your secret>`

**Body:**
```json
{
  "from_number": "8785",
  "message": "Easypaisa: Rs.5000 received from 03XX... TID: ABC12345",
  "sent_at": "2024-01-01T10:00:00Z"
}
```

**Response:**
```json
{ "status": "received", "id": "uuid" }
```

---

### `POST /api/v1/verify`
Student submits their transaction ID.

**Body:**
```json
{
  "transaction_id": "ABC12345",
  "student_id": "STU-001",
  "student_email": "student@email.com"
}
```

**Response statuses:**
| status | meaning |
|---|---|
| `SUCCESS` | Payment verified ✅ |
| `NOT_FOUND` | SMS not received yet — retry in 2 min |
| `ALREADY_USED` | Someone already claimed this TxnID |
| `PENDING_REVIEW` | Parsing failed — contact admin |

---

### `GET /api/v1/admin/parse-failed`
List all SMS that Groq couldn't parse.

**Headers:** `X-Admin-Key: <your secret>`

---

### `POST /api/v1/admin/resolve`
Manually enter details for a parse-failed row.

**Headers:** `X-Admin-Key: <your secret>`

**Body:**
```json
{
  "row_id": "uuid",
  "txn_id": "ABC12345",
  "amount": 5000.00,
  "bank": "Easypaisa"
}
```

---

## Deployment (Railway)

```bash
# Install Railway CLI
npm i -g @railway/cli
railway login
railway init
railway up
# Set env vars in Railway dashboard
```

Or deploy to **Render** — the `Procfile` is already configured.

---

## Dead SMS Watchdog

To run the watchdog that alerts admin if no SMS arrives during school hours:

```python
# Add to your cron or APScheduler setup:
from app.services.alert_service import check_sms_heartbeat
import asyncio

asyncio.run(check_sms_heartbeat())
```

Or add to `main.py` using `APScheduler`:

```bash
pip install apscheduler
```

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler = AsyncIOScheduler()
scheduler.add_job(check_sms_heartbeat, "interval", minutes=30)
scheduler.start()
```

---

## Key Design Decisions

- **Raw SMS stored before Groq call** — zero payment loss even if AI fails
- **Groq `temperature=0`** — deterministic parsing, no creative responses
- **Regex fallback** — if Groq is down, basic extraction still works
- **PARSE_FAILED queue** — admin can manually fix anything the AI missed
- **Unique `txn_id` constraint** — database-level duplicate prevention
