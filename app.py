import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from db import ensure_db, insert_record, find_candidates_by_phone, find_candidates_by_keys
from matching import (
    compute_keys,
    normalize_address,
    normalize_company_name,
    normalize_phone,
    pick_best_match,
)


def load_metadata_config(config_path: Path) -> dict:
    """Load metadata configuration from JSON file. Returns default config if file doesn't exist."""
    default_config = {
        "input_columns": {
            "SOURCE_TYPE": {
                "field_type": "Source Fields",
                "label": "Source Type",
                "description": "The type of source of the record",
                "type": "string",
                "required": True,
                "active": True,
                "alternate_names": ["SOURCE_TYPE", "SRC_TYPE"]
            },
            "SOURCE_ID": {
                "field_type": "Source Fields",
                "label": "Source ID",
                "description": "The ID of the source of the record",
                "type": "string",
                "required": True,
                "active": True,
                "alternate_names": ["SOURCE_ID", "SRC_ID"]
            },
            "COMPANY_NAME": {
                "field_type": "Base Fields",
                "label": "Company Name",
                "description": "The name of the company",
                "type": "string",
                "required": True,
                "active": True,
                "alternate_names": ["COMPANY_NAME", "COMP_NAME"]
            },
            "ADDRESS": {
                "field_type": "Address Fields",
                "label": "Address",
                "description": "The address of the company",
                "type": "string",
                "required": True,
                "active": True,
                "alternate_names": ["ADDRESS", "ADDR"]
            },
            "PHONE_NUMBER": {
                "field_type": "Phone Fields",
                "label": "Phone Number",
                "description": "The phone number of the company",
                "type": "string",
                "required": True,
                "active": True,
                "alternate_names": ["PHONE_NUMBER", "PHONE"]
            }
        },
        "output_columns": {
            "DEDUP_ID": "dedup_id",
            "MATCH_STATUS": "match_status",
            "MATCH_SCORE": "match_score",
            "MATCHED_TO": "matched_to",
            "ERROR": "error"
        }
    }
    
    if not config_path.exists():
        # Create config directory and file with defaults if they don't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        return default_config
    
    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
            # Ensure input_columns exists
            if "input_columns" not in config:
                config["input_columns"] = default_config["input_columns"]
            # Ensure output_columns exists
            if "output_columns" not in config:
                config["output_columns"] = default_config["output_columns"]
            # Ensure all columns have 'active' field
            for col_key, col_data in config.get("input_columns", {}).items():
                if "active" not in col_data:
                    col_data["active"] = True
            return config
    except (json.JSONDecodeError, IOError) as e:
        # If config file is corrupted, return defaults
        return default_config


def get_required_columns_from_config(config: dict) -> list:
    """Extract required column names from config, considering alternate names."""
    required = []
    input_columns = config.get("input_columns", {})
    
    for col_key, col_data in input_columns.items():
        if col_data.get("active", True) and col_data.get("required", False):
            # Add the label and all alternate names
            required.append(col_data.get("label", col_key))
            required.extend(col_data.get("alternate_names", []))
    
    return required


def find_column_by_header(header: str, config: dict) -> tuple:
    """Find the column key and data for a given CSV header."""
    input_columns = config.get("input_columns", {})
    header_upper = header.upper().strip()
    
    for col_key, col_data in input_columns.items():
        if not col_data.get("active", True):
            continue
        
        # Check if header matches label
        if col_data.get("label", "").upper() == header_upper:
            return col_key, col_data
        
        # Check if header matches any alternate name
        for alt_name in col_data.get("alternate_names", []):
            if alt_name.upper() == header_upper:
                return col_key, col_data
    
    return None, None


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", str(10 * 1024 * 1024)))
    app.config["DATA_DIR"] = os.getenv("DATA_DIR", str(Path(__file__).parent / "data"))
    app.config["OUTPUT_DIR"] = os.getenv("OUTPUT_DIR", str(Path(__file__).parent / "outputs"))
    app.config["DB_PATH"] = os.getenv(
        "DB_PATH", str(Path(app.config["DATA_DIR"]) / "matches.db")
    )
    app.config["METADATA_CONFIG_PATH"] = os.getenv(
        "METADATA_CONFIG_PATH", str(Path(__file__).parent / "config" / "metadata_config.json")
    )

    Path(app.config["DATA_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["OUTPUT_DIR"]).mkdir(parents=True, exist_ok=True)

    # Load metadata configuration
    app.config["METADATA_CONFIG"] = load_metadata_config(Path(app.config["METADATA_CONFIG_PATH"]))

    ensure_db(app.config["DB_PATH"])

    @app.get("/")
    def index():
        return render_template("index.html")
    
    @app.get("/config")
    def config_page():
        return render_template("config.html")
    
    @app.get("/api/config")
    def get_config():
        """Get the current metadata configuration."""
        return jsonify(app.config["METADATA_CONFIG"])
    
    @app.post("/api/config")
    def update_config():
        """Update the metadata configuration."""
        try:
            new_config = request.get_json()
            if not new_config:
                return jsonify({"error": "No configuration data provided"}), 400
            
            # Validate structure
            if "input_columns" not in new_config:
                return jsonify({"error": "Missing 'input_columns' in configuration"}), 400
            
            # Save to file
            config_path = Path(app.config["METADATA_CONFIG_PATH"])
            with config_path.open("w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=4)
            
            # Update in-memory config
            app.config["METADATA_CONFIG"] = new_config
            
            return jsonify({"ok": True, "message": "Configuration updated successfully"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.post("/api/upload")
    def upload():
        if "file" not in request.files:
            return jsonify({"error": "No file field named 'file'"}), 400

        f = request.files["file"]
        if not f or not f.filename:
            return jsonify({"error": "No file selected"}), 400

        filename = f.filename.lower()
        if not filename.endswith(".csv"):
            return jsonify({"error": "Only .csv uploads are supported"}), 400

        raw = f.stream.read().decode("utf-8", errors="replace")
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        if not lines:
            return jsonify({"error": "Uploaded CSV is empty"}), 400

        import csv
        from io import StringIO

        reader = csv.DictReader(StringIO("\n".join(lines)))
        csv_headers = [h.strip() for h in (reader.fieldnames or [])]

        # Validate CSV headers against metadata config
        config = app.config["METADATA_CONFIG"]
        input_columns = config.get("input_columns", {})
        
        # Find required active columns
        required_cols = {}
        for col_key, col_data in input_columns.items():
            if col_data.get("active", True) and col_data.get("required", False):
                required_cols[col_key] = col_data
        
        # Check if all required columns are present (by label or alternate name)
        missing = []
        found_mapping = {}
        
        for col_key, col_data in required_cols.items():
            label = col_data.get("label", "")
            alternate_names = col_data.get("alternate_names", [])
            
            # Check if any header matches
            found = False
            matched_header = None
            
            for header in csv_headers:
                header_upper = header.upper()
                if (header_upper == label.upper() or 
                    header_upper in [alt.upper() for alt in alternate_names]):
                    found = True
                    matched_header = header
                    found_mapping[col_key] = header
                    break
            
            if not found:
                missing.append({
                    "column_key": col_key,
                    "label": label,
                    "alternate_names": alternate_names
                })
        
        if missing:
            missing_labels = [m["label"] for m in missing]
            return (
                jsonify(
                    {
                        "error": "Missing required columns",
                        "missing": missing_labels,
                        "missing_details": missing,
                        "found": csv_headers,
                    }
                ),
                400,
            )

        out_rows = []
        stats = {
            "processed": 0,
            "matched_existing": 0,
            "new_dedup": 0,
            "errors": 0,
        }

        # Build mapping from CSV headers to column keys
        header_to_col_key = {}
        for col_key, col_data in input_columns.items():
            if not col_data.get("active", True):
                continue
            label = col_data.get("label", "")
            alternate_names = col_data.get("alternate_names", [])
            
            for header in csv_headers:
                header_upper = header.upper()
                if (header_upper == label.upper() or 
                    header_upper in [alt.upper() for alt in alternate_names]):
                    header_to_col_key[header] = col_key
                    break
        
        for row in reader:
            stats["processed"] += 1
            try:
                # Extract values using the mapping
                source_type = ""
                source_id = ""
                company_name_raw = ""
                address_parts = []
                phone_raw = ""
                
                # Find values by matching headers to column keys
                for header, value in row.items():
                    col_key = header_to_col_key.get(header)
                    if col_key == "SOURCE_TYPE":
                        source_type = (value or "").strip()
                    elif col_key == "SOURCE_ID":
                        source_id = (value or "").strip()
                    elif col_key == "COMPANY_NAME":
                        company_name_raw = (value or "").strip()
                    elif col_key and col_key.startswith("ADDRESS"):
                        # Collect all address fields
                        val = (value or "").strip()
                        if val:
                            address_parts.append(val)
                    elif col_key == "PHONE_NUMBER":
                        phone_raw = (value or "").strip()
                
                # Combine address parts
                address_raw = ", ".join(address_parts) if address_parts else ""

                company_name = normalize_company_name(company_name_raw)
                address = normalize_address(address_raw)
                phone = normalize_phone(phone_raw)

                name_key, addr_key = compute_keys(company_name, address)

                # 1) Candidate blocking by phone if present.
                candidates = []
                if phone:
                    candidates = find_candidates_by_phone(app.config["DB_PATH"], phone)

                # 2) Fallback blocking by keys.
                if not candidates:
                    candidates = find_candidates_by_keys(
                        app.config["DB_PATH"], name_key=name_key, addr_key=addr_key, limit=500
                    )

                # 3) Pick best match using fuzzy scoring.
                match = pick_best_match(
                    company_name=company_name,
                    address=address,
                    phone=phone,
                    candidates=candidates,
                )

                if match is None:
                    dedup_id = str(uuid.uuid4())
                    match_status = "NEW"
                    stats["new_dedup"] += 1
                    match_score = None
                    matched_to_source = None
                else:
                    dedup_id = match["dedup_id"]
                    match_status = "MATCH"
                    stats["matched_existing"] += 1
                    match_score = match["score"]
                    matched_to_source = f"{match['source_type']}:{match['source_id']}"

                insert_record(
                    app.config["DB_PATH"],
                    {
                        "source_type": source_type,
                        "source_id": source_id,
                        "company_name": company_name_raw,
                        "company_name_norm": company_name,
                        "address": address_raw,
                        "address_norm": address,
                        "phone": phone_raw,
                        "phone_norm": phone,
                        "name_key": name_key,
                        "addr_key": addr_key,
                        "dedup_id": dedup_id,
                        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    },
                )

                out = dict(row)
                out["DeDup ID"] = dedup_id
                out["Match Status"] = match_status
                out["Match Score"] = "" if match_score is None else str(match_score)
                out["Matched To"] = "" if matched_to_source is None else matched_to_source
                out_rows.append(out)
            except Exception as e:
                stats["errors"] += 1
                out = dict(row)
                out["DeDup ID"] = ""
                out["Match Status"] = "ERROR"
                out["Match Score"] = ""
                out["Matched To"] = ""
                out["Error"] = str(e)
                out_rows.append(out)

        output_id = str(uuid.uuid4())
        out_path = Path(app.config["OUTPUT_DIR"]) / f"{output_id}.csv"

        fieldnames = list(reader.fieldnames or [])
        for extra in ["DeDup ID", "Match Status", "Match Score", "Matched To", "Error"]:
            if extra not in fieldnames:
                fieldnames.append(extra)

        import csv

        with out_path.open("w", newline="", encoding="utf-8") as fp:
            w = csv.DictWriter(fp, fieldnames=fieldnames)
            w.writeheader()
            for r in out_rows:
                w.writerow(r)

        return jsonify(
            {
                "ok": True,
                "stats": stats,
                "download_url": f"/download/{output_id}",
            }
        )

    @app.get("/download/<output_id>")
    def download(output_id: str):
        out_path = Path(app.config["OUTPUT_DIR"]) / f"{output_id}.csv"
        if not out_path.exists():
            return jsonify({"error": "Not found"}), 404
        return send_file(out_path, as_attachment=True, download_name=f"dedup_results_{output_id}.csv")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
