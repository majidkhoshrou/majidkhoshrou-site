# libs/ratelimiter.py

import redis
from datetime import timedelta

# Connect to Redis
r = redis.Redis(
    host="localhost",  # Update for AWS in prod
    port=6379,
    db=0,
    decode_responses=True
)

# Rate limit config
RATE_LIMIT = 20
WINDOW_SECONDS = 86400  # 24 hours

def check_and_increment_ip(ip: str) -> bool:
    """
    Returns True if the IP is under the limit and increments its count.
    Returns False if the limit is exceeded.
    """
    ip_key = f"ratelimit:{ip}"

    try:
        current_count = r.get(ip_key)
        if current_count and int(current_count) >= RATE_LIMIT:
            return False

        pipe = r.pipeline()
        pipe.incr(ip_key)
        pipe.expire(ip_key, WINDOW_SECONDS)
        pipe.execute()

        return True

    except Exception as e:
        print(f"[RateLimiter] Redis error for IP {ip}: {e}")
        return True  # Fail-open: allow requests if Redis fails
