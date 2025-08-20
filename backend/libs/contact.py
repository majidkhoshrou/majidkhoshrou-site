# libs/contact.py
import os
import time
from collections import defaultdict, deque
from email.message import EmailMessage
import smtplib

# Optional: pull secrets from SSM if not in env
try:
    from libs.utils import getenv_or_ssm
except Exception:
    def getenv_or_ssm(env_name, ssm_path=None, **_):
        return os.getenv(env_name)

# --- simple in-memory rate limit (per IP, rolling window) ---
_WINDOW_SECONDS = int(os.getenv("CONTACT_WINDOW_SECONDS", "3600"))  # 1 hour
_MAX_PER_WINDOW = int(os.getenv("CONTACT_MAX_PER_WINDOW", "5"))

_hits: defaultdict[str, deque] = defaultdict(deque)

def _too_many(ip: str) -> bool:
    now = time.time()
    cutoff = now - _WINDOW_SECONDS
    q = _hits[ip]
    while q and q[0] < cutoff:
        q.popleft()
    return len(q) >= _MAX_PER_WINDOW

def _record(ip: str) -> None:
    _hits[ip].append(time.time())

def _human_delay_ok(submitted_at: str, min_ms: int = 1500) -> bool:
    """Reject forms submitted 'too fast' after page load (bots)."""
    try:
        started = float(submitted_at)
        return (time.time() * 1000 - started) >= min_ms
    except Exception:
        # If missing/invalid, don't block legit users
        return True

def send_contact_email(
    *,
    name: str,
    email: str,
    message: str,
    ip: str | None = None,
    honeypot: str = "",
    submitted_at: str = "",   # from hidden field, optional
) -> dict:
    """
    Returns: {"ok": True} on success, otherwise {"ok": False, "error": "..."}.
    """

    # 🪤 Honeypot: if filled, pretend success (don’t tip off bots)
    if honeypot and honeypot.strip():
        print("[contact] honeypot triggered; skipping send")
        return {"ok": True}

    # Optional: time trap (fast submissions look botty)
    if not _human_delay_ok(submitted_at):
        print("[contact] too-fast submission; skipping send")
        return {"ok": True}

    ip = ip or "unknown"

    # throttle
    if _too_many(ip):
        return {"ok": False, "error": "Too many messages from this IP. Try again later."}

    # validate inputs
    name = (name or "").strip()
    email = (email or "").strip()
    message = (message or "").strip()
    if not name or not email or not message:
        return {"ok": False, "error": "Please fill in all required fields."}
    if len(message) > 10_000:
        return {"ok": False, "error": "Message is too long."}

    # SMTP / Gmail config (env first, then SSM fallback)
    smtp_host = os.getenv("SMTP_HOST") or os.getenv("SMTP_SERVER") or "smtp.gmail.com"
    smtp_port = int(os.getenv("SMTP_PORT", os.getenv("MAIL_PORT", "587")))
    smtp_user = getenv_or_ssm("SMTP_USERNAME", "/majidkhoshrou/prod/SMTP_USER") or \
                getenv_or_ssm("SMTP_USER", "/majidkhoshrou/prod/SMTP_USER")
    smtp_pass = getenv_or_ssm("SMTP_PASSWORD", "/majidkhoshrou/prod/SMTP_PASSWORD") or \
                getenv_or_ssm("SMTP_PASS", "/majidkhoshrou/prod/SMTP_PASSWORD")
    use_tls   = (os.getenv("SMTP_USE_TLS", "true").lower() == "true")
    recipient = os.getenv("CONTACT_RECIPIENT") or smtp_user

    if not all([smtp_host, smtp_port, smtp_user, smtp_pass, recipient]):
        return {"ok": False, "error": "Email service is not configured on the server."}

    subject = f"New message from {name} (Contact Form)"
    body = (
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"IP: {ip}\n\n"
        f"Message:\n{message}\n"
    )

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"Contact Form <{smtp_user}>"
        msg["To"] = recipient
        msg["Reply-To"] = email
        msg.set_content(body)

        if use_tls:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

        _record(ip)
        return {"ok": True}
    except Exception as e:
        print("❌ send_contact_email error:", repr(e))
        return {"ok": False, "error": "Failed to send your message. Please try again later."}
