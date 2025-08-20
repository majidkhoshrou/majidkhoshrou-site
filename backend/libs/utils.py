# backend/libs/utils.py
import os
import secrets
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError


@lru_cache(maxsize=None)
def _ssm_client(region: str | None = None):
    region = region or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "eu-central-1"
    return boto3.client("ssm", region_name=region)


def _safe_default(name: str, default: str | None):
    # ensure Flask SECRET_KEY is never None so app can start
    if name == "SECRET_KEY" and not default:
        return secrets.token_hex(32)
    return default


@lru_cache(maxsize=None)
def ssm_get(param_name: str, *, decrypt: bool = True, region: str | None = None) -> str | None:
    try:
        resp = _ssm_client(region).get_parameter(Name=param_name, WithDecryption=decrypt)
        return resp["Parameter"]["Value"]
    except ClientError as e:
        print(f"[warn] SSM get_parameter failed for {param_name}: {e}")
        return None


def getenv_or_ssm(env_name: str, ssm_path: str | None = None, *, decrypt: bool = True, default: str | None = None) -> str | None:
    v = os.getenv(env_name)
    if v is not None:
        v = v.strip()
        if v:                      # only accept non-empty env values
            return v
    if ssm_path:
        v = ssm_get(ssm_path, decrypt=decrypt)
        if v is not None:
            v = v.strip()
            if v:                  # only accept non-empty SSM values
                return v
    return _safe_default(env_name, default)


# ------------------------------
# 🔐 Lazy, cached getters (as requested)
# ------------------------------
@lru_cache(maxsize=1)
def get_secret_key() -> str:
    # env FIRST, else SSM
    return getenv_or_ssm("SECRET_KEY", "/majidkhoshrou/prod/SECRET_KEY") or secrets.token_hex(32)


@lru_cache(maxsize=1)
def _get_openai_api_key_cached() -> str:
    # env (non-empty) else SSM (non-empty); returns "" if unavailable
    return getenv_or_ssm("OPENAI_API_KEY", "/majidkhoshrou/prod/OPENAI_API_KEY") or ""

def get_openai_api_key() -> str:
    v = _get_openai_api_key_cached()
    if v:
        return v
    # don't keep empty in cache — clear and let the next call retry
    try:
        _get_openai_api_key_cached.cache_clear()
    except Exception:
        pass
    try:
        ssm_get.cache_clear()  # in case the first SSM read failed/transient
    except Exception:
        pass
    return ""

@lru_cache(maxsize=1)
def get_turnstile_site_key() -> str:
    return getenv_or_ssm(
        "TURNSTILE_SITE_KEY",
        "/majidkhoshrou/prod/TURNSTILE_SITE_KEY",
        decrypt=False,
        default=""
    ) or ""


# Optional helper so app.py doesn’t create the client at import time
_openai_client = None
def get_openai_client():
    """Create the OpenAI client lazily and cache it."""
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI  # import here to avoid import-time work
        api_key = get_openai_api_key()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client
