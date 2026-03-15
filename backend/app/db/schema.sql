-- Run this once in your Supabase SQL editor
-- ============================================================
-- sms_transactions: core table — every bank SMS lands here
-- ============================================================
CREATE TABLE IF NOT EXISTS sms_transactions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_sms      TEXT NOT NULL,
    sender       TEXT,
    bank         TEXT,                      -- Easypaisa | JazzCash | Meezan | Unknown
    amount       NUMERIC(12, 2),
    txn_id       TEXT UNIQUE,               -- extracted transaction ID
    status       TEXT NOT NULL DEFAULT 'UNMATCHED',
    -- status values:
    --   UNMATCHED    → received & parsed, waiting for student to claim
    --   VERIFIED     → student claimed it
    --   USED         → already claimed, reject duplicates
    --   PARSE_FAILED → Groq couldn't parse, needs manual review
    student_id   TEXT,                      -- set when VERIFIED
    received_at  TIMESTAMPTZ DEFAULT NOW(),
    verified_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_txn_id  ON sms_transactions(txn_id);
CREATE INDEX IF NOT EXISTS idx_status  ON sms_transactions(status);
CREATE INDEX IF NOT EXISTS idx_recv_at ON sms_transactions(received_at DESC);

-- ============================================================
-- admin_alerts: log every alert sent to admin
-- ============================================================
CREATE TABLE IF NOT EXISTS admin_alerts (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_type TEXT NOT NULL,   -- DEAD_SMS | AMOUNT_MISMATCH | PARSE_FAILED
    message    TEXT,
    sent_at    TIMESTAMPTZ DEFAULT NOW()
);
