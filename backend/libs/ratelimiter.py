# libs/ratelimiter.py

import os
import redis
from datetime import timedelta

# ----------------------------
# 🔧 Redis Setup
# ----------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Connect to Redis
r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
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
    """
    Returns True if IP is under the rate limit and increments usage.
    Returns False if the IP has exceeded the limit.
    """
    key = _get_ip_key(ip)

    try:
        current = r.get(key)
        if current and int(current) >= RATE_LIMIT:
            return False

        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, WINDOW_SECONDS)  # Resets 24h after first use
        pipe.execute()

        return True

    except Exception as e:
        print(f"[RateLimiter] Redis error for IP {ip}: {e}")
        return True  # Fail-open: allow requests if Redis fails

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
