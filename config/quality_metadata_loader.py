"""
Example implementation: Load quality metadata from SQLite database.
This is an alternative to loading from JSON.
"""

import sqlite3
from pathlib import Path
from typing import Dict, Set


def load_quality_metadata_from_sqlite(db_path: str = None) -> Dict[str, Set[str]]:
    """
    Load quality metadata from SQLite database.
    
    Usage:
        metadata = load_quality_metadata_from_sqlite()
        personal_domains = metadata['personal_domains']
    """
    if db_path is None:
        base_dir = Path(__file__).parent
        db_path = str(base_dir / "quality_metadata.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Load personal domains
    cursor.execute('SELECT domain FROM personal_domains')
    personal_domains = {row[0] for row in cursor.fetchall()}
    
    # Load generic prefixes
    cursor.execute('SELECT prefix FROM generic_prefixes')
    generic_prefixes = {row[0] for row in cursor.fetchall()}
    
    # Load department prefixes
    cursor.execute('SELECT prefix FROM department_prefixes')
    department_prefixes = {row[0] for row in cursor.fetchall()}
    
    # Load toll-free codes
    cursor.execute('SELECT code FROM toll_free_codes')
    toll_free_codes = {row[0] for row in cursor.fetchall()}
    
    conn.close()
    
    return {
        'personal_domains': personal_domains,
        'generic_prefixes': generic_prefixes,
        'department_prefixes': department_prefixes,
        'toll_free_codes': toll_free_codes
    }


def add_personal_domain(domain: str, db_path: str = None):
    """Add a new personal domain to the database."""
    if db_path is None:
        base_dir = Path(__file__).parent
        db_path = str(base_dir / "quality_metadata.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO personal_domains (domain) VALUES (?)', (domain,))
    conn.commit()
    conn.close()


def remove_personal_domain(domain: str, db_path: str = None):
    """Remove a personal domain from the database."""
    if db_path is None:
        base_dir = Path(__file__).parent
        db_path = str(base_dir / "quality_metadata.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM personal_domains WHERE domain = ?', (domain,))
    conn.commit()
    conn.close()


# Similar functions can be created for other metadata types

