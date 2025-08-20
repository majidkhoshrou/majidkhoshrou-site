# libs/ratelimiter.py
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# --- Config ---
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "6"))  # requests per day
TABLE_NAME = os.getenv("RATE_TABLE_NAME")       # set by SAM in prod

# --- Helpers ---
def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def _ttl_until_midnight_utc() -> int:
    now = datetime.now(timezone.utc)
    midnight = datetime.combine((now + timedelta(days=1)).date(), datetime.min.time(), tzinfo=timezone.utc)
    # small buffer so DynamoDB TTL cleanup isn't time-critical
    return max(60, int((midnight - now).total_seconds()) + 300)

def _get_ip_key(ip: str) -> str:
    # include date so caps reset daily regardless of TTL processing lag
    return f"ratelimit:v3:{_today_str()}:{ip}"

# --- Backend 1: DynamoDB (prod) ---
_ddb_table = None
def _get_ddb_table():
    global _ddb_table
    if _ddb_table is not None:
        return _ddb_table
    if not TABLE_NAME:
        return None
    import boto3
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "eu-central-1"
    _ddb_table = boto3.resource("dynamodb", region_name=region).Table(TABLE_NAME)
    return _ddb_table

def _ddb_check_and_increment(ip: str) -> bool:
    table = _get_ddb_table()
    if not table:
        raise RuntimeError("DDB not configured")
    key = {"k": _get_ip_key(ip)}
    ttl = int(datetime.now(timezone.utc).timestamp() + _ttl_until_midnight_utc())
    resp = table.update_item(
        Key=key,
        UpdateExpression="SET #c = if_not_exists(#c, :zero) + :one, #ttl = if_not_exists(#ttl, :ttl)",
        ExpressionAttributeNames={"#c": "count", "#ttl": "ttl"},
        ExpressionAttributeValues={":zero": Decimal(0), ":one": Decimal(1), ":ttl": Decimal(ttl)},
        ReturnValues="UPDATED_NEW",
    )
    used = int(resp["Attributes"]["count"])
    return used <= RATE_LIMIT

def _ddb_get_quota(ip: str) -> dict:
    table = _get_ddb_table()
    if not table:
        raise RuntimeError("DDB not configured")
    key = {"k": _get_ip_key(ip)}
    item = table.get_item(Key=key).get("Item", {}) or {}
    used = int(item.get("count", 0))
    ttl_epoch = int(item.get("ttl", 0))
    reset_in = max(1, ttl_epoch - int(datetime.now(timezone.utc).timestamp())) if ttl_epoch else _ttl_until_midnight_utc()
    return {"used": used, "remaining": max(0, RATE_LIMIT - used), "limit": RATE_LIMIT, "reset_in_seconds": reset_in}

# --- Backend 2: Redis (local optional) ---
_r = None
def _get_redis():
    global _r
    if _r is not None:
        return _r
    host = os.getenv("REDIS_HOST")
    if not host:
        _r = None
        return None
    import redis
    _r = redis.Redis(
        host=host,
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True,
    )
    return _r

def _redis_check_and_increment(ip: str) -> bool:
    r = _get_redis()
    if not r:
        raise RuntimeError("Redis not configured")
    key = _get_ip_key(ip)
    new_value = r.incr(key)
    ttl = r.ttl(key)
    if new_value == 1 or ttl is None or ttl < 0:
        r.expire(key, _ttl_until_midnight_utc())
    return new_value <= RATE_LIMIT

def _redis_get_quota(ip: str) -> dict:
    r = _get_redis()
    if not r:
        raise RuntimeError("Redis not configured")
    key = _get_ip_key(ip)
    used = int(r.get(key) or 0)
    ttl = r.ttl(key)
    if used > 0 and (ttl is None or ttl < 0):
        r.expire(key, _ttl_until_midnight_utc())
        ttl = r.ttl(key)
    return {"used": used, "remaining": max(0, RATE_LIMIT - used), "limit": RATE_LIMIT,
            "reset_in_seconds": ttl if (ttl and ttl > 0) else _ttl_until_midnight_utc()}

# --- Backend 3: In-memory (fallback for local dev) ---
_mem = {}
def _mem_check_and_increment(ip: str) -> bool:
    key = _get_ip_key(ip)
    now = datetime.now(timezone.utc).timestamp()
    exp = _mem.get(key, {}).get("exp", 0)
    if now > exp:
        _mem[key] = {"count": 0, "exp": now + _ttl_until_midnight_utc()}
    _mem[key]["count"] += 1
    return _mem[key]["count"] <= RATE_LIMIT

def _mem_get_quota(ip: str) -> dict:
    key = _get_ip_key(ip)
    entry = _mem.get(key)
    if not entry:
        return {"used": 0, "remaining": RATE_LIMIT, "limit": RATE_LIMIT, "reset_in_seconds": _ttl_until_midnight_utc()}
    used = entry["count"]
    reset_in = max(1, int(entry["exp"] - datetime.now(timezone.utc).timestamp()))
    return {"used": used, "remaining": max(0, RATE_LIMIT - used), "limit": RATE_LIMIT, "reset_in_seconds": reset_in}

# --- Public API ---
def check_and_increment_ip(ip: str) -> bool:
    # Prefer DynamoDB in prod
    try:
        if TABLE_NAME:
            return _ddb_check_and_increment(ip)
    except Exception as e:
        print(f"[RateLimiter] DDB error for IP {ip}: {e}")
    # Then Redis if configured
    try:
        if _get_redis():
            return _redis_check_and_increment(ip)
    except Exception as e:
        print(f"[RateLimiter] Redis error for IP {ip}: {e}")
    # Fallback to memory
    return _mem_check_and_increment(ip)

def get_ip_quota(ip: str) -> dict:
    try:
        if TABLE_NAME:
            return _ddb_get_quota(ip)
    except Exception as e:
        print(f"[RateLimiter] DDB error for IP {ip}: {e}")
    try:
        if _get_redis():
            return _redis_get_quota(ip)
    except Exception as e:
        print(f"[RateLimiter] Redis error for IP {ip}: {e}")
    return _mem_get_quota(ip)
