"""
Migration script to convert quality_metadata.json to SQLite database.
This script is optional - the database will be auto-created when quality_scorer.py is imported.
Run this if you want to explicitly migrate from JSON to SQLite.
"""

import json
import sqlite3
from pathlib import Path


def migrate_json_to_sqlite(json_path: str = None, db_path: str = None):
    """Migrate quality metadata from JSON to SQLite database."""
    if json_path is None:
        base_dir = Path(__file__).parent
        json_path = str(base_dir / "config" / "quality_metadata.json")
    
    if db_path is None:
        base_dir = Path(__file__).parent
        db_path = str(base_dir / "config" / "quality_metadata.db")
    
    # Check if JSON file exists
    if not Path(json_path).exists():
        print(f"⚠ JSON file not found at {json_path}")
        print("  Database will be initialized with default values when quality_scorer.py is imported.")
        return
    
    # Load JSON data
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"⚠ Error reading JSON file: {e}")
        return
    
    # Create SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS personal_domains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS generic_prefixes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prefix TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS department_prefixes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prefix TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS toll_free_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Clear existing data (optional - comment out if you want to keep existing data)
    cursor.execute('DELETE FROM personal_domains')
    cursor.execute('DELETE FROM generic_prefixes')
    cursor.execute('DELETE FROM department_prefixes')
    cursor.execute('DELETE FROM toll_free_codes')
    
    # Insert data
    for domain in data.get('personal_domains', []):
        cursor.execute('INSERT INTO personal_domains (domain) VALUES (?)', (domain,))
    
    for prefix in data.get('generic_prefixes', []):
        cursor.execute('INSERT INTO generic_prefixes (prefix) VALUES (?)', (prefix,))
    
    for prefix in data.get('department_prefixes', []):
        cursor.execute('INSERT INTO department_prefixes (prefix) VALUES (?)', (prefix,))
    
    for code in data.get('toll_free_codes', []):
        cursor.execute('INSERT INTO toll_free_codes (code) VALUES (?)', (code,))
    
    conn.commit()
    conn.close()
    
    print(f"✓ Migration complete! Database created at: {db_path}")
    print(f"  - Personal domains: {len(data.get('personal_domains', []))}")
    print(f"  - Generic prefixes: {len(data.get('generic_prefixes', []))}")
    print(f"  - Department prefixes: {len(data.get('department_prefixes', []))}")
    print(f"  - Toll-free codes: {len(data.get('toll_free_codes', []))}")


if __name__ == '__main__':
    migrate_json_to_sqlite()

