# services/mr-m/scripts/seed_sqlite.py
import sqlite3, pandas as pd, pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]
DB_PATH = BASE / "data" / "artifacts" / "catalog.db"
PUBS_CSV = BASE / "data" / "artifacts" / "structured_publications.csv"
AUTH_CSV = BASE / "data" / "artifacts" / "pub_authors.csv"

con = sqlite3.connect(DB_PATH)
con.executescript("""
PRAGMA foreign_keys=ON;

DROP TABLE IF EXISTS publications;
DROP TABLE IF EXISTS pub_authors;

CREATE TABLE publications (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  year INT NOT NULL,
  publication_type TEXT NOT NULL,
  venue TEXT
);

CREATE TABLE pub_authors (
  pub_id TEXT NOT NULL,
  author TEXT NOT NULL,
  ord INT NOT NULL,
  FOREIGN KEY(pub_id) REFERENCES publications(id)
);

CREATE INDEX IF NOT EXISTS idx_pub_year ON publications(year);
CREATE INDEX IF NOT EXISTS idx_auth_author ON pub_authors(author);
CREATE INDEX IF NOT EXISTS idx_auth_pub ON pub_authors(pub_id);
""")

# --- Import publications: drop the 'authors' CSV column (we store authors in pub_authors)
df_pubs = pd.read_csv(PUBS_CSV)
if "authors" in df_pubs.columns:
    df_pubs = df_pubs.drop(columns=["authors"])

df_pubs.to_sql("publications", con, if_exists="append", index=False)

# --- Import pub_authors as-is
pd.read_csv(AUTH_CSV).to_sql("pub_authors", con, if_exists="append", index=False)

con.close()
print(f"Seeded SQLite DB at {DB_PATH}")
