"use client";
import { useState } from "react";
import Link from "next/link";
import { getParseFailedRows, resolveRow, type Transaction } from "@/lib/api";
import styles from "./admin.module.css";

type View = "login" | "dashboard";

export default function AdminPage() {
  const [view, setView] = useState<View>("login");
  const [key, setKey] = useState("");
  const [keyInput, setKeyInput] = useState("");
  const [rows, setRows] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resolving, setResolving] = useState<string | null>(null);
  const [resolveForm, setResolveForm] = useState<Record<string, { txn_id: string; amount: string; bank: string }>>({});

  async function login() {
    if (!keyInput.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await getParseFailedRows(keyInput.trim());
      setKey(keyInput.trim());
      setRows(data.rows);
      setView("dashboard");
    } catch {
      setError("Invalid admin key or server unreachable.");
    } finally {
      setLoading(false);
    }
  }

  async function refresh() {
    setLoading(true);
    try {
      const data = await getParseFailedRows(key);
      setRows(data.rows);
    } finally {
      setLoading(false);
    }
  }

  async function handleResolve(rowId: string) {
    const f = resolveForm[rowId];
    if (!f?.txn_id || !f?.amount) return;
    setResolving(rowId);
    try {
      await resolveRow(key, rowId, f.txn_id, parseFloat(f.amount), f.bank || "Unknown");
      await refresh();
      setResolving(null);
    } catch {
      setResolving(null);
    }
  }

  function updateForm(rowId: string, field: string, value: string) {
    setResolveForm((p) => ({ ...p, [rowId]: { ...(p[rowId] || {}), [field]: value } as typeof p[string] }));
  }

  const statusColor = (s: string) => {
    if (s === "VERIFIED") return styles.green;
    if (s === "PARSE_FAILED") return styles.red;
    if (s === "UNMATCHED") return styles.amber;
    return styles.gray;
  };

  /* ── LOGIN ── */
  if (view === "login") {
    return (
      <div className={styles.loginPage}>
        <Link href="/" className={styles.back}>&larr; Back</Link>
        <div className={styles.loginCard}>
          <div className={styles.loginIcon}>⚙</div>
          <h1 className={styles.loginTitle}>Admin access</h1>
          <p className={styles.loginSub}>Enter your admin key to continue</p>
          <input
            type="password"
            placeholder="Admin key"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && login()}
            style={{ marginBottom: 14 }}
          />
          {error && <p className={styles.loginError}>{error}</p>}
          <button className={styles.loginBtn} onClick={login} disabled={loading}>
            {loading ? "Checking..." : "Sign in"}
          </button>
        </div>
      </div>
    );
  }

  /* ── DASHBOARD ── */
  const verified = rows.filter((r) => r.status === "VERIFIED").length;
  const failed   = rows.filter((r) => r.status === "PARSE_FAILED").length;
  const unmatched = rows.filter((r) => r.status === "UNMATCHED").length;

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <div>
          <div className={styles.headerLogo}>pay<span>verify</span></div>
          <div className={styles.headerSub}>Admin dashboard</div>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.refreshBtn} onClick={refresh} disabled={loading}>
            {loading ? "..." : "Refresh"}
          </button>
          <button className={styles.logoutBtn} onClick={() => setView("login")}>
            Sign out
          </button>
        </div>
      </div>

      {/* Metrics */}
      <div className={styles.metrics}>
        <div className={styles.metric}>
          <div className={`${styles.metricVal} ${styles.greenText}`}>{verified}</div>
          <div className={styles.metricLabel}>Verified</div>
        </div>
        <div className={styles.metric}>
          <div className={`${styles.metricVal} ${styles.amberText}`}>{unmatched}</div>
          <div className={styles.metricLabel}>Unmatched</div>
        </div>
        <div className={styles.metric}>
          <div className={`${styles.metricVal} ${styles.redText}`}>{failed}</div>
          <div className={styles.metricLabel}>Need review</div>
        </div>
        <div className={styles.metric}>
          <div className={styles.metricVal}>{rows.length}</div>
          <div className={styles.metricLabel}>Total SMS</div>
        </div>
      </div>

      {/* Transactions table */}
      <div className={styles.tableWrap}>
        <div className={styles.tableHeader}>
          <div className={styles.tableTitle}>Transactions</div>
          {failed > 0 && (
            <div className={styles.alertBadge}>
              {failed} need manual review
            </div>
          )}
        </div>

        {rows.length === 0 ? (
          <div className={styles.empty}>No transactions yet.</div>
        ) : (
          <div className={styles.txnList}>
            {rows.map((row) => (
              <div key={row.id} className={styles.txnRow}>
                <div className={styles.txnMain}>
                  <div className={`${styles.dot} ${statusColor(row.status)}`} />
                  <div className={styles.txnInfo}>
                    <div className={styles.txnId}>
                      {row.txn_id || <span className={styles.noId}>no txn_id</span>}
                    </div>
                    <div className={styles.txnMeta}>
                      {row.bank || "?"} &middot; {row.sender} &middot;{" "}
                      {new Date(row.received_at).toLocaleString("en-PK", {
                        hour: "2-digit", minute: "2-digit", day: "numeric", month: "short",
                      })}
                      {row.student_id && <> &middot; {row.student_id}</>}
                    </div>
                  </div>
                  <div className={styles.txnRight}>
                    <div className={styles.txnAmt}>
                      {row.amount ? `Rs ${Number(row.amount).toLocaleString()}` : "—"}
                    </div>
                    <div className={`${styles.statusBadge} ${statusColor(row.status)}`}>
                      {row.status}
                    </div>
                  </div>
                </div>

                {/* Manual resolve form for PARSE_FAILED */}
                {row.status === "PARSE_FAILED" && (
                  <div className={styles.resolveForm}>
                    <div className={styles.rawSms}>{row.raw_sms}</div>
                    <div className={styles.resolveInputs}>
                      <input
                        placeholder="Transaction ID"
                        value={resolveForm[row.id]?.txn_id || ""}
                        onChange={(e) => updateForm(row.id, "txn_id", e.target.value)}
                        style={{ fontFamily: "var(--mono)", fontSize: 12 }}
                      />
                      <input
                        placeholder="Amount"
                        type="number"
                        value={resolveForm[row.id]?.amount || ""}
                        onChange={(e) => updateForm(row.id, "amount", e.target.value)}
                      />
                      <select
                        value={resolveForm[row.id]?.bank || ""}
                        onChange={(e) => updateForm(row.id, "bank", e.target.value)}
                        style={{ background: "var(--bg-input)", border: "1px solid var(--border)", borderRadius: 10, padding: "11px 14px", color: "var(--text)", fontSize: 13 }}
                      >
                        <option value="">Bank</option>
                        <option>Easypaisa</option>
                        <option>JazzCash</option>
                        <option>Meezan</option>
                      </select>
                      <button
                        className={styles.resolveBtn}
                        onClick={() => handleResolve(row.id)}
                        disabled={resolving === row.id}
                      >
                        {resolving === row.id ? "Saving..." : "Save"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
