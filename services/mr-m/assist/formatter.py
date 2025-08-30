# assist/formatters.py
def format_rows(rows):
    if not rows: return "_No results found._"
    hdr = "| Year | Title | Authors | Venue |\n|---|---|---|---|"
    lines = [f"| {r['year']} | {r['title']} | {r['authors']} | {r.get('venue','')} |" for r in rows]
    return "\n".join([hdr] + lines)

def format_coauthors(names):
    return "_No co-authors found._" if not names else "**Co-authors:** " + ", ".join(names)

def format_venues(items):
    if not items: return "_No venues found._"
    hdr = "| Venue | Count |\n|---|---|"
    lines = [f"| {v} | {c} |" for v, c in items]
    return "\n".join([hdr] + lines)
