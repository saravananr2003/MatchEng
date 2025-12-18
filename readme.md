# Matching Engine - Complete Documentation

**Version**: 2.0  
**Last Updated**: December 15, 2025  
**Status**: Production Ready

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Business Requirements](#business-requirements)
3. [System Architecture](#system-architecture)
4. [User Interface Guide](#user-interface-guide)
5. [Matching Rules](#matching-rules)
6. [Configuration](#configuration)
7. [Data Quality & Scoring](#data-quality--scoring)
8. [Technical Implementation](#technical-implementation)
9. [Performance Optimization](#performance-optimization)
10. [Deployment & Operations](#deployment--operations)
11. [Quick Reference](#quick-reference)

---

## Executive Summary

The Matching Engine is a sophisticated data deduplication and matching platform that identifies and clusters related company records across disparate data sources. The system uses advanced matching algorithms based on company name, address, email, and phone number, with configurable business rules and quality scoring.

### Key Features

- **Smart Matching**: 40+ configurable business rules for matching records
- **Quality Scoring**: Individual quality scores for email, phone, and address
- **Human-in-the-Loop**: AI/ML classification with human validation for continuous improvement
- **Web UI**: Complete workflow from upload to results with visual feedback
- **Flexible Input**: CSV upload, Snowflake, ADLS, or FTP sources
- **Persistent Dedup**: Maintains dedup keys across multiple runs
- **Standardization**: Automatic data cleaning and standardization
- **Performance**: Optimized for large datasets with blocking and vectorization

---

## Business Requirements

### Objectives

1. **Reduce Duplicates**: Identify and cluster duplicate company records
2. **Improve Data Quality**: Enrich records with quality indicators and confidence scores
3. **Enable Self-Service**: Business users can configure rules and run matching jobs
4. **Continuous Improvement**: ML/AI learns from user feedback to improve over time
5. **Audit Trail**: Track matching decisions with reasons and confidence scores

### Scope

**In Scope (Current)**:
- CSV/Snowflake/ADLS/FTP data upload
- Field mapping with ML-powered auto-detection
- Configurable matching rules (40+ available)
- Dedup key generation and persistence
- Quality scoring for email, phone, address
- Human-in-the-loop training interface
- Results download and visualization

**Out of Scope (Future)**:
- Direct CRM/MDM integration
- Real-time API matching
- Advanced ML model training
- Multi-language support

### User Personas

1. **Data Analyst**: Uploads data, maps fields, runs matching, reviews results
2. **Data Steward**: Configures rules and thresholds, validates matches
3. **Trainer**: Validates email/phone classifications to improve quality scores
4. **Administrator**: Manages field configuration and system settings

---

## System Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    Web UI (Flask)                       │
│  Upload → Map Fields → Configure → Process → Results   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│              Application Layer (Python)                 │
│  - Routes (modularized)                                 │
│  - File Handlers                                        │
│  - Configuration Manager                                │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│              Matching Engine Core                       │
│  - Matching Rules Engine                                │
│  - Dedup Key Generator                                  │
│  - Similarity Calculator                                │
│  - Quality Scorer                                       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│                  Data Layer                             │
│  - CSV Cache                                            │
│  - Dedup Persistence (dedup_mappings.json)             │
│  - Configuration Files (JSON)                           │
│  - ML Models                                            │
└─────────────────────────────────────────────────────────┘
```

### Directory Structure

```
MatchingEngine/
├── app.py                      # Main Flask application
├── matching_engine.py          # Core matching logic
├── dedup.py                    # Dedup key generation
├── similarity.py               # Similarity calculations
├── email_classification_ml.py  # Email/phone classification
├── config/
│   ├── settings.json          # Thresholds, quality scores
│   ├── rules.json             # Business matching rules
│   ├── column_config.json     # Field configuration
│   └── columns_metadata.json  # Field metadata
├── datafiles/
│   ├── incoming/              # Upload directory
│   ├── output/                # Results directory
│   ├── models/                # ML models
│   └── training/              # Training data
├── routes/                    # Modularized routes
├── helpers/                   # Utility functions
├── templates/                 # HTML templates
└── static/                    # CSS, JS, images
```

---

## User Interface Guide

### Navigation Flow

```
Home Dashboard
    │
    ├─→ Upload File
    │       ↓
    ├─→ Map Fields (with auto-mapping)
    │       ↓
    ├─→ Configure Mapping (review and adjust)
    │       ↓
    ├─→ Process & Match (select output columns)
    │       ↓
    ├─→ Results (download and view)
    │
    ├─→ Configure Rules (business rules)
    ├─→ Configure Thresholds (similarity percentages)
    ├─→ File Management (view/delete files)
    ├─→ Training (email/phone classification)
    └─→ Admin (field and metadata configuration)
```

### Key UI Features

#### 1. Upload File
- **Multiple Sources**: Local CSV, ADLS, FTP, Snowflake
- **Preview**: See first rows of uploaded data
- **Validation**: Check required fields and format
- **Quick Start**: Collapsible help sections

#### 2. Map Fields
- **Auto-Mapping**: ML-powered field detection (with confidence scores)
- **Source Preview**: View and filter source data
- **Mapping Summary**: See mapped vs unmapped fields
- **Field Groups**: Organized by category (source, company, address, contact)

#### 3. Configure Mapping
- **Mandatory Validation**: Highlights unmapped required fields
- **Group View**: Accordion-style field grouping
- **Mapping Summary**: Top-level overview (collapsed by default)

#### 4. Process & Match
- **Output Column Selection**: Choose which columns to include
- **Group Selection**: Select all/none by category
- **Visual Feedback**: Color-coded selection states
- **ML Enhancement**: Toggle machine learning features
- **Progress Tracking**: Real-time status updates

#### 5. Results
- **Download Options**: Multiple format support
- **Confidence Scores**: Name+Address, Name+Email, Name+Phone
- **Match Tracking**: Reason codes and matched record IDs
- **Statistics**: Match counts and quality metrics

#### 6. Configure Rules
- **40+ Fields**: All input and standardized fields available
- **Rule Priority**: Drag-and-drop ordering
- **Enable/Disable**: Toggle rules on/off
- **Edit Modal**: Visual editor for rule conditions
- **Preview**: See rule logic before saving

#### 7. Configure Thresholds
- **Field-Level**: Set similarity percentages per field
- **Address Tree**: Hierarchical address component configuration
- **Quality Weights**: Adjustable email and phone scoring criteria
- **Blank Handling**: Configure null value matching

#### 8. Training (HITL)
- **Email Classification**:
  - Domain classification (personal/business)
  - Pattern classification (generic/individual)
  - Real-time feedback
- **Phone Classification**:
  - Area code validation
  - Exchange code validation
  - Toll-free identification
  - Main line detection

#### 9. Admin
- **Field Configuration**: Manage column sequence and defaults
- **Metadata Management**: Update labels and descriptions
- **Drag-and-Drop**: Reorder fields visually
- **Bulk Actions**: Select all, expand/collapse groups

---

## Matching Rules

### Rule Categories

All rules are stored in `config/rules.json` with the following structure:

```json
{
  "rules": {
    "R001": {
      "id": "R001",
      "name": "Company + Address Match",
      "description": "Match records with similar company name and address",
      "enabled": true,
      "priority": 100,
      "match_reason": "COMP_ADDR",
      "conditions": [
        {"field": "COMPANY_NAME", "percentage": "70", "include": true},
        {"field": "ADDRESS1", "percentage": "80", "include": true},
        {"field": "ZIP_CODE", "percentage": "100", "include": true}
      ]
    }
  }
}
```

### Standard Rules (Pre-configured)

| Rule ID | Name | Conditions | Priority |
|---------|------|------------|----------|
| R001 | Company + Address | Company ≥70%, Address1 ≥80%, ZIP =100% | 100 |
| R002 | Company + Email | Company ≥70%, Email =100% | 200 |
| R003 | Company + Phone | Company ≥70%, Phone =100%, Address context | 300 |
| R004 | Company + Address + Email | Company ≥70%, Address ≥80%, Email =100% | 150 |
| R005 | Company + Address + Phone | Company ≥70%, Address ≥80%, Phone =100% | 250 |
| R006 | Company + Email + Phone | Company ≥70%, Email =100%, Phone =100% | 350 |
| R007 | Company + Phone (Blank Address) | Company ≥70%, Phone =100%, Both addresses blank | 400 |

### Available Fields for Rules (40+)

#### Input Fields
- SOURCE_TYPE, SOURCE_ID, RECORD_ID
- COMPANY_NAME
- ADDRESS1, ADDRESS2, CITY, STATE, ZIP_CODE, ZIP_SUPP
- COUNTY, COUNTRY_CODE
- EMAIL, PHONE, PHONE_EXTENSION
- GENDER
- Quality indicators: *_VALID_IND, *_MARKETABLE_IND

#### Standardized Fields
- COMPANY_NAME_STD
- ADDRESS1_STD, ADDRESS2_STD, CITY_STD, STATE_STD
- ZIP_CODE_STD, ZIP_SUPP_STD
- EMAIL_STD, PHONE_STD, PHONE_EXTENSION_STD

### Rule Matching Logic

```python
def evaluate_rule(record1, record2, rule):
    for condition in rule.conditions:
        field = condition['field']
        threshold = condition['percentage']
        
        # Get similarity score
        similarity = calculate_similarity(record1[field], record2[field])
        
        if condition['include']:
            # Field must match
            if similarity < threshold:
                return False
        else:
            # Field must NOT match
            if similarity >= threshold:
                return False
    
    # All conditions met
    return True
```

### Special Conditions

- **Blank Allowed**: Match even if value is blank
- **Blank Only**: Only match if both values are blank
- **Include**: Field must match above threshold
- **Exclude**: Field must NOT match above threshold

---

## Configuration

### Configuration Files

#### 1. settings.json
**Location**: `config/settings.json`

**Structure**:
```json
{
  "thresholds": {
    "company_name_threshold": {
      "value": 70,
      "description": "Company name similarity percentage"
    },
    "address_line_1_threshold": {
      "value": 80,
      "description": "Address line 1 similarity percentage"
    }
  },
  "quality_scores": {
    "email": {
      "max_points": 100,
      "criteria": {
        "valid_format": {"weight": 20, "description": "Valid email format"},
        "not_personal": {"weight": 25, "description": "Business email"},
        "not_generic": {"weight": 20, "description": "Not generic mailbox"}
      }
    },
    "phone": {
      "max_points": 100,
      "criteria": {
        "ten_digits": {"weight": 10, "description": "Has 10 digits"},
        "valid_area_code": {"weight": 15, "description": "Valid area code"}
      }
    }
  }
}
```

#### 2. rules.json
**Location**: `config/rules.json`

Contains all business matching rules (see Matching Rules section).

#### 3. column_config.json
**Location**: `config/column_config.json`

**Purpose**: Field configuration for output selection
```json
{
  "input_fields": [
    {
      "column_name": "COMPANY_NAME",
      "sequence": 1001,
      "default_selected": true
    }
  ]
}
```

#### 4. columns_metadata.json
**Location**: `config/columns_metadata.json`

**Purpose**: Field metadata (labels, descriptions, groups)
```json
{
  "COMPANY_NAME": {
    "display_label": "Company Name",
    "description": "Legal or trading name of the company",
    "group": "input-fields",
    "required": true,
    "data_type": "string",
    "alternate_columns": ["COMPANYNAME", "BUSINESS_NAME"]
  }
}
```

### Field Groups

Fields are organized into groups:
- `input-fields-(source)`: Source identification
- `input-fields`: Core input fields
- `input-fields-address`: Address components
- `input-fields-email-quality`: Email quality indicators
- `input-fields-phone-quality`: Phone quality indicators
- `matching_results`: Dedup keys, match reasons
- `confidence_scores`: Similarity scores
- `similarity_scores`: Individual field similarities
- `standardized_fields`: Cleaned/standardized data

---

## Data Quality & Scoring

### Email Quality Scoring (Max: 100 points)

| Criteria | Weight | Description |
|----------|--------|-------------|
| Valid Format | 11% | Matches standard email regex |
| Business Email | 11% | Not personal domain (@gmail, @yahoo) |
| Not Generic | 11% | Not generic mailbox (info@, admin@) |
| Not Admin/Help | 11% | Not support mailbox |
| Not Department | 11% | Not department email (sales@, hr@) |
| Domain Quality | 22% | High-quality business domain |
| Uniqueness | 23% | Individual, not shared mailbox |

**Scoring Logic**:
```python
def calculate_email_quality(email):
    score = 0
    
    # Valid format (11 points)
    if is_valid_email_format(email):
        score += 11
    
    # Business domain (11 points)
    if not is_personal_domain(email):
        score += 11
    
    # Not generic (11 points)
    if not is_generic_mailbox(email):
        score += 11
    
    # ... other criteria
    
    return min(score, 100)
```

### Phone Quality Scoring (Max: 100 points)

| Criteria | Weight | Description |
|----------|--------|-------------|
| 10 Digits | 10% | US phone number format |
| Not All Same | 10% | Digits are not all identical |
| Valid Area Code | 10% | Area code exists and is valid |
| Valid Exchange | 10% | Exchange code is valid |
| Valid Number | 10% | Full number is valid |
| Not Toll-Free | 20% | Not 800/888/877/etc |
| Not Main Line | 20% | Has extension or direct line |
| High Quality | 10% | Verified or high-confidence |

### Address Quality Indicators

Provided by external data vendors:
- `RESIDENTIAL_DELIVERY_IND`: Is residential address
- `ADDRESS_LOCATION_TYPE`: Type of location
- `ADDRESS_VALID_IND`: Address is valid
- `ADDRESS_MARKETABLE_IND`: Address is marketable
- `ADDRESS_FAULT_CODE`: Address issues/errors

### Confidence Scores

Generated for each match:
- **Company Match Confidence**: Similarity percentage for company name
- **Address Match Confidence**: Weighted average of address components
- **Email Match Confidence**: Binary (100% or 0%) with quality score
- **Phone Match Confidence**: Binary (100% or 0%) with quality score

---

## Technical Implementation

### Core Technologies

- **Backend**: Python 3.13, Flask 3.0
- **Data Processing**: Pandas 2.x, NumPy
- **ML/AI**: scikit-learn, fuzzy matching (fuzzywuzzy)
- **Frontend**: Bootstrap 5, jQuery, Jinja2
- **Storage**: JSON configuration, CSV data files

### Key Modules

#### matching_engine.py
**Purpose**: Core matching logic

**Key Functions**:
```python
def run(input_file, output_file, config):
    """Main matching pipeline"""
    # 1. Load and validate data
    # 2. Standardize fields
    # 3. Calculate quality scores
    # 4. Create blocking keys
    # 5. Compare records within blocks
    # 6. Apply matching rules
    # 7. Generate dedup keys
    # 8. Write output
```

#### dedup.py
**Purpose**: Dedup key generation and persistence

**Key Functions**:
```python
def generate_dedup_key(record):
    """Generate UUID-based dedup key"""
    components = [
        record.get('SOURCE_TYPE'),
        record.get('SOURCE_ID'),
        record.get('COMPANY_NAME_STD'),
        record.get('ADDRESS1_STD'),
        record.get('PHONE_STD')
    ]
    return generate_uuid(components)

def load_dedup_mappings():
    """Load persistent dedup keys"""
    return json.load('datafiles/dedup_mappings.json')
```

#### similarity.py
**Purpose**: Calculate similarity between values

**Algorithms**:
- Levenshtein distance
- Jaro-Winkler similarity
- Token-based matching
- Phonetic matching (Soundex, Metaphone)

#### email_classification_ml.py
**Purpose**: Email and phone classification

**Features**:
- Domain classification (personal/business)
- Pattern matching (generic/individual)
- Phone component validation
- Human-in-the-loop training
- Model persistence

### Performance Optimizations

#### 1. Blocking
**Purpose**: Reduce comparison space

```python
def create_blocking_key(record):
    """Create key for grouping similar records"""
    company = record.get('COMPANY_NAME', '')[:3]
    zip_code = record.get('ZIP_CODE', '')[:5]
    phone = record.get('PHONE', '')[-4:]
    return f"{company}_{zip_code}_{phone}"
```

Only records with the same blocking key are compared.

#### 2. Vectorization
**Purpose**: Speed up pandas operations

```python
# Instead of iterating rows
for idx, row in df.iterrows():
    df.at[idx, 'RESULT'] = calculate(row['VALUE'])

# Use vectorized operations
df['RESULT'] = df['VALUE'].apply(calculate)
```

#### 3. Caching
**Purpose**: Avoid redundant file reads

```python
from helpers.csv_cache import load_csv_with_cache

# First call: reads file
df = load_csv_with_cache('file.csv')

# Subsequent calls: returns cached dataframe
df = load_csv_with_cache('file.csv')
```

#### 4. Parallel Processing
**Purpose**: Utilize multiple CPU cores

```python
from multiprocessing import Pool

def process_batch(records):
    # Process records
    return results

with Pool(processes=4) as pool:
    results = pool.map(process_batch, batches)
```

---

## Performance Optimization

### Current Performance

| Dataset Size | Processing Time | Throughput |
|--------------|----------------|------------|
| 1,000 records | ~5 seconds | 200 rec/sec |
| 10,000 records | ~45 seconds | 220 rec/sec |
| 100,000 records | ~8 minutes | 208 rec/sec |

### Optimization Techniques

1. **Blocking**: Reduces O(n²) to O(n×m) where m << n
2. **Vectorization**: 10-50x faster than row iteration
3. **Caching**: Eliminates redundant file I/O
4. **Indexing**: Fast lookups for dedup keys
5. **Lazy Loading**: Load data only when needed
6. **Batch Processing**: Process records in chunks

### Recommendations for Large Datasets

- Use blocking keys effectively
- Limit preview rows to 100-500
- Enable ML features only when needed
- Clear cache between large runs
- Consider database backend for 1M+ records

---

## Deployment & Operations

### Installation

```bash
# Clone repository
git clone <repo-url>
cd MatchingEngine

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Starting the Application

```bash
# Development
python app.py

# Production (with gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Configuration

1. Edit `config/settings.json` for thresholds
2. Edit `config/rules.json` for matching rules
3. Edit `config/column_config.json` for output fields
4. Configure file paths in `app.py`

### Monitoring

- **Logs**: `datafiles/logs/matching_engine.log`
- **Metrics**: Processing time, match counts
- **Errors**: Check Flask console output

### Backup

```bash
# Backup configuration
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/

# Backup dedup mappings
cp datafiles/dedup_mappings.json datafiles/dedup_mappings_$(date +%Y%m%d).json.bak
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Slow processing | Enable blocking, reduce preview size |
| Memory error | Process in smaller batches |
| Missing fields | Check column_config.json |
| Wrong matches | Adjust thresholds in settings.json |
| UI not loading | Clear browser cache (Cmd+Shift+R) |

---

## Quick Reference

### Workflow Checklist

- [ ] Upload CSV file or configure data source
- [ ] Review auto-mapped fields
- [ ] Adjust any incorrect mappings
- [ ] Select output columns
- [ ] Enable/disable matching rules
- [ ] Configure thresholds if needed
- [ ] Start matching process
- [ ] Review results and confidence scores
- [ ] Download output file
- [ ] Train email/phone classifications (optional)

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Refresh page | Cmd/Ctrl + R |
| Hard refresh | Cmd/Ctrl + Shift + R |
| Expand/collapse | Click header |
| Select all | Checkbox in header |

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/upload` | GET/POST | Upload file |
| `/map_fields` | GET | Map fields page |
| `/process` | GET/POST | Start matching |
| `/results` | GET | View results |
| `/configure_rules` | GET/POST | Configure rules |
| `/configure_thresholds` | GET/POST | Configure thresholds |
| `/api/update_rule` | POST | Update rule via API |
| `/api/get_column_config` | GET | Get field config |

### File Locations

| Type | Location |
|------|----------|
| Input files | `datafiles/incoming/` |
| Output files | `datafiles/output/` |
| Dedup mappings | `datafiles/dedup_mappings.json` |
| Configuration | `config/*.json` |
| ML models | `datafiles/models/` |
| Logs | `datafiles/logs/` |

---

## Recent Improvements (December 2025)

### UI Enhancements
- Edit modal for matching rules
- All input and standardized fields available in rules
- Column resizing in data preview
- Improved file management with expand/collapse
- CSS consolidation into single stylesheet
- Mapping summary moved to top and collapsed
- Source data preview uses display labels

### Performance
- Vectorized pandas operations
- CSV caching for repeated reads
- Optimized blocking key generation
- Reduced file I/O operations

### Configuration
- Modularized routes into separate files
- Centralized configuration management
- Dynamic field loading from metadata
- Improved error handling throughout

### Bug Fixes
- Preview limit variable not defined
- Column filter preview errors
- File management sections not expanding
- Edit button not showing modal
- Rule names wrapping in table

---

## Support & Contact

For issues, questions, or enhancements:
1. Check this documentation
2. Review configuration files
3. Check logs for errors
4. Contact system administrator

---
