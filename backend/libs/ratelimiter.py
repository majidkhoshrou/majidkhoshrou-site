# libs/ratelimiter.py
import os
import redis
from datetime import datetime, timezone, timedelta

# Connect to Redis
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=int(os.getenv("REDIS_DB", 0)),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True,
)

# ⏱️ Rate Limit Configuration
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "6"))  # default 6/day

def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def _ttl_until_midnight_utc() -> int:
    now = datetime.now(timezone.utc)
    midnight = datetime.combine((now + timedelta(days=1)).date(), datetime.min.time(), tzinfo=timezone.utc)
    return max(1, int((midnight - now).total_seconds()))

def _get_ip_key(ip: str) -> str:
    # v2 namespace + date to avoid old/stale keys
    return f"ratelimit:v2:{_today_str()}:{ip}"

# ✅ Used during chat requests
def check_and_increment_ip(ip: str) -> bool:
    key = _get_ip_key(ip)
    try:
        new_value = r.incr(key)  # atomic
        ttl = r.ttl(key)
        if new_value == 1 or ttl is None or ttl < 0:
            r.expire(key, _ttl_until_midnight_utc())  # reset at midnight UTC
        return new_value <= RATE_LIMIT
    except Exception as e:
        print(f"[RateLimiter] Redis error for IP {ip}: {e}")
        return True  # or False if you prefer fail-closed

# 📊 Used to show quota info
def get_ip_quota(ip: str) -> dict:
    key = _get_ip_key(ip)
    try:
        used = int(r.get(key) or 0)
        ttl = r.ttl(key)
        if used > 0 and (ttl is None or ttl < 0):  # auto-heal if somehow missing
            r.expire(key, _ttl_until_midnight_utc())
            ttl = r.ttl(key)

        remaining = max(0, RATE_LIMIT - used)
        return {
            "used": used,
            "remaining": remaining,
            "limit": RATE_LIMIT,
            "reset_in_seconds": ttl if (ttl and ttl > 0) else _ttl_until_midnight_utc()
        }
    except Exception as e:
        print(f"[RateLimiter] Redis error for IP {ip}: {e}")
        return {
            "used": 0,
            "remaining": RATE_LIMIT,
            "limit": RATE_LIMIT,
            "reset_in_seconds": None
        }
