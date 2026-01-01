"""
Quality scoring module for email and phone data.
"""

import json
import re
import sqlite3
from pathlib import Path
from typing import Dict, Any, Set


def get_db_path() -> str:
    """Get the path to the quality metadata SQLite database."""
    base_dir = Path(__file__).parent
    db_path = str(base_dir / "config" / "quality_metadata.db")
    return db_path


def init_quality_metadata_db(db_path: str = None) -> None:
    """Initialize the SQLite database with schema and default data."""
    if db_path is None:
        db_path = get_db_path()
    
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
    
    # Check if database is empty
    cursor.execute('SELECT COUNT(*) FROM personal_domains')
    if cursor.fetchone()[0] == 0:
        # Database is empty, populate with default data
        # Try to load from JSON first, otherwise use hardcoded defaults
        json_path = Path(__file__).parent / "config" / "quality_metadata.json"
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    personal_domains = data.get('personal_domains', [])
                    generic_prefixes = data.get('generic_prefixes', [])
                    department_prefixes = data.get('department_prefixes', [])
                    toll_free_codes = data.get('toll_free_codes', [])
            except (json.JSONDecodeError, KeyError):
                personal_domains = generic_prefixes = department_prefixes = toll_free_codes = []
        else:
            personal_domains = generic_prefixes = department_prefixes = toll_free_codes = []
        
        # Use defaults if JSON didn't provide data
        if not personal_domains:
            personal_domains = [
                'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
                'icloud.com', 'mail.com', 'protonmail.com', 'zoho.com', 'yandex.com',
                'live.com', 'msn.com', 'comcast.net', 'att.net', 'verizon.net'
            ]
        if not generic_prefixes:
            generic_prefixes = [
                'info', 'contact', 'sales', 'support', 'admin', 'help', 'service',
                'webmaster', 'postmaster', 'noreply', 'no-reply', 'hello', 'enquiries'
            ]
        if not department_prefixes:
            department_prefixes = [
                'hr', 'finance', 'marketing', 'legal', 'accounting', 'billing',
                'operations', 'engineering', 'it', 'tech', 'development'
            ]
        if not toll_free_codes:
            toll_free_codes = ['800', '888', '877', '866', '855', '844', '833']
        
        # Insert default data
        for domain in personal_domains:
            cursor.execute('INSERT OR IGNORE INTO personal_domains (domain) VALUES (?)', (domain,))
        
        for prefix in generic_prefixes:
            cursor.execute('INSERT OR IGNORE INTO generic_prefixes (prefix) VALUES (?)', (prefix,))
        
        for prefix in department_prefixes:
            cursor.execute('INSERT OR IGNORE INTO department_prefixes (prefix) VALUES (?)', (prefix,))
        
        for code in toll_free_codes:
            cursor.execute('INSERT OR IGNORE INTO toll_free_codes (code) VALUES (?)', (code,))
    
    conn.commit()
    conn.close()


def load_quality_metadata_from_db(db_path: str = None) -> Dict[str, Set[str]]:
    """Load quality metadata from SQLite database."""
    if db_path is None:
        db_path = get_db_path()
    
    # Initialize database if it doesn't exist
    init_quality_metadata_db(db_path)
    
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


# Lazy loading for performance - only load when needed
_QUALITY_METADATA = None
PERSONAL_DOMAINS = None
GENERIC_PREFIXES = None
DEPARTMENT_PREFIXES = None
TOLL_FREE_CODES = None


def _ensure_metadata_loaded():
    """Lazy load quality metadata on first use."""
    global _QUALITY_METADATA, PERSONAL_DOMAINS, GENERIC_PREFIXES, DEPARTMENT_PREFIXES, TOLL_FREE_CODES
    
    if _QUALITY_METADATA is None:
        _QUALITY_METADATA = load_quality_metadata_from_db()
        PERSONAL_DOMAINS = _QUALITY_METADATA['personal_domains']
        GENERIC_PREFIXES = _QUALITY_METADATA['generic_prefixes']
        DEPARTMENT_PREFIXES = _QUALITY_METADATA['department_prefixes']
        TOLL_FREE_CODES = _QUALITY_METADATA['toll_free_codes']


def calculate_email_quality(email: str, config: Dict = None) -> Dict[str, Any]:
    """Calculate quality score for an email address."""
    _ensure_metadata_loaded()
    """
    Calculate quality score for an email address.
    
    Returns dict with individual criteria scores and total.
    """
    result = {
        'valid_format': 0,
        'non_personal': 0,
        'non_generic': 0,
        'non_admin': 0,
        'non_department': 0,
        'total': 0
    }
    
    if not email:
        return result
    
    email = str(email).lower().strip()
    
    # Valid format check
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_pattern, email):
        result['valid_format'] = 20
    else:
        return result  # Invalid format, return early
    
    # Extract parts
    try:
        local_part, domain = email.rsplit('@', 1)
    except ValueError:
        return result
    
    # Non-personal domain check
    if domain not in PERSONAL_DOMAINS:
        result['non_personal'] = 20
    
    # Non-generic mailbox check
    if local_part not in GENERIC_PREFIXES:
        result['non_generic'] = 20
    
    # Non-admin check
    admin_prefixes = {'admin', 'support', 'help', 'helpdesk', 'service'}
    if local_part not in admin_prefixes:
        result['non_admin'] = 20
    
    # Non-department check
    if local_part not in DEPARTMENT_PREFIXES:
        result['non_department'] = 20
    
    result['total'] = sum(v for k, v in result.items() if k != 'total')
    return result


def calculate_phone_quality(phone: str, extension: str = None, config: Dict = None) -> Dict[str, Any]:
    """
    Calculate quality score for a phone number.
    
    Returns dict with individual criteria scores and total.
    """
    _ensure_metadata_loaded()
    
    result = {
        'has_10_digits': 0,
        'not_all_same': 0,
        'valid_area_code': 0,
        'valid_exchange': 0,
        'valid_line_number': 0,
        'not_toll_free': 0,
        'not_main_line': 0,
        'has_extension': 0,
        'high_quality': 0,
        'total': 0
    }
    
    if not phone:
        return result
    
    # Extract digits only
    digits = re.sub(r'\D', '', str(phone))
    
    # Remove leading 1 for US numbers
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    
    # Has 10 digits
    if len(digits) == 10:
        result['has_10_digits'] = 11
    else:
        return result  # Invalid length, return early
    
    # Not all same digits
    if len(set(digits)) > 1:
        result['not_all_same'] = 11
    
    area_code = digits[:3]
    exchange = digits[3:6]
    line_number = digits[6:]
    
    # Valid area code (not starting with 0 or 1)
    if area_code[0] not in ('0', '1'):
        result['valid_area_code'] = 11
    
    # Valid exchange (not starting with 0 or 1)
    if exchange[0] not in ('0', '1'):
        result['valid_exchange'] = 11
    
    # Valid line number (not all zeros)
    if line_number != '0000':
        result['valid_line_number'] = 11
    
    # Not toll-free
    if area_code not in TOLL_FREE_CODES:
        result['not_toll_free'] = 12
    
    # Not main line (doesn't end in 000 or 0000)
    is_main_line = line_number.endswith('000') or line_number.endswith('0000')
    if not is_main_line:
        result['not_main_line'] = 11
    
    # Has extension (bonus if main line has extension)
    if extension and str(extension).strip():
        result['has_extension'] = 11
    elif not is_main_line:
        result['has_extension'] = 5  # Partial credit if not main line
    
    # High quality (no sequential patterns, no repeating blocks)
    sequential = '0123456789' in digits or '9876543210' in digits
    repeating = any(digits[i:i+4] == digits[i]*4 for i in range(7))
    if not sequential and not repeating:
        result['high_quality'] = 11
    
    result['total'] = sum(v for k, v in result.items() if k != 'total')
    return result


def calculate_address_confidence(record: dict, matched_record: dict, scores: dict) -> float:
    """Calculate combined address match confidence."""
    weights = {
        'address1': 0.4,
        'address2': 0.1,
        'city': 0.2,
        'state': 0.15,
        'zip_code': 0.15
    }
    
    total = 0
    for field, weight in weights.items():
        score = scores.get(f'{field}_score', 0) or 0
        total += score * weight
    
    return round(total, 2)


def calculate_overall_confidence(scores: dict) -> float:
    """Calculate overall match confidence from individual scores."""
    weights = {
        'company_name_score': 0.35,
        'address1_score': 0.25,
        'email_score': 0.20,
        'phone_score': 0.20
    }
    
    total = 0
    total_weight = 0
    
    for field, weight in weights.items():
        score = scores.get(field)
        if score is not None and score > 0:
            total += score * weight
            total_weight += weight
    
    if total_weight > 0:
        return round(total / total_weight * (total_weight / sum(weights.values())), 2)
    return 0.0

