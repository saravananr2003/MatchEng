"""
Similarity calculation module for the matching engine.
Provides various similarity algorithms for comparing field values.
"""

import re
from typing import Optional
from rapidfuzz import fuzz


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    text = str(text).lower().strip()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_company_name(name: str) -> str:
    """Normalize company name by removing common suffixes."""
    if not name:
        return ""
    
    name = normalize_text(name)
    
    # Remove common suffixes
    suffixes = [
        r'\b(inc|incorporated|corp|corporation|llc|ltd|limited|co|company)\b',
        r'\b(plc|lp|llp|pllc|pc|pa|na)\b',
        r'\b(the|a|an)\b'
    ]
    
    for suffix in suffixes:
        name = re.sub(suffix, '', name, flags=re.IGNORECASE)
    
    return re.sub(r'\s+', ' ', name).strip()


def normalize_address(address: str) -> str:
    """Normalize address by standardizing abbreviations."""
    if not address:
        return ""
    
    address = normalize_text(address)
    
    # Standard abbreviations
    replacements = {
        r'\bstreet\b': 'st',
        r'\bavenue\b': 'ave',
        r'\broad\b': 'rd',
        r'\bboulevard\b': 'blvd',
        r'\bdrive\b': 'dr',
        r'\blane\b': 'ln',
        r'\bcourt\b': 'ct',
        r'\bplace\b': 'pl',
        r'\bsuite\b': 'ste',
        r'\bapartment\b': 'apt',
        r'\bbuilding\b': 'bldg',
        r'\bfloor\b': 'fl',
        r'\bnorth\b': 'n',
        r'\bsouth\b': 's',
        r'\beast\b': 'e',
        r'\bwest\b': 'w',
    }
    
    for pattern, replacement in replacements.items():
        address = re.sub(pattern, replacement, address)
    
    return address


def normalize_phone(phone: str) -> str:
    """Normalize phone number to digits only."""
    if not phone:
        return ""
    
    digits = re.sub(r'\D', '', str(phone))
    
    # Remove leading 1 for US numbers
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    
    return digits


def normalize_email(email: str) -> str:
    """Normalize email address."""
    if not email:
        return ""
    return str(email).lower().strip()


def calculate_similarity(value1: str, value2: str, method: str = 'token_sort') -> float:
    """
    Calculate similarity between two strings.
    
    Args:
        value1: First string
        value2: Second string
        method: Similarity method ('ratio', 'token_sort', 'token_set', 'partial')
    
    Returns:
        Similarity score from 0 to 100
    """
    if not value1 or not value2:
        return 0.0
    
    v1 = str(value1).strip()
    v2 = str(value2).strip()
    
    if not v1 or not v2:
        return 0.0
    
    if method == 'ratio':
        return fuzz.ratio(v1, v2)
    elif method == 'token_sort':
        return fuzz.token_sort_ratio(v1, v2)
    elif method == 'token_set':
        return fuzz.token_set_ratio(v1, v2)
    elif method == 'partial':
        return fuzz.partial_ratio(v1, v2)
    else:
        return fuzz.token_sort_ratio(v1, v2)


def compare_company_names(name1: str, name2: str) -> float:
    """Compare two company names with normalization."""
    n1 = normalize_company_name(name1)
    n2 = normalize_company_name(name2)
    return calculate_similarity(n1, n2, 'token_sort')


def compare_addresses(addr1: str, addr2: str) -> float:
    """Compare two addresses with normalization."""
    a1 = normalize_address(addr1)
    a2 = normalize_address(addr2)
    return calculate_similarity(a1, a2, 'token_sort')


def compare_phones(phone1: str, phone2: str) -> float:
    """Compare two phone numbers."""
    p1 = normalize_phone(phone1)
    p2 = normalize_phone(phone2)
    
    if not p1 or not p2:
        return 0.0
    
    # Exact match for phones
    return 100.0 if p1 == p2 else 0.0


def compare_emails(email1: str, email2: str) -> float:
    """Compare two email addresses."""
    e1 = normalize_email(email1)
    e2 = normalize_email(email2)
    
    if not e1 or not e2:
        return 0.0
    
    # Exact match for emails
    return 100.0 if e1 == e2 else 0.0


def create_blocking_key(record: dict) -> str:
    """
    Create a blocking key for grouping similar records.
    Only records with the same blocking key are compared.
    """
    company = normalize_company_name(record.get('COMPANY_NAME', '') or '')[:3]
    zip_code = str(record.get('ZIP_CODE', '') or '')[:5]
    phone = normalize_phone(record.get('PHONE_NUMBER', '') or '')[-4:]
    
    return f"{company}_{zip_code}_{phone}".lower()

