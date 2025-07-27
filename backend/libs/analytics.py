from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, Any, List
from flask import request, has_request_context
from urllib.parse import urlparse
import requests
import json
import re

def parse_device(user_agent: str) -> str:
    if not user_agent:
        return "Unknown"

    ua = user_agent.lower()
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "Mobile"
    elif "ipad" in ua or "tablet" in ua:
        return "Tablet"
    return "Desktop"


def anonymize_ip(ip: str) -> str:
    if ":" in ip:
        return re.sub(r'(:[^:]+){2}$', '::****', ip)
    parts = ip.split('.')
    return '.'.join(parts[:2]) + '.***.***' if len(parts) == 4 else ip

def log_visit(log_dir: Path = None) -> None:
    if not has_request_context():
        return

    log_dir = log_dir or Path("data")

    TAB_NAME_MAP = {
        "/": "Home",
        "/about": "About Me",
        "/projects": "Projects",
        "/research": "Research",
        "/talks": "Talks",
        "/ask-mr-m": "Ask Mr. M",
        "/analytics": "Analytics",
        "/contact": "Contact"
    }

    referer = request.headers.get("Referer", "")
    parsed = urlparse(referer)
    ref_path = parsed.path

    # Normalize to standard path
    path = ref_path if ref_path else request.path or "/"
    if path in ["/index.html", "/home"]:
        path = "/"

    if path not in TAB_NAME_MAP:
        return

    tab_name = TAB_NAME_MAP[path]

    ip_raw = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent = request.headers.get("User-Agent", "")
    device = parse_device(user_agent)

    if ip_raw.startswith("127.") or ip_raw == "localhost":
        country = "Local"
        latitude = None
        longitude = None
        proxy = False
    else:
        try:
            geo = requests.get(f"https://ipapi.co/{ip_raw}/json/").json()
            country = geo.get("country_name", "Unknown")
            latitude = geo.get("latitude")
            longitude = geo.get("longitude")
            proxy = geo.get("proxy", False)
        except Exception:
            country = "Unknown"
            latitude = None
            longitude = None
            proxy = False

    log_entry = {
        "ip": anonymize_ip(ip_raw),
        "country": country,
        "device": device,
        "user_agent": user_agent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "proxy": proxy,
        "latitude": latitude,
        "longitude": longitude,
        "path": path,
        "tab": tab_name  # ✅ readable tab name
    }

    log_file = log_dir / "visits.json"
    log_dir.mkdir(parents=True, exist_ok=True)

    logs: List[Dict[str, Any]] = []
    if log_file.exists():
        with log_file.open("r", encoding="utf-8") as f:
            logs = json.load(f)

    logs.append(log_entry)

    with log_file.open("w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)


def load_analytics_data(log_dir: Path = None) -> List[Dict[str, Any]]:
    log_dir = log_dir or Path("data")
    log_file = log_dir / "visits.json"
    if not log_file.exists():
        return []
    with log_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def summarize_analytics(log_dir: Path = None) -> Dict[str, Any]:
    log_dir = log_dir or Path("data")
    visits = load_analytics_data(log_dir)

    by_country = defaultdict(int)
    by_device = defaultdict(int)
    by_ip = defaultdict(int)
    by_day = defaultdict(int)
    by_path = defaultdict(int)
    by_tab = defaultdict(int)  # ✅ new

    vpn_count = 0
    unknown_country_count = 0

    for visit in visits:
        country = visit.get("country", "Unknown")
        device = visit.get("device", "Unknown")
        ip = visit.get("ip", "Unknown")
        path = visit.get("path", "Unknown")
        tab = visit.get("tab", "Unknown")  # ✅ new

        by_country[country] += 1
        by_device[device] += 1
        by_ip[ip] += 1
        by_path[path] += 1
        by_tab[tab] += 1  # ✅ new

        if country == "Unknown":
            unknown_country_count += 1
        if visit.get("proxy") is True:
            vpn_count += 1

        timestamp = visit.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            by_day[dt.date().isoformat()] += 1
        except Exception:
            continue

    most_visited_path = max(by_path.items(), key=lambda x: x[1])[0] if by_path else None
    most_visited_tab = max(by_tab.items(), key=lambda x: x[1])[0] if by_tab else None

    return {
        "total_visits": len(visits),
        "by_country": dict(by_country),
        "by_device": dict(by_device),
        "by_ip": dict(by_ip),
        "by_day": dict(by_day),
        "by_path": dict(by_path),
        "by_tab": dict(by_tab),  # ✅ added
        "most_visited_path": most_visited_path,
        "most_visited_tab": most_visited_tab,  # ✅ added
        "unknown_country_count": unknown_country_count,
        "vpn_count": vpn_count
    }
