# libs/ratelimiter.py

import os
import redis
from datetime import timedelta


# Connect to Redis
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=int(os.getenv("REDIS_DB", 0)),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True,
)

# ----------------------------
# ⏱️ Rate Limit Configuration
# ----------------------------
RATE_LIMIT = 4            # Max messages per user per window
WINDOW_SECONDS = 86400     # 24 hours

def _get_ip_key(ip: str) -> str:
    return f"ratelimit:{ip}"

# ----------------------------
# ✅ Used during chat requests
# ----------------------------
def check_and_increment_ip(ip: str) -> bool:
    key = _get_ip_key(ip)
    try:
        new_value = r.incr(key)  # atomic
        if new_value == 1:
            r.expire(key, WINDOW_SECONDS)  # set TTL once = fixed window from first hit
        return new_value <= RATE_LIMIT
    except Exception as e:
        print(f"[RateLimiter] Redis error for IP {ip}: {e}")
        return True  # or False if you prefer fail-closed

# ----------------------------
# 📊 Used to show quota info
# ----------------------------
def get_ip_quota(ip: str) -> dict:
    """
    Returns the current quota status for the given IP:
    { used: int, remaining: int, limit: int, ttl: int or None }
    """
    key = _get_ip_key(ip)

    try:
        used = int(r.get(key) or 0)
        remaining = max(0, RATE_LIMIT - used)
        ttl = r.ttl(key)  # Time remaining until reset, in seconds

        return {
            "used": used,
            "remaining": remaining,
            "limit": RATE_LIMIT,
            "reset_in_seconds": ttl if ttl > 0 else 0
        }

    except Exception as e:
        print(f"[RateLimiter] Redis error for IP {ip}: {e}")
        return {
            "used": 0,
            "remaining": RATE_LIMIT,
            "limit": RATE_LIMIT,
            "reset_in_seconds": None
        }
