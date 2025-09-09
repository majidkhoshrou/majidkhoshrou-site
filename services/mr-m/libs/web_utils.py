# libs/web_utils.py
import time
import random
import requests
from requests.adapters import HTTPAdapter, Retry
from urllib.parse import urlparse, quote
import urllib.robotparser as robotparser

# ---------------- Session ----------------
def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36; "
            "mr-m/knowledge-crawler (+contact: you@example.com)"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8",
    })
    retries = Retry(
        total=5,
        backoff_factor=1.2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "GET"]
    )
    s.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=10))
    s.mount("http://", HTTPAdapter(max_retries=retries, pool_maxsize=10))
    return s

SESSION = build_session()

# ---------------- Robots.txt ----------------
_ROBOTS_CACHE = {}
def robots_allows(url: str, user_agent: str = None) -> bool:
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        rp = _ROBOTS_CACHE.get(base)
        if rp is None:
            rp = robotparser.RobotFileParser()
            rp.set_url(f"{base}/robots.txt")
            try:
                rp.read()
            except Exception:
                _ROBOTS_CACHE[base] = rp
                return False
            _ROBOTS_CACHE[base] = rp
        return rp.can_fetch(user_agent or SESSION.headers.get("User-Agent", "*"), url)
    except Exception:
        return False

# ---------------- Domain helpers ----------------
def is_wikipedia(url: str) -> bool:
    return "wikipedia.org" in urlparse(url).netloc.lower()

def is_google_scholar(url: str) -> bool:
    return urlparse(url).netloc.lower().startswith("scholar.google.")

# ---------------- Wikipedia helpers ----------------
def _wiki_title_from_url(url: str) -> str:
    """
    Extract the /wiki/Title part, strip fragments, and keep underscores (REST likes underscores).
    """
    path = urlparse(url).path  # e.g., /wiki/Delft_University_of_Technology
    if "/wiki/" in path:
        title = path.split("/wiki/", 1)[1]
    else:
        title = path.strip("/")

    # Drop any fragments like ...#Section
    title = title.split("#", 1)[0]
    # Some links include percent-encoding already; quoting again is fine.
    return title or "Main_Page"

def _wiki_summary(title: str) -> dict | None:
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
    r = SESSION.get(url, timeout=20)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()

def _wiki_plain(title: str) -> str | None:
    url = f"https://en.wikipedia.org/api/rest_v1/page/plain/{quote(title)}"
    r = SESSION.get(url, timeout=20)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.text

def _wiki_extracts_fallback(title: str) -> tuple[str, str] | None:
    """
    Fallback to the classic MediaWiki API to get plaintext extracts.
    Returns (resolved_title, extract) or None.
    """
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "format": "json",
        "redirects": "1",
        "titles": title,
    }
    r = SESSION.get("https://en.wikipedia.org/w/api.php", params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None
    page = next(iter(pages.values()))
    extract = page.get("extract", "")
    resolved = page.get("title") or title.replace("_", " ")
    if not extract:
        return None
    return resolved, extract

def fetch_wikipedia_text(url: str) -> tuple[str, str]:
    """
    Robust Wikipedia fetcher:
      1) Resolve canonical title via REST /summary (follows redirects)
      2) Try REST /page/plain/{title} for full plain text
      3) Fallback to MediaWiki API extracts (plaintext)
    Returns (title, text). Raises on hard failures.
    """
    # 1) normalize and resolve canonical title
    raw_title = _wiki_title_from_url(url)

    summary = _wiki_summary(raw_title)
    if summary is not None and summary.get("title"):
        resolved_title = summary["title"].replace(" ", "_")  # plain endpoint likes underscores
    else:
        # try a second normalization (swap underscores/spaces) before falling back
        alt_title = raw_title.replace("_", " ")
        summary = _wiki_summary(alt_title)
        if summary is not None and summary.get("title"):
            resolved_title = summary["title"].replace(" ", "_")
        else:
            resolved_title = raw_title  # last resort

    # 2) try REST plain text
    text = _wiki_plain(resolved_title)
    if text:
        # prefer display title from summary if available
        display_title = (summary.get("title") if summary else resolved_title.replace("_", " "))
        return display_title, text

    # 3) fallback to MediaWiki extracts (usually succeeds even when REST plain 404s)
    fallback = _wiki_extracts_fallback(resolved_title)
    if fallback:
        return fallback

    # If absolutely nothing worked, raise a helpful error
    raise requests.HTTPError(f"Wikipedia content not found for title '{resolved_title}'")

# ---------------- Polite generic fetch ----------------
def polite_get(url: str, *, min_delay=0.7, max_delay=1.6) -> requests.Response:
    if not robots_allows(url):
        raise requests.HTTPError(f"Blocked by robots.txt for {url}")
    time.sleep(random.uniform(min_delay, max_delay))
    resp = SESSION.get(url, timeout=20)
    resp.raise_for_status()
    return resp
