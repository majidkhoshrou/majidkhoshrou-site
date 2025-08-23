# libs/challenge.py
import os
import requests
from typing import Tuple, Dict, Any, Optional
from functools import lru_cache

# Reuse your Redis client from ratelimiter
try:
    from libs.ratelimiter import r  # type: ignore
except Exception:
    r = None  # graceful fallback if Redis isn't available yet

# Fallback import: read from env or SSM when available
try:
    from libs.utils import getenv_or_ssm   # expects (name, ssm_path)
except Exception:
    def getenv_or_ssm(name, ssm_path=None, **_):
        return os.getenv(name)

# ----------------------------
# Config (env-driven)
# ----------------------------
CHALLENGE_PROVIDER = os.getenv("CHALLENGE_PROVIDER", "turnstile").lower()

# Trust a client for this long once they pass a challenge
TRUST_TTL_SECONDS = int(os.getenv("TRUST_TTL_SECONDS", str(2 * 60 * 60)))  # 2h

# Light burst limiter defaults (1 request / 3s)
BURST_WINDOW_SECONDS = int(os.getenv("BURST_WINDOW_SECONDS", "3"))
BURST_LIMIT = int(os.getenv("BURST_LIMIT", "1"))

# Local/dev convenience: skip provider calls on private nets when no secrets are set
DEV_BYPASS_RECAPTCHA = os.getenv("DEV_BYPASS_RECAPTCHA", "true").lower() == "true"

# Provider secrets
# Provider secrets — lazy + SSM fallback
@lru_cache(maxsize=1)
def _turnstile_secret() -> str:
    return (
        os.getenv("TURNSTILE_SECRET")
        or getenv_or_ssm("TURNSTILE_SECRET", "/majidkhoshrou/prod/TURNSTILE_SECRET")
        or ""
    )

@lru_cache(maxsize=1)
def _recaptcha_secret() -> str:
    return (
        os.getenv("RECAPTCHA_SECRET")
        or getenv_or_ssm("RECAPTCHA_SECRET", "/majidkhoshrou/prod/RECAPTCHA_SECRET")
        or ""
    )

RECAPTCHA_MIN_SCORE = float(os.getenv("RECAPTCHA_MIN_SCORE", "0.6"))

# ----------------------------
# Helpers: local dev & keys
# ----------------------------
def _is_local(ip: Optional[str]) -> bool:
    """Rudimentary check for localhost / RFC1918 / Docker bridge ranges."""
    if not ip:
        return True
    return (
        ip in {"127.0.0.1", "::1"}
        or ip.startswith("10.")
        or ip.startswith("192.168.")
        or ip.startswith("172.16.") or ip.startswith("172.17.")
        or ip.startswith("172.18.") or ip.startswith("172.19.")
        or ip.startswith("172.2")   # covers 172.20.* through 172.29.*
        or ip.startswith("172.3")   # covers 172.30.* and 172.31.*
    )

def _trust_key(ip: str) -> str:
    return f"trust:{ip}"

# ----------------------------
# Public API used by app.py
# ----------------------------
def is_trusted(ip: str) -> bool:
    """Return True if this IP has a short-lived trust flag set."""
    if r is None:
        return False
    try:
        return r.get(_trust_key(ip)) is not None
    except Exception:
        return False

def mark_trusted(ip: str, ttl: Optional[int] = None) -> None:
    """Set a trust flag (default TTL from env)."""
    if r is None:
        return
    try:
        r.setex(_trust_key(ip), int(ttl or TRUST_TTL_SECONDS), "1")
    except Exception:
        pass

def clear_trust(ip: str) -> None:
    if r is None:
        return
    try:
        r.delete(_trust_key(ip))
    except Exception:
        pass

def burst_ok(ip: str, limit: Optional[int] = None, window_seconds: Optional[int] = None) -> bool:
    """
    Very light burst control: allow `limit` requests per `window_seconds` per IP.
    Default: 1 request / 3 seconds.
    """
    if r is None:
        return True  # no Redis → don't block
    if limit is None:
        limit = BURST_LIMIT
    if window_seconds is None:
        window_seconds = BURST_WINDOW_SECONDS

    key = f"burst:{ip}"
    try:
        count = r.incr(key)
        if count == 1:
            r.expire(key, int(window_seconds))
        return int(count) <= int(limit)
    except Exception:
        return True  # fail-open for burst limiter

# ----------------------------
# Provider verifiers
# ----------------------------
def verify_turnstile(
    token: Optional[str],
    remoteip: Optional[str],
    expected_action: str = "chat",
    timeout: float = 5.0
) -> Tuple[bool, Dict[str, Any]]:
    
    secret = _turnstile_secret()
    if not secret:
        return False, {"error": "TURNSTILE_SECRET not configured"}
    if not token:
        return False, {"error": "missing_token"}

    try:
        resp = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": secret, "response": token, "remoteip": remoteip},
            timeout=timeout,
        )

        data = resp.json()
    except Exception as e:
        return False, {"error": "verify_request_failed", "exception": str(e)}

    if not data.get("success"):
        return False, {"error": "provider_rejected", "details": data}

    # If you set an action on the client, Turnstile may echo it back—check when present
    if "action" in data and data.get("action") != expected_action:
        return False, {"error": "bad_action", "details": data}

    return True, {"details": data}

def verify_recaptcha(
    token: Optional[str],
    remoteip: Optional[str],
    expected_action: str = "chat",
    min_score: Optional[float] = None,
    timeout: float = 5.0
) -> Tuple[bool, Dict[str, Any]]:
    if min_score is None:
        min_score = RECAPTCHA_MIN_SCORE

    secret = _recaptcha_secret()
    if not secret:
        return False, {"error": "RECAPTCHA_SECRET not configured"}
    if not token:
        return False, {"error": "missing_token"}

    try:
        resp = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": secret, "response": token, "remoteip": remoteip},
            timeout=timeout,
        )
        data = resp.json()
    except Exception as e:
        return False, {"error": "verify_request_failed", "exception": str(e)}

    if not data.get("success"):
        return False, {"error": "provider_rejected", "details": data}

    if data.get("action") != expected_action:
        return False, {"error": "bad_action", "details": data}
    if float(data.get("score", 0)) < float(min_score):
        return False, {"error": "low_score", "details": data}

    return True, {"details": data}

# ----------------------------
# Orchestrator
# ----------------------------
def verify_challenge(
    token: Optional[str],
    remoteip: Optional[str],
    expected_action: str = "chat",
) -> Tuple[bool, Dict[str, Any]]:
    """
    Provider-agnostic verification. In dev/local (and with no secrets set),
    returns True when DEV_BYPASS_RECAPTCHA=true.
    """
    # Dev bypass: local/private IPs and no provider secrets → allow
    if DEV_BYPASS_RECAPTCHA and _is_local(remoteip) and not (_turnstile_secret() or _recaptcha_secret()):
        return True, {"dev_bypass": True}

    if CHALLENGE_PROVIDER == "turnstile":
        return verify_turnstile(token, remoteip, expected_action)
    if CHALLENGE_PROVIDER == "recaptcha":
        return verify_recaptcha(token, remoteip, expected_action)

    return False, {"error": f"unknown_provider:{CHALLENGE_PROVIDER}"}
