import sqlite3
from typing import Any, Dict, List, Optional


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db(db_path: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                company_name TEXT,
                company_name_norm TEXT,
                address TEXT,
                address_norm TEXT,
                phone TEXT,
                phone_norm TEXT,
                name_key TEXT,
                addr_key TEXT,
                dedup_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(source_type, source_id)
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_records_phone_norm ON records(phone_norm);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_records_name_key ON records(name_key);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_records_addr_key ON records(addr_key);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_records_dedup_id ON records(dedup_id);")


def insert_record(db_path: str, rec: Dict[str, Any]) -> None:
    cols = list(rec.keys())
    vals = [rec[c] for c in cols]
    placeholders = ",".join(["?"] * len(cols))
    sql = f"INSERT OR REPLACE INTO records ({','.join(cols)}) VALUES ({placeholders})"
    with connect(db_path) as conn:
        conn.execute(sql, vals)
        conn.commit()


def find_candidates_by_phone(db_path: str, phone_norm: str) -> List[Dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT source_type, source_id, company_name_norm, address_norm, phone_norm, dedup_id
            FROM records
            WHERE phone_norm = ?
            ORDER BY id DESC
            LIMIT 500
            """,
            (phone_norm,),
        ).fetchall()
    return [dict(r) for r in rows]


def find_candidates_by_keys(
    db_path: str, *, name_key: Optional[str], addr_key: Optional[str], limit: int = 500
) -> List[Dict[str, Any]]:
    if not name_key and not addr_key:
        return []

    clauses = []
    params: List[Any] = []
    if name_key:
        clauses.append("name_key = ?")
        params.append(name_key)
    if addr_key:
        clauses.append("addr_key = ?")
        params.append(addr_key)

    where = " OR ".join(clauses)
    with connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT source_type, source_id, company_name_norm, address_norm, phone_norm, dedup_id
            FROM records
            WHERE {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()

    return [dict(r) for r in rows]
