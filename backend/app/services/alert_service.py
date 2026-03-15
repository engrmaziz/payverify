"""
Dead SMS watchdog.
Run this as a cron job or APScheduler task every 30 minutes during school hours.
If no SMS has arrived in 3+ hours between 8am–5pm, alert admin.
"""
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

SCHOOL_HOUR_START = 8   # 8 AM
SCHOOL_HOUR_END   = 17  # 5 PM
DEAD_SMS_THRESHOLD_HOURS = 3


async def check_sms_heartbeat():
    """Check if SMS pipeline is alive. Call this on a schedule."""
    from app.db.supabase_client import get_last_sms_received_at, log_admin_alert
    from app.services.email_service import send_dead_sms_alert

    now = datetime.now(timezone.utc)
    # Only alert during school hours (Pakistan = UTC+5)
    local_hour = (now.hour + 5) % 24
    if not (SCHOOL_HOUR_START <= local_hour < SCHOOL_HOUR_END):
        logger.debug("Outside school hours — skipping watchdog check")
        return

    last_received = get_last_sms_received_at()
    if last_received is None:
        logger.warning("No SMS ever received — system may be unconfigured")
        return

    # Make timezone-aware if naive
    if last_received.tzinfo is None:
        last_received = last_received.replace(tzinfo=timezone.utc)

    gap = now - last_received
    if gap > timedelta(hours=DEAD_SMS_THRESHOLD_HOURS):
        msg = (
            f"No SMS received for {gap.seconds // 3600}h {(gap.seconds % 3600) // 60}m. "
            f"Last received: {last_received.isoformat()}"
        )
        logger.error(f"DEAD SMS ALERT: {msg}")
        log_admin_alert("DEAD_SMS", msg)
        await send_dead_sms_alert()
    else:
        logger.debug(f"SMS heartbeat OK. Last: {last_received.isoformat()}")
