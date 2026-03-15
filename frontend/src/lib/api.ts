const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type VerifyStatus =
  | "SUCCESS"
  | "NOT_FOUND"
  | "ALREADY_USED"
  | "PENDING_REVIEW"
  | "ERROR";

export interface VerifyResponse {
  status: VerifyStatus;
  message: string;
  amount?: number;
  bank?: string;
  transaction_id?: string;
}

export interface Transaction {
  id: string;
  raw_sms: string;
  sender: string;
  bank: string;
  amount: number;
  txn_id: string;
  status: "UNMATCHED" | "VERIFIED" | "USED" | "PARSE_FAILED";
  student_id: string | null;
  received_at: string;
  verified_at: string | null;
}

export async function verifyPayment(
  transaction_id: string,
  student_id: string,
  student_email?: string
): Promise<VerifyResponse> {
  const res = await fetch(`${API}/api/v1/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transaction_id, student_id, student_email }),
  });
  if (!res.ok) throw new Error("Network error");
  return res.json();
}

export async function getParseFailedRows(adminKey: string): Promise<{
  count: number;
  rows: Transaction[];
}> {
  const res = await fetch(`${API}/api/v1/admin/parse-failed`, {
    headers: { "X-Admin-Key": adminKey },
  });
  if (!res.ok) throw new Error("Unauthorized");
  return res.json();
}

export async function resolveRow(
  adminKey: string,
  row_id: string,
  txn_id: string,
  amount: number,
  bank: string
): Promise<{ status: string }> {
  const res = await fetch(`${API}/api/v1/admin/resolve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": adminKey,
    },
    body: JSON.stringify({ row_id, txn_id, amount, bank }),
  });
  if (!res.ok) throw new Error("Failed to resolve");
  return res.json();
}
