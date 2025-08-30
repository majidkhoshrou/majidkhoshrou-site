# services/mr-m/assist/names.py
import re
from unicodedata import normalize

_CANON = "Khoshrou, Abdolrahman"
_YOU = {
    "majid", "maajid", "mjid", "majd",
    "abdolrahman khoshrou", "khoshrou abdolrahman", "khoshrou",
    "abdolrahman", "a khoshrou", "a. khoshrou",
    "khoshroo", "khoshro", "khohrou", "khosrou"
}
_BOT = {"mr m", "mr-m", "mr m.", "mrm", "mr m ai", "mr m assistant"}

def canonicalize_author(name: str | None) -> str | None:
    if not name:
        return None
    s = normalize("NFKD", name).encode("ascii", "ignore").decode().lower().strip()
    s = re.sub(r"[\s\.\-]+", " ", s)
    if s in _BOT or " mr m" in f" {s} ":
        return None
    if s in _YOU or ("majid" in s and "khosh" in s) or s.startswith("khosh"):
        return _CANON
    return name
