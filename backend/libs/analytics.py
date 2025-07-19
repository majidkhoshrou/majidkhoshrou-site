from pathlib import Path
import json
import requests
from datetime import datetime
from flask import request
from collections import defaultdict
from typing import Dict, Any


def parse_device(user_agent: str) -> str:
    if not user_agent:
        return "Unknown"
    
    ua = user_agent.lower()
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "Mobile"
    elif "ipad" in ua or "tablet" in ua:
        return "Tablet"
    else:
        return "Desktop"


def log_visit(log_dir: Path = Path("data")):
    log_file = log_dir / "visits.json"
    log_dir.mkdir(parents=True, exist_ok=True)

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent = request.headers.get("User-Agent", "")
    device = parse_device(user_agent)

    try:
        response = requests.get(f"https://ipapi.co/{ip}/json/")
        if response.status_code == 200:
            geo = response.json()
            country = geo.get("country_name", "Unknown")
        else:
            country = "Unknown"
    except Exception:
        country = "Unknown"

    log_entry = {
        "ip": ip,
        "country": country,
        "device": device,
        "user_agent": user_agent,
        "timestamp": datetime.utcnow().isoformat()
    }

    logs = []
    if log_file.exists():
        with log_file.open("r", encoding="utf-8") as f:
            logs = json.load(f)

    logs.append(log_entry)

    with log_file.open("w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)


def load_analytics_data(log_dir: Path = Path("data")) -> list:
    log_file = log_dir / "visits.json"
    if not log_file.exists():
        return []
    with log_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def summarize_analytics() -> Dict[str, Any]:
    data_path = Path(__file__).resolve().parent.parent / "data" / "visits.json"

    if not data_path.exists():
        return {
            "total_visits": 0,
            "by_country": {},
            "by_device": {},
            "by_ip": {},
            "by_day": {}
        }

    with data_path.open("r", encoding="utf-8") as f:
        visits = json.load(f)

    by_country = defaultdict(int)
    by_device = defaultdict(int)
    by_ip = defaultdict(int)
    by_day = defaultdict(int)

    for visit in visits:
        by_country[visit.get("country", "Unknown")] += 1
        by_device[visit.get("device", "Unknown")] += 1
        by_ip[visit.get("ip", "Unknown")] += 1

        timestamp = visit.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            by_day[dt.date().isoformat()] += 1
        except Exception:
            continue

    return {
        "total_visits": len(visits),
        "by_country": dict(by_country),
        "by_device": dict(by_device),
        "by_ip": dict(by_ip),
        "by_day": dict(by_day)
    }
