"""
Dedup key generation and persistence module.
Manages unique identifiers for matched record groups.
"""

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from similarity import normalize_company_name, normalize_address, normalize_phone


DEDUP_FILE = "datafiles/models/dedup_mappings.json"


def generate_data_hash(record: dict) -> str:
    """Generate a hash from key record fields for dedup lookup."""
    components = [
        str(record.get('SOURCE_TYPE', '') or '').strip().upper(),
        str(record.get('SOURCE_ID', '') or '').strip(),
        normalize_company_name(record.get('COMPANY_NAME', '') or ''),
        normalize_address(record.get('ADDRESS_LINE_1', '') or ''),
        normalize_phone(record.get('PHONE_NUMBER', '') or ''),
    ]
    
    combined = '|'.join(components)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def generate_dedup_key() -> str:
    """Generate a new unique dedup key (UUID)."""
    return str(uuid.uuid4())


def load_dedup_mappings(file_path: str = DEDUP_FILE) -> dict:
    """Load persistent dedup mappings from file."""
    try:
        path = Path(file_path)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
    except (json.JSONDecodeError, IOError):
        pass
    
    return {
        "version": "2.0",
        "data_hash_to_key": {},
        "key_to_data_hashes": {},
        "key_to_identifiers": {},
        "metadata": {
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "total_runs": 0,
            "version": "2.0"
        }
    }


def save_dedup_mappings(mappings: dict, file_path: str = DEDUP_FILE) -> bool:
    """Save dedup mappings to file."""
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        mappings["metadata"]["last_updated"] = datetime.utcnow().isoformat()
        mappings["metadata"]["total_runs"] = mappings["metadata"].get("total_runs", 0) + 1
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=2)
        return True
    except IOError:
        return False


def get_or_create_dedup_key(record: dict, mappings: dict) -> tuple:
    """
    Get existing dedup key or create new one for a record.
    
    Returns:
        Tuple of (dedup_key, is_new)
    """
    data_hash = generate_data_hash(record)
    
    # Check if we've seen this exact record before
    if data_hash in mappings.get("data_hash_to_key", {}):
        return mappings["data_hash_to_key"][data_hash], False
    
    # Create new dedup key
    dedup_key = generate_dedup_key()
    
    # Store mappings
    if "data_hash_to_key" not in mappings:
        mappings["data_hash_to_key"] = {}
    if "key_to_data_hashes" not in mappings:
        mappings["key_to_data_hashes"] = {}
    if "key_to_identifiers" not in mappings:
        mappings["key_to_identifiers"] = {}
    
    mappings["data_hash_to_key"][data_hash] = dedup_key
    mappings["key_to_data_hashes"][dedup_key] = [data_hash]
    
    # Store identifier info
    identifier = f"{record.get('SOURCE_TYPE', '')}:{record.get('SOURCE_ID', '')}"
    mappings["key_to_identifiers"][dedup_key] = [identifier]
    
    return dedup_key, True


def link_records(dedup_key: str, record: dict, mappings: dict) -> None:
    """Link a record to an existing dedup key."""
    data_hash = generate_data_hash(record)
    
    if "data_hash_to_key" not in mappings:
        mappings["data_hash_to_key"] = {}
    if "key_to_data_hashes" not in mappings:
        mappings["key_to_data_hashes"] = {}
    if "key_to_identifiers" not in mappings:
        mappings["key_to_identifiers"] = {}
    
    mappings["data_hash_to_key"][data_hash] = dedup_key
    
    if dedup_key not in mappings["key_to_data_hashes"]:
        mappings["key_to_data_hashes"][dedup_key] = []
    if data_hash not in mappings["key_to_data_hashes"][dedup_key]:
        mappings["key_to_data_hashes"][dedup_key].append(data_hash)
    
    identifier = f"{record.get('SOURCE_TYPE', '')}:{record.get('SOURCE_ID', '')}"
    if dedup_key not in mappings["key_to_identifiers"]:
        mappings["key_to_identifiers"][dedup_key] = []
    if identifier not in mappings["key_to_identifiers"][dedup_key]:
        mappings["key_to_identifiers"][dedup_key].append(identifier)


def get_matched_identifiers(dedup_key: str, mappings: dict) -> List[str]:
    """Get all identifiers linked to a dedup key."""
    return mappings.get("key_to_identifiers", {}).get(dedup_key, [])

