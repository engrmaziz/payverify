"use client";
import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { verifyPayment, type VerifyResponse } from "@/lib/api";
import styles from "./verify.module.css";

type State = "idle" | "loading" | "polling" | "success" | "error";

const BANKS = ["Easypaisa", "JazzCash", "Meezan"];

export default function VerifyPage() {
  const [txnId, setTxnId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [email, setEmail] = useState("");
  const [state, setState] = useState<State>("idle");
  const [result, setResult] = useState<VerifyResponse | null>(null);
  const [pollCount, setPollCount] = useState(0);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  const stopPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current);
  };

  useEffect(() => () => stopPolling(), []);

  async function submit() {
    if (!txnId.trim() || !studentId.trim()) return;
    setState("loading");
    setResult(null);
    setPollCount(0);

    const res = await tryVerify();
    if (!res) { setState("error"); return; }

    if (res.status === "NOT_FOUND") {
      setState("polling");
      let count = 0;
      pollRef.current = setInterval(async () => {
        count++;
        setPollCount(count);
        if (count >= 10) {            // 10 × 30s = 5 minutes
          stopPolling();
          setResult(res);
          setState("error");
          return;
        }
        const r = await tryVerify();
        if (r && r.status !== "NOT_FOUND") {
          stopPolling();
          setResult(r);
          setState(r.status === "SUCCESS" ? "success" : "error");
        }
      }, 30_000);
      setResult(res);
    } else {
      setResult(res);
      setState(res.status === "SUCCESS" ? "success" : "error");
    }
  }

  async function tryVerify(): Promise<VerifyResponse | null> {
    try {
      return await verifyPayment(txnId.trim(), studentId.trim(), email.trim() || undefined);
    } catch { return null; }
  }

  return (
    <div className={styles.page}>
      <Link href="/" className={styles.back}>&larr; Back</Link>

      <div className={styles.card}>
        {/* Header */}
        <div className={styles.cardHeader}>
          <div className={styles.icon}>
            {state === "success" ? "✓" : state === "error" ? "!" : "₨"}
          </div>
          <h1 className={styles.title}>
            {state === "success"
              ? "Payment verified"
              : state === "polling"
              ? "Checking..."
              : "Verify payment"}
          </h1>
          <p className={styles.subtitle}>
            {state === "success"
              ? "Your fee has been confirmed"
              : state === "polling"
              ? `Retrying automatically (${pollCount}/10)`
              : "Enter your transaction details below"}
          </p>
        </div>

        {/* SUCCESS STATE */}
        {state === "success" && result && (
          <div className={styles.successBox}>
            <div className={styles.successAmount}>
              Rs. {result.amount?.toLocaleString()}
            </div>
            <div className={styles.successBank}>via {result.bank}</div>
            <div className={styles.successRows}>
              <div className={styles.successRow}>
                <span>Transaction ID</span>
                <span className={styles.mono}>{result.transaction_id}</span>
              </div>
              <div className={styles.successRow}>
                <span>Student</span>
                <span className={styles.mono}>{studentId}</span>
              </div>
              <div className={styles.successRow}>
                <span>Status</span>
                <span className={styles.verified}>Verified</span>
              </div>
            </div>
            <button
              className={styles.resetBtn}
              onClick={() => { setState("idle"); setResult(null); setTxnId(""); setStudentId(""); setEmail(""); }}
            >
              Verify another payment
            </button>
          </div>
        )}

        {/* ERROR / NOT FOUND */}
        {state === "error" && result && (
          <div className={styles.errorBox}>
            <p>{result.message}</p>
            <button className={styles.retryBtn} onClick={() => setState("idle")}>
              Try again
            </button>
          </div>
        )}

        {/* INPUT FORM */}
        {(state === "idle" || state === "loading" || state === "polling") && (
          <>
            <div className={styles.banks}>
              {BANKS.map((b) => (
                <div key={b} className={styles.bankChip}>{b}</div>
              ))}
            </div>

            <div className={styles.field}>
              <label>Transaction ID</label>
              <input
                value={txnId}
                onChange={(e) => setTxnId(e.target.value)}
                placeholder="e.g. TID12345678 or REF-XXXXXX"
                style={{ fontFamily: "var(--mono)" }}
                disabled={state === "loading" || state === "polling"}
              />
            </div>

            <div className={styles.field}>
              <label>Student ID</label>
              <input
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                placeholder="e.g. STU-0042"
                disabled={state === "loading" || state === "polling"}
              />
            </div>

            <div className={styles.field}>
              <label>Email <span className={styles.optional}>(optional — for receipt)</span></label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="student@email.com"
                disabled={state === "loading" || state === "polling"}
              />
            </div>

            {state === "polling" && (
              <div className={styles.pollingBanner}>
                <div className={styles.spinner} />
                <span>
                  SMS not received yet. Auto-checking every 30 seconds&hellip;
                </span>
              </div>
            )}

            <button
              className={styles.submitBtn}
              onClick={submit}
              disabled={state === "loading" || state === "polling" || !txnId || !studentId}
            >
              {state === "loading" ? "Verifying..." : "Verify payment"}
            </button>
          </>
        )}
      </div>

      <p className={styles.help}>
        Having trouble?{" "}
        <a href="mailto:admin@school.com">Contact the school office</a>
      </p>
    </div>
  );
}
