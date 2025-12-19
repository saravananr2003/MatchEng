"""
File Processor Module
Handles file standardization and analytics for uploaded CSV files.
Creates processed files with standardized column names from columns_metadata.json.
"""

import csv
import json
import re
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def load_columns_metadata(config_path: str = "config/columns_metadata.json") -> Dict[str, Any]:
    """Load columns metadata configuration."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def build_column_mapping(source_headers: List[str], columns_metadata: Dict[str, Any]) -> Dict[str, str]:
    """
    Build mapping from source columns to standard column names.
    Returns dict: {source_column: standard_column}
    """
    mapping = {}
    
    for source_col in source_headers:
        source_upper = source_col.upper().strip()
        
        for std_col, meta in columns_metadata.items():
            # Exact match with standard column
            if source_upper == std_col.upper():
                mapping[source_col] = std_col
                break
            
            # Check alternate names
            alternates = [a.upper() for a in meta.get('alternate_columns', [])]
            if source_upper in alternates:
                mapping[source_col] = std_col
                break
    
    return mapping


def calculate_analytics(rows: List[Dict], headers: List[str], columns_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate comprehensive analytics for the processed file.
    
    Analytics include:
    - Basic stats (row count, column count)
    - Column completeness (% non-empty values per column)
    - Data quality scores
    - Field-specific analytics (email validity, phone format, etc.)
    - Duplicate detection stats
    - Value distribution for key fields
    """
    total_rows = len(rows)
    if total_rows == 0:
        return {"error": "No data to analyze"}
    
    analytics = {
        "summary": {
            "total_rows": total_rows,
            "total_columns": len(headers),
            "processed_at": datetime.utcnow().isoformat(),
        },
        "column_completeness": {},
        "data_quality": {},
        "field_analytics": {},
        "duplicates": {},
        "value_distributions": {}
    }
    
    # Column completeness analysis
    for col in headers:
        non_empty = sum(1 for row in rows if row.get(col) and str(row.get(col)).strip())
        completeness = round((non_empty / total_rows) * 100, 2) if total_rows > 0 else 0
        
        # Get metadata for this column
        col_meta = columns_metadata.get(col, {})
        display_label = col_meta.get("display_label", col)
        description = col_meta.get("description", "")
        
        analytics["column_completeness"][col] = {
            "filled": non_empty,
            "empty": total_rows - non_empty,
            "completeness_pct": completeness,
            "display_label": display_label,
            "description": description
        }
    
    # Field-specific analytics
    analytics["field_analytics"] = _analyze_fields(rows, headers)
    
    # Duplicate detection
    analytics["duplicates"] = _detect_duplicates(rows, headers)
    
    # Value distributions for key categorical fields
    analytics["value_distributions"] = _get_value_distributions(rows, headers)
    
    # Overall data quality score
    analytics["data_quality"] = _calculate_quality_score(analytics)
    
    return analytics


def _analyze_fields(rows: List[Dict], headers: List[str]) -> Dict[str, Any]:
    """Analyze specific field types for data quality."""
    field_stats = {}
    
    # Email analysis
    if "EMAIL_ADDRESS" in headers:
        emails = [row.get("EMAIL_ADDRESS", "") for row in rows]
        valid_emails = sum(1 for e in emails if _is_valid_email(e))
        field_stats["email"] = {
            "total": len(emails),
            "valid": valid_emails,
            "invalid": len(emails) - valid_emails,
            "validity_pct": round((valid_emails / len(emails)) * 100, 2) if emails else 0,
            "unique": len(set(e.lower().strip() for e in emails if e))
        }
    
    # Phone analysis
    if "PHONE_NUMBER" in headers:
        phones = [row.get("PHONE_NUMBER", "") for row in rows]
        valid_phones = sum(1 for p in phones if _is_valid_phone(p))
        field_stats["phone"] = {
            "total": len(phones),
            "valid": valid_phones,
            "invalid": len(phones) - valid_phones,
            "validity_pct": round((valid_phones / len(phones)) * 100, 2) if phones else 0,
            "unique": len(set(_normalize_phone(p) for p in phones if p))
        }
    
    # ZIP code analysis
    if "ZIP_CODE" in headers:
        zips = [row.get("ZIP_CODE", "") for row in rows]
        valid_zips = sum(1 for z in zips if _is_valid_zip(z))
        field_stats["zip_code"] = {
            "total": len(zips),
            "valid": valid_zips,
            "invalid": len(zips) - valid_zips,
            "validity_pct": round((valid_zips / len(zips)) * 100, 2) if zips else 0,
            "unique": len(set(str(z).strip()[:5] for z in zips if z))
        }
    
    # State analysis
    if "STATE" in headers:
        states = [row.get("STATE", "") for row in rows if row.get("STATE")]
        state_counts = Counter(s.upper().strip() for s in states)
        field_stats["state"] = {
            "unique_states": len(state_counts),
            "top_states": dict(state_counts.most_common(10))
        }
    
    # Company name analysis
    if "COMPANY_NAME" in headers:
        companies = [row.get("COMPANY_NAME", "") for row in rows if row.get("COMPANY_NAME")]
        field_stats["company_name"] = {
            "total": len(companies),
            "unique": len(set(c.lower().strip() for c in companies)),
            "avg_length": round(sum(len(c) for c in companies) / len(companies), 1) if companies else 0
        }
    
    return field_stats


def _detect_duplicates(rows: List[Dict], headers: List[str]) -> Dict[str, Any]:
    """Detect potential duplicates based on key fields."""
    duplicates = {
        "exact_duplicates": 0,
        "potential_duplicates": {},
        "duplicate_groups": []
    }
    
    # Check for exact row duplicates
    row_hashes = []
    for row in rows:
        row_str = "|".join(str(row.get(h, "")).strip().lower() for h in headers)
        row_hashes.append(hash(row_str))
    
    hash_counts = Counter(row_hashes)
    duplicates["exact_duplicates"] = sum(count - 1 for count in hash_counts.values() if count > 1)
    
    # Check duplicates by key field combinations
    key_combinations = [
        ("company_phone", ["COMPANY_NAME", "PHONE_NUMBER"]),
        ("company_address", ["COMPANY_NAME", "ADDRESS_LINE_1", "ZIP_CODE"]),
        ("email", ["EMAIL_ADDRESS"]),
        ("phone", ["PHONE_NUMBER"])
    ]
    
    for combo_name, fields in key_combinations:
        if all(f in headers for f in fields):
            values = []
            for row in rows:
                val = "|".join(str(row.get(f, "")).strip().lower() for f in fields)
                if val and val != "|" * (len(fields) - 1):  # Skip empty combinations
                    values.append(val)
            
            value_counts = Counter(values)
            dup_count = sum(count - 1 for count in value_counts.values() if count > 1)
            duplicates["potential_duplicates"][combo_name] = {
                "duplicate_count": dup_count,
                "fields": fields
            }
    
    return duplicates


def _get_value_distributions(rows: List[Dict], headers: List[str]) -> Dict[str, Any]:
    """Get value distributions for categorical fields."""
    distributions = {}
    
    categorical_fields = ["SOURCE_TYPE", "STATE", "COUNTRY_CODE", "PHONE_TYPE", "ADDRESS_LOCATION_TYPE"]
    
    for field in categorical_fields:
        if field in headers:
            values = [row.get(field, "") for row in rows if row.get(field)]
            if values:
                counts = Counter(v.strip() for v in values)
                distributions[field] = {
                    "unique_values": len(counts),
                    "top_values": dict(counts.most_common(10)),
                    "total_filled": len(values)
                }
    
    return distributions


def _calculate_quality_score(analytics: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate overall data quality score."""
    scores = []
    
    # Completeness score (average completeness across all columns)
    completeness_values = [v["completeness_pct"] for v in analytics["column_completeness"].values()]
    avg_completeness = sum(completeness_values) / len(completeness_values) if completeness_values else 0
    scores.append(avg_completeness)
    
    # Validity scores from field analytics
    field_analytics = analytics.get("field_analytics", {})
    for field_type in ["email", "phone", "zip_code"]:
        if field_type in field_analytics:
            scores.append(field_analytics[field_type].get("validity_pct", 0))
    
    # Uniqueness penalty for duplicates
    total_rows = analytics["summary"]["total_rows"]
    exact_dups = analytics["duplicates"].get("exact_duplicates", 0)
    dup_penalty = max(0, 100 - (exact_dups / total_rows * 100)) if total_rows > 0 else 100
    scores.append(dup_penalty)
    
    overall_score = round(sum(scores) / len(scores), 1) if scores else 0
    
    return {
        "overall_score": overall_score,
        "completeness_score": round(avg_completeness, 1),
        "duplicate_penalty": round(100 - dup_penalty, 1),
        "grade": _get_grade(overall_score)
    }


def _get_grade(score: float) -> str:
    """Convert score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def _is_valid_email(email: str) -> bool:
    """Check if email format is valid."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, str(email).strip()))


def _is_valid_phone(phone: str) -> bool:
    """Check if phone has valid format (at least 10 digits)."""
    if not phone:
        return False
    digits = re.sub(r'\D', '', str(phone))
    return len(digits) >= 10


def _normalize_phone(phone: str) -> str:
    """Normalize phone to digits only."""
    if not phone:
        return ""
    return re.sub(r'\D', '', str(phone))


def _is_valid_zip(zip_code: str) -> bool:
    """Check if ZIP code is valid (5 or 9 digits for US)."""
    if not zip_code:
        return False
    digits = re.sub(r'\D', '', str(zip_code))
    return len(digits) in [5, 9]


def process_file(
    input_path: str,
    output_dir: str = "datafiles/process",
    columns_metadata_path: str = "config/columns_metadata.json"
) -> Dict[str, Any]:
    """
    Process an uploaded file:
    1. Read the source file
    2. Map columns to standard names
    3. Create processed file with standardized columns
    4. Generate analytics
    
    Returns:
        Dict with processed file info and analytics
    """
    input_file = Path(input_path)
    if not input_file.exists():
        return {"error": f"Input file not found: {input_path}"}
    
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load column metadata
    columns_metadata = load_columns_metadata(columns_metadata_path)
    
    # Read source file
    rows = []
    source_headers = []
    
    try:
        with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            source_headers = reader.fieldnames or []
            rows = [dict(row) for row in reader]
    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}
    
    if not rows:
        return {"error": "File is empty or has no data rows"}
    
    # Build column mapping
    column_mapping = build_column_mapping(source_headers, columns_metadata)
    
    # Get all standard columns from metadata (for consistent output)
    input_groups = ["input-fields", "input-fields-(source)", "input-fields-(address)", 
                    "input-fields-(email)", "input-fields-(phone)"]
    standard_columns = [
        col for col, meta in columns_metadata.items()
        if meta.get("group", "") in input_groups
    ]
    
    # Transform rows to use standard column names
    processed_rows = []
    for row in rows:
        processed_row = {}
        
        # Map source columns to standard columns
        for source_col, value in row.items():
            if source_col in column_mapping:
                std_col = column_mapping[source_col]
                processed_row[std_col] = value
            else:
                # Keep unmapped columns with original name
                processed_row[source_col] = value
        
        # Ensure all standard columns exist (even if empty)
        for std_col in standard_columns:
            if std_col not in processed_row:
                processed_row[std_col] = ""
        
        processed_rows.append(processed_row)
    
    # Determine output headers (standard columns + any unmapped source columns)
    unmapped_cols = [h for h in source_headers if h not in column_mapping]
    output_headers = standard_columns + unmapped_cols
    
    # Generate output filename
    file_id = str(uuid.uuid4())[:8]
    original_name = input_file.stem
    output_filename = f"{file_id}_{original_name}_processed.csv"
    output_file = output_path / output_filename
    
    # Write processed file
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=output_headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(processed_rows)
    except Exception as e:
        return {"error": f"Failed to write processed file: {str(e)}"}
    
    # Calculate analytics
    analytics = calculate_analytics(processed_rows, output_headers, columns_metadata)
    
    # Save analytics to JSON
    analytics_filename = f"{file_id}_{original_name}_analytics.json"
    analytics_file = output_path / analytics_filename
    
    try:
        with open(analytics_file, 'w', encoding='utf-8') as f:
            json.dump(analytics, f, indent=2)
    except Exception:
        pass  # Analytics save is optional
    
    return {
        "ok": True,
        "input_file": str(input_file),
        "processed_file": str(output_file),
        "processed_filename": output_filename,
        "analytics_file": str(analytics_file),
        "analytics_filename": analytics_filename,
        "column_mapping": column_mapping,
        "mapped_columns": len(column_mapping),
        "unmapped_columns": unmapped_cols,
        "total_rows": len(processed_rows),
        "total_columns": len(output_headers),
        "analytics": analytics
    }


def get_processed_file_preview(
    processed_filename: str,
    process_dir: str = "datafiles/process",
    limit: int = 100
) -> Dict[str, Any]:
    """Get preview of a processed file."""
    file_path = Path(process_dir) / processed_filename
    
    if not file_path.exists():
        return {"error": "Processed file not found"}
    
    try:
        preview_rows = []
        headers = []
        total_rows = 0
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            for i, row in enumerate(reader):
                total_rows = i + 1
                if i < limit:
                    preview_rows.append(dict(row))
        
        return {
            "headers": headers,
            "preview": preview_rows,
            "total_rows": total_rows
        }
    except Exception as e:
        return {"error": str(e)}


def load_analytics(
    analytics_filename: str,
    process_dir: str = "datafiles/process"
) -> Dict[str, Any]:
    """Load analytics for a processed file."""
    file_path = Path(process_dir) / analytics_filename
    
    if not file_path.exists():
        return {"error": "Analytics file not found"}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

