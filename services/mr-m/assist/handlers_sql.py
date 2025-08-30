# services/mr-m/assist/handlers_sql.py
import sqlite3, os
from pathlib import Path

# Resolve to /app/data/artifacts/catalog.db in the container
_THIS_DIR = Path(__file__).resolve().parent
_DEFAULT_DB = (_THIS_DIR / ".." / "data" / "artifacts" / "catalog.db").resolve()

DB_PATH = os.getenv("DB_PATH", str(_DEFAULT_DB))

def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def latest_publications(author: str, limit: int = 5, first: bool = False):
    order = "ASC" if first else "DESC"
    sql = f"""
    SELECT p.year, p.title, p.venue,
           GROUP_CONCAT(a2.author, ', ') AS authors
    FROM publications p
    JOIN pub_authors a  ON a.pub_id  = p.id
    JOIN pub_authors a2 ON a2.pub_id = p.id
    WHERE LOWER(a.author) = LOWER(?)
    GROUP BY p.id
    ORDER BY p.year {order}
    LIMIT ?
    """
    with _conn() as con:
        cur = con.cursor()
        cur.execute(sql, (author, limit))
        return [dict(r) for r in cur.fetchall()]

def coauthors_of(author: str):
    sql = """
    SELECT DISTINCT a2.author
    FROM pub_authors m
    JOIN pub_authors a2 ON a2.pub_id = m.pub_id
    WHERE LOWER(m.author) = LOWER(?) AND LOWER(a2.author) <> LOWER(?)
    ORDER BY a2.author
    """
    with _conn() as con:
        cur = con.cursor()
        cur.execute(sql, (author, author))
        return [r[0] for r in cur.fetchall()]

def venues_of(author: str):
    sql = """
    SELECT COALESCE(p.venue,'') AS venue, COUNT(*) AS count
    FROM publications p
    JOIN pub_authors a ON a.pub_id = p.id
    WHERE LOWER(a.author) = LOWER(?)
    GROUP BY COALESCE(p.venue,'')
    ORDER BY count DESC, venue ASC
    """
    with _conn() as con:
        cur = con.cursor()
        cur.execute(sql, (author,))
        return [tuple(r) for r in cur.fetchall()]
