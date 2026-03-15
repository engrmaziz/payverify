import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


async def send_verification_email(
    student_email: str,
    student_id: str,
    amount: float,
    bank: str,
    txn_id: str,
):
    """Send payment confirmation email to student via Resend."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping student email")
        return

    html_body = f"""
    <h2>Payment Verified ✅</h2>
    <p>Dear Student ({student_id}),</p>
    <p>Your payment has been successfully verified.</p>
    <table style="border-collapse:collapse;width:100%;max-width:400px">
      <tr><td style="padding:8px;border:1px solid #ddd"><strong>Transaction ID</strong></td>
          <td style="padding:8px;border:1px solid #ddd">{txn_id}</td></tr>
      <tr><td style="padding:8px;border:1px solid #ddd"><strong>Amount</strong></td>
          <td style="padding:8px;border:1px solid #ddd">Rs. {amount:,.2f}</td></tr>
      <tr><td style="padding:8px;border:1px solid #ddd"><strong>Bank</strong></td>
          <td style="padding:8px;border:1px solid #ddd">{bank}</td></tr>
    </table>
    <p style="color:#666;font-size:12px">Keep this email as your receipt.</p>
    """

    await _send(
        to=student_email,
        subject=f"Payment Verified — Rs. {amount:,.0f} via {bank}",
        html=html_body,
    )


async def send_admin_payment_alert(
    amount: float,
    bank: str,
    txn_id: str,
    student_id: str,
):
    """Notify admin when a payment is verified."""
    if not settings.ADMIN_EMAIL or not settings.RESEND_API_KEY:
        return

    html_body = f"""
    <h2>New Payment Verified</h2>
    <p><strong>Student:</strong> {student_id}</p>
    <p><strong>Amount:</strong> Rs. {amount:,.2f}</p>
    <p><strong>Bank:</strong> {bank}</p>
    <p><strong>Transaction ID:</strong> {txn_id}</p>
    """

    await _send(
        to=settings.ADMIN_EMAIL,
        subject=f"[Payment] Rs. {amount:,.0f} from {student_id} verified",
        html=html_body,
    )


async def send_dead_sms_alert():
    """Alert admin that no SMS has been received for a suspiciously long time."""
    if not settings.ADMIN_EMAIL or not settings.RESEND_API_KEY:
        logger.warning("Cannot send dead SMS alert — email not configured")
        return

    await _send(
        to=settings.ADMIN_EMAIL,
        subject="⚠️ WARNING: No bank SMS received in 3+ hours",
        html="""
        <h2>⚠️ SMS Watchdog Alert</h2>
        <p>No bank SMS has been received in the last 3 hours during school hours.</p>
        <p><strong>Action required:</strong> Check that the HTTP SMS app is running
        on the admin phone and is connected to the internet.</p>
        """,
    )


async def _send(to: str, subject: str, html: str):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": f"{settings.SCHOOL_NAME} <noreply@yourdomain.com>",
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
            )
            resp.raise_for_status()
            logger.info(f"Email sent to {to}: {subject}")
    except Exception as e:
        logger.error(f"Email send failed: {e}")
