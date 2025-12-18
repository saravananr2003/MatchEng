"""
Core matching engine module.
Implements the main matching pipeline for record deduplication.
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from similarity import (
    compare_company_names, compare_addresses, compare_phones, compare_emails,
    normalize_company_name, normalize_address, normalize_phone, normalize_email,
    create_blocking_key, calculate_similarity
)
from dedup import (
    load_dedup_mappings, save_dedup_mappings, get_or_create_dedup_key,
    link_records, get_matched_identifiers
)
from quality_scorer import (
    calculate_email_quality, calculate_phone_quality,
    calculate_address_confidence, calculate_overall_confidence
)


def load_rules(rules_path: str = "config/rules.json") -> Dict:
    """Load matching rules from configuration."""
    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"rules": {}}


def load_settings(settings_path: str = "config/settings.json") -> Dict:
    """Load settings from configuration."""
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def evaluate_condition(record1: dict, record2: dict, condition: dict) -> bool:
    """Evaluate a single rule condition."""
    field = condition.get('field', '')
    threshold = float(condition.get('percentage', 0) or 0)
    include = condition.get('include', True)
    blank_required = condition.get('blank', False)
    blank_allowed = condition.get('blank_allowed', False)
    
    val1 = str(record1.get(field, '') or '').strip()
    val2 = str(record2.get(field, '') or '').strip()
    
    # Handle blank conditions
    if blank_required:
        # Both must be blank
        return not val1 and not val2
    
    # If either is blank
    if not val1 or not val2:
        return blank_allowed
    
    # Calculate similarity based on field type
    if 'COMPANY' in field.upper() or 'NAME' in field.upper():
        similarity = compare_company_names(val1, val2)
    elif 'ADDRESS' in field.upper():
        similarity = compare_addresses(val1, val2)
    elif 'PHONE' in field.upper():
        similarity = compare_phones(val1, val2)
    elif 'EMAIL' in field.upper():
        similarity = compare_emails(val1, val2)
    else:
        similarity = calculate_similarity(val1, val2)
    
    if include:
        return similarity >= threshold
    else:
        return similarity < threshold


def evaluate_rule(record1: dict, record2: dict, rule: dict) -> Tuple[bool, Dict]:
    """
    Evaluate if two records match according to a rule.
    
    Returns:
        Tuple of (is_match, scores_dict)
    """
    if not rule.get('enabled', True):
        return False, {}
    
    conditions = rule.get('conditions', [])
    if not conditions:
        return False, {}
    
    scores = {}
    
    for condition in conditions:
        field = condition.get('field', '')
        
        # Calculate score for tracking
        val1 = str(record1.get(field, '') or '').strip()
        val2 = str(record2.get(field, '') or '').strip()
        
        if val1 and val2:
            if 'COMPANY' in field.upper():
                scores[f'{field.lower()}_score'] = compare_company_names(val1, val2)
            elif 'ADDRESS' in field.upper():
                scores[f'{field.lower()}_score'] = compare_addresses(val1, val2)
            elif 'PHONE' in field.upper():
                scores[f'{field.lower()}_score'] = compare_phones(val1, val2)
            elif 'EMAIL' in field.upper():
                scores[f'{field.lower()}_score'] = compare_emails(val1, val2)
            else:
                scores[f'{field.lower()}_score'] = calculate_similarity(val1, val2)
        
        if not evaluate_condition(record1, record2, condition):
            return False, scores
    
    return True, scores


def find_best_match(record: dict, candidates: List[dict], rules: Dict) -> Tuple[Optional[dict], str, Dict]:
    """
    Find the best matching record from candidates.
    
    Returns:
        Tuple of (matched_record, match_reason, scores)
    """
    # Sort rules by priority
    sorted_rules = sorted(
        rules.get('rules', {}).items(),
        key=lambda x: x[1].get('priority', 999)
    )
    
    for rule_id, rule in sorted_rules:
        if not rule.get('enabled', True):
            continue
        
        for candidate in candidates:
            is_match, scores = evaluate_rule(record, candidate, rule)
            if is_match:
                match_reason = rule.get('match_reason', rule_id)
                return candidate, match_reason, scores
    
    return None, '', {}


def standardize_record(record: dict) -> dict:
    """Add standardized fields to a record."""
    record['COMPANY_NAME_STD'] = normalize_company_name(record.get('COMPANY_NAME', '') or '')
    record['ADDRESS1_STD'] = normalize_address(record.get('ADDRESS_LINE_1', '') or '')
    record['ADDRESS2_STD'] = normalize_address(record.get('ADDRESS_LINE_2', '') or '')
    record['PHONE_STD'] = normalize_phone(record.get('PHONE_NUMBER', '') or '')
    record['EMAIL_STD'] = normalize_email(record.get('EMAIL_ADDRESS', '') or '')
    
    return record


def calculate_quality_scores(record: dict, settings: dict) -> dict:
    """Calculate quality scores for a record."""
    # Email quality
    email_quality = calculate_email_quality(
        record.get('EMAIL_ADDRESS', ''),
        settings.get('quality_scores', {}).get('email', {})
    )
    
    # Phone quality
    phone_quality = calculate_phone_quality(
        record.get('PHONE_NUMBER', ''),
        record.get('PHONE_EXTENSION', ''),
        settings.get('quality_scores', {}).get('phone', {})
    )
    
    record['email_quality_total'] = email_quality['total']
    record['phone_quality_total'] = phone_quality['total']
    
    # Add individual criteria scores
    for key, value in email_quality.items():
        if key != 'total':
            record[f'email_quality_{key}'] = value
    
    for key, value in phone_quality.items():
        if key != 'total':
            record[f'phone_quality_{key}'] = value
    
    return record


def run_matching(
    input_file: str,
    output_file: str,
    field_mapping: Dict[str, str] = None,
    selected_output_columns: List[str] = None
) -> Dict[str, Any]:
    """
    Main matching pipeline.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file
        field_mapping: Mapping from source columns to standard columns
        selected_output_columns: List of columns to include in output
    
    Returns:
        Statistics dictionary
    """
    # Load configuration
    rules = load_rules()
    settings = load_settings()
    mappings = load_dedup_mappings()
    
    stats = {
        'total_records': 0,
        'matched_existing': 0,
        'new_dedup_keys': 0,
        'errors': 0,
        'start_time': datetime.utcnow().isoformat(),
        'end_time': None
    }
    
    # Read input file
    records = []
    try:
        with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Apply field mapping if provided
                if field_mapping:
                    mapped_row = {}
                    for source_col, target_col in field_mapping.items():
                        if source_col in row:
                            mapped_row[target_col] = row[source_col]
                    # Keep unmapped columns too
                    for col, val in row.items():
                        if col not in field_mapping:
                            mapped_row[col] = val
                    records.append(mapped_row)
                else:
                    records.append(dict(row))
    except Exception as e:
        stats['errors'] += 1
        stats['error_message'] = str(e)
        return stats
    
    stats['total_records'] = len(records)
    
    # Create blocking groups
    blocks = defaultdict(list)
    for i, record in enumerate(records):
        record = standardize_record(record)
        record = calculate_quality_scores(record, settings)
        records[i] = record
        
        blocking_key = create_blocking_key(record)
        blocks[blocking_key].append(i)
    
    # Process each record
    results = []
    processed_in_block = set()
    
    for i, record in enumerate(records):
        try:
            blocking_key = create_blocking_key(record)
            candidates_indices = [j for j in blocks[blocking_key] if j != i and j not in processed_in_block]
            candidates = [records[j] for j in candidates_indices]
            
            # Find match
            matched_record, match_reason, scores = find_best_match(record, candidates, rules)
            
            if matched_record:
                # Use existing dedup key from matched record
                if 'DEDUP_KEY' in matched_record and matched_record['DEDUP_KEY']:
                    dedup_key = matched_record['DEDUP_KEY']
                    is_new = False
                else:
                    dedup_key, is_new = get_or_create_dedup_key(record, mappings)
                
                link_records(dedup_key, record, mappings)
                stats['matched_existing'] += 1
                
                record['DEDUP_KEY'] = dedup_key
                record['MATCH_REASON'] = match_reason
                record['MATCHED_RECORD_IDS'] = '|'.join(get_matched_identifiers(dedup_key, mappings))
                
                # Add similarity scores
                for key, value in scores.items():
                    record[key] = round(value, 2) if value else 0
            else:
                # Create new dedup key
                dedup_key, is_new = get_or_create_dedup_key(record, mappings)
                record['DEDUP_KEY'] = dedup_key
                record['MATCH_REASON'] = 'NEW'
                record['MATCHED_RECORD_IDS'] = ''
                
                if is_new:
                    stats['new_dedup_keys'] += 1
            
            record['MATCH_TIMESTAMP'] = datetime.utcnow().isoformat()
            results.append(record)
            processed_in_block.add(i)
            
        except Exception as e:
            stats['errors'] += 1
            record['MATCH_REASON'] = 'ERROR'
            record['ERROR'] = str(e)
            results.append(record)
    
    # Save dedup mappings
    save_dedup_mappings(mappings)
    
    # Write output
    if results:
        # Determine output columns
        if selected_output_columns:
            output_columns = selected_output_columns
        else:
            # Get all unique columns
            output_columns = []
            for record in results:
                for col in record.keys():
                    if col not in output_columns:
                        output_columns.append(col)
        
        try:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=output_columns, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(results)
        except Exception as e:
            stats['errors'] += 1
            stats['write_error'] = str(e)
    
    stats['end_time'] = datetime.utcnow().isoformat()
    return stats

