# libs/recaptcha.py
import os
import requests
from typing import Tuple, Dict, Any, Optional

# Reuse your Redis client so "trust" lives with rate-limit state
try:
    from libs.ratelimiter import r  # your existing Redis instance
except Exception:
    r = None  # fallback: still allow verification; trust cache just won't work

RECAPTCHA_SECRET = os.getenv("RECAPTCHA_SECRET")  # set in env
RECAPTCHA_MIN_SCORE = float(os.getenv("RECAPTCHA_MIN_SCORE", "0.6"))
TRUST_TTL_SECONDS = int(os.getenv("TRUST_TTL_SECONDS", str(2 * 60 * 60)))  # default 2h
BURST_WINDOW_SECONDS = int(os.getenv("BURST_WINDOW_SECONDS", "3"))         # 1 msg / 3s

def _trust_key(ip: str) -> str:
    return f"trust:{ip}"

def is_trusted(ip: str) -> bool:
    """Return True if this IP has a valid short-lived trust flag."""
    if r is None:
        return False
    try:
        return r.get(_trust_key(ip)) is not None
    except Exception:
        return False

def mark_trusted(ip: str) -> None:
    """Set a short-lived trust flag so we don't re-challenge constantly."""
    if r is None:
        return
    try:
        r.setex(_trust_key(ip), TRUST_TTL_SECONDS, "1")
    except Exception:
        pass

def clear_trust(ip: str) -> None:
    if r is None:
        return
    try:
        r.delete(_trust_key(ip))
    except Exception:
        pass

def burst_ok(ip: str, limit: int = 1, window_seconds: Optional[int] = None) -> bool:
    """
    Very light burst control: allow `limit` requests per `window_seconds` (default BURST_WINDOW_SECONDS).
    """
    if r is None:
        return True  # no Redis → don't block
    if window_seconds is None:
        window_seconds = BURST_WINDOW_SECONDS
    key = f"burst:{ip}"
    try:
        count = r.incr(key)
        if count == 1:
            r.expire(key, window_seconds)
        return count <= limit
    except Exception:
        return True  # fail-open for burst limiter

def verify_recaptcha(
    token: Optional[str],
    remoteip: Optional[str],
    expected_action: str = "chat",
    min_score: Optional[float] = None,
    timeout: float = 5.0,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Verify Google reCAPTCHA v3 token server-side.
    Returns (ok, details_dict) where details contains raw provider response for logging.
    """
    if min_score is None:
        min_score = RECAPTCHA_MIN_SCORE

    if not RECAPTCHA_SECRET:
        return False, {"error": "RECAPTCHA_SECRET not configured"}
    if not token:
        return False, {"error": "missing_token"}

    try:
        resp = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET, "response": token, "remoteip": remoteip},
            timeout=timeout,
        )
        data = resp.json()
    except Exception as e:
        return False, {"error": "verify_request_failed", "exception": str(e)}

    if not data.get("success"):
        return False, {"error": "provider_rejected", "details": data}

    # v3 only: check action & score
    action_ok = (data.get("action") == expected_action) if "action" in data else True
    score_ok = float(data.get("score", 0)) >= float(min_score)

    ok = action_ok and score_ok
    if not ok:
        reason = []
        if not action_ok:
            reason.append("bad_action")
        if not score_ok:
            reason.append("low_score")
        return False, {"error": ",".join(reason) or "policy_fail", "details": data}

    return True, {"details": data}
