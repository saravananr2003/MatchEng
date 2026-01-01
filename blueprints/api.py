"""
API routes blueprint with optimized handlers.
"""

import csv
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, jsonify, request, send_file, session, current_app
from werkzeug.utils import secure_filename

from core.config_manager import get_config_manager
from services.file_service import get_file_service

api_bp = Blueprint('api', __name__, url_prefix='/api')
config_manager = get_config_manager()
file_service = get_file_service()


# ==================== File Upload API ====================

@api_bp.post("/upload")
def upload_file():
    """Handle file upload with optimized preview reading."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    if not filename.lower().endswith('.csv'):
        return jsonify({"error": "Only CSV files are supported"}), 400
    
    # Generate unique filename
    file_id = str(uuid.uuid4())[:8]
    stored_filename = f"{file_id}_{filename}"
    file_path = Path(current_app.config["UPLOAD_FOLDER"]) / stored_filename
    
    try:
        file.save(str(file_path))
        
        # Use file service for optimized preview
        preview_data = file_service.read_csv_preview(file_path, max_rows=10)
        
        if "error" in preview_data:
            return jsonify({"error": preview_data["error"]}), 500
        
        # Store in session
        session['current_file'] = stored_filename
        session['file_headers'] = preview_data["headers"]
        
        return jsonify({
            "ok": True,
            "file_id": file_id,
            "filename": filename,
            "stored_filename": stored_filename,
            "headers": preview_data["headers"],
            "preview": preview_data["preview"],
            "total_rows": preview_data["total_rows"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.get("/files")
def list_files():
    """List uploaded files using file service."""
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    files = file_service.list_files(upload_dir, pattern="*.csv", sort_by="modified")
    return jsonify(files)


@api_bp.delete("/files/<filename>")
def delete_file(filename: str):
    """Delete an uploaded file."""
    file_path = Path(current_app.config["UPLOAD_FOLDER"]) / secure_filename(filename)
    
    if file_path.exists():
        # Invalidate cache
        file_service.cache.delete(f"file_info:{file_path}")
        file_path.unlink()
        return jsonify({"ok": True, "message": "File deleted"})
    else:
        return jsonify({"error": "File not found"}), 404


@api_bp.get("/file-preview/<filename>")
def file_preview(filename: str):
    """Get preview of a file using file service."""
    file_path = Path(current_app.config["UPLOAD_FOLDER"]) / secure_filename(filename)
    
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    
    preview_data = file_service.read_csv_preview(file_path, max_rows=100)
    
    if "error" in preview_data:
        return jsonify({"error": preview_data["error"]}), 500
    
    return jsonify(preview_data)


# ==================== File Processing API ====================

@api_bp.post("/process-file")
def process_uploaded_file():
    """Process an uploaded file: standardize columns and generate analytics."""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid JSON or missing Content-Type header"}), 400
        
        filename = data.get('filename')
        
        if not filename:
            return jsonify({"error": "No file specified"}), 400
        
        input_path = Path(current_app.config["UPLOAD_FOLDER"]) / secure_filename(filename)
        if not input_path.exists():
            return jsonify({"error": "File not found"}), 404
    except Exception:
        return jsonify({"error": "Invalid request format"}), 400
    
    try:
        from file_processor import process_file
        
        result = process_file(
            input_path=str(input_path),
            output_dir=current_app.config["PROCESS_FOLDER"],
            columns_metadata_path=current_app.config["COLUMNS_METADATA_PATH"]
        )
        
        if "error" in result:
            return jsonify(result), 500
        
        # Store in session
        session['processed_file'] = result.get('processed_filename')
        session['analytics_file'] = result.get('analytics_filename')
        
        return jsonify(result)
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error processing file: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "Failed to process file. Please check the file format and try again."}), 500


@api_bp.get("/processed-files")
def list_processed_files():
    """List processed files using file service."""
    process_dir = Path(current_app.config["PROCESS_FOLDER"])
    files = []
    
    for f in process_dir.glob("*_processed.csv"):
        info = file_service.get_file_info(f)
        if info:
            # Check for corresponding analytics file
            analytics_name = f.name.replace("_processed.csv", "_analytics.json")
            analytics_path = process_dir / analytics_name
            
            info["has_analytics"] = analytics_path.exists()
            info["analytics_filename"] = analytics_name if analytics_path.exists() else None
            files.append(info)
    
    # Sort by modified time (already sorted by file_service, but ensure)
    files.sort(key=lambda x: x.get("modified", ""), reverse=True)
    return jsonify(files)


@api_bp.get("/processed-file-preview/<filename>")
def processed_file_preview(filename: str):
    """Get preview of a processed file."""
    safe_filename = secure_filename(filename)
    if not safe_filename.endswith('_processed.csv'):
        return jsonify({"error": "Invalid file format. Expected filename ending with '_processed.csv'"}), 400
    
    from file_processor import get_processed_file_preview
    
    result = get_processed_file_preview(
        processed_filename=safe_filename,
        process_dir=current_app.config["PROCESS_FOLDER"]
    )
    
    if "error" in result:
        return jsonify(result), 404
    
    return jsonify(result)


@api_bp.get("/analytics/<filename>")
def get_analytics(filename: str):
    """Get analytics for a processed file."""
    safe_filename = secure_filename(filename)
    if not safe_filename.endswith('_analytics.json'):
        return jsonify({"error": "Invalid file format. Expected filename ending with '_analytics.json'"}), 400
    
    from file_processor import load_analytics
    
    result = load_analytics(
        analytics_filename=safe_filename,
        process_dir=current_app.config["PROCESS_FOLDER"]
    )
    
    if "error" in result:
        return jsonify(result), 404
    
    return jsonify(result)


@api_bp.delete("/processed-files/<filename>")
def delete_processed_file(filename: str):
    """Delete a processed file and its analytics."""
    safe_filename = secure_filename(filename)
    if not safe_filename.endswith('_processed.csv'):
        return jsonify({"error": "Invalid file format. Expected filename ending with '_processed.csv'"}), 400
    
    process_dir = Path(current_app.config["PROCESS_FOLDER"])
    file_path = process_dir / safe_filename
    
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    
    # Delete the processed file
    file_service.cache.delete(f"file_info:{file_path}")
    file_path.unlink()
    
    # Delete corresponding analytics file if exists
    analytics_name = safe_filename.replace("_processed.csv", "_analytics.json")
    analytics_path = process_dir / analytics_name
    if analytics_path.exists():
        analytics_path.unlink()
    
    return jsonify({"ok": True, "message": "File deleted"})


# ==================== Processing API ====================

@api_bp.post("/process")
def run_process():
    """Run the matching process."""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid JSON or missing Content-Type header"}), 400
        
        processed_filename = data.get('processed_filename')
        if processed_filename:
            safe_filename = secure_filename(processed_filename)
            if not safe_filename.endswith('_processed.csv'):
                return jsonify({"error": "Invalid file format. Expected filename ending with '_processed.csv'"}), 400
            
            input_path = Path(current_app.config["PROCESS_FOLDER"]) / safe_filename
            if not input_path.exists():
                return jsonify({"error": "Processed file not found"}), 404
            
            field_mapping = None
        else:
            filename = data.get('filename')
            if not filename:
                return jsonify({"error": "No file specified"}), 400
            
            input_path = Path(current_app.config["UPLOAD_FOLDER"]) / secure_filename(filename)
            if not input_path.exists():
                return jsonify({"error": "File not found"}), 404
            
            field_mapping = data.get('field_mapping', {})
        
        output_columns = data.get('output_columns', [])
        
        # Generate output filename
        output_id = str(uuid.uuid4())[:8]
        output_filename = f"matched_{output_id}.csv"
        output_path = Path(current_app.config["OUTPUT_FOLDER"]) / output_filename
        
        try:
            from matching_engine import run_matching
            
            stats = run_matching(
                input_file=str(input_path),
                output_file=str(output_path),
                field_mapping=field_mapping,
                selected_output_columns=output_columns if output_columns else None
            )
            
            stats['output_filename'] = output_filename
            stats['download_url'] = f"/download/{output_filename}"
            
            # Store in session
            session['last_output'] = output_filename
            session['last_stats'] = stats
            
            return jsonify({"ok": True, "stats": stats})
        except Exception as e:
            import traceback
            current_app.logger.error(f"Error running matching process: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"error": "Failed to process matching. Please check your configuration and try again."}), 500
    except Exception:
        return jsonify({"error": "Invalid request format"}), 400


@api_bp.get("/download/<filename>")
def download_file(filename: str):
    """Download output file."""
    file_path = Path(current_app.config["OUTPUT_FOLDER"]) / secure_filename(filename)
    
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=filename
    )


@api_bp.get("/output-files")
def list_output_files():
    """List output files using file service."""
    output_dir = Path(current_app.config["OUTPUT_FOLDER"])
    files = file_service.list_files(output_dir, pattern="*.csv", sort_by="modified")
    
    # Add download URLs
    for file_info in files:
        file_info["download_url"] = f"/download/{file_info['filename']}"
    
    return jsonify(files)


# ==================== Settings API ====================

@api_bp.get("/settings")
def get_settings():
    """Get all settings with caching."""
    settings = config_manager.load_config(current_app.config["SETTINGS_PATH"])
    return jsonify(settings)


@api_bp.post("/settings")
def update_settings():
    """Update settings."""
    try:
        new_settings = request.get_json()
        if not new_settings:
            return jsonify({"error": "No settings data provided"}), 400
        
        if config_manager.save_config(current_app.config["SETTINGS_PATH"], new_settings):
            return jsonify({"ok": True, "message": "Settings saved successfully"})
        else:
            return jsonify({"error": "Failed to save settings"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.patch("/settings/<section>")
def update_settings_section(section: str):
    """Update a specific settings section."""
    try:
        settings = config_manager.load_config(current_app.config["SETTINGS_PATH"])
        section_data = request.get_json()
        
        if not section_data:
            return jsonify({"error": "No data provided"}), 400
        
        settings[section] = section_data
        
        if config_manager.save_config(current_app.config["SETTINGS_PATH"], settings):
            return jsonify({"ok": True, "message": f"Section '{section}' updated"})
        else:
            return jsonify({"error": "Failed to save settings"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== Rules API ====================

@api_bp.get("/rules")
def get_rules():
    """Get all rules with caching."""
    rules_config = config_manager.load_config(current_app.config["RULES_PATH"])
    return jsonify(rules_config)


@api_bp.post("/rules")
def create_rule():
    """Create a new rule."""
    try:
        rules_config = config_manager.load_config(current_app.config["RULES_PATH"])
        rules = rules_config.get("rules", {})
        new_rule = request.get_json()
        
        if not new_rule or "name" not in new_rule:
            return jsonify({"error": "Rule name is required"}), 400
        
        rule_id = new_rule.get("id") or new_rule["name"].lower().replace(" ", "_")
        rules[rule_id] = new_rule
        rules_config["rules"] = rules
        
        if config_manager.save_config(current_app.config["RULES_PATH"], rules_config):
            return jsonify({"ok": True, "rule_id": rule_id, "message": "Rule created"})
        else:
            return jsonify({"error": "Failed to save rule"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.put("/rules/<rule_id>")
def update_rule(rule_id: str):
    """Update an existing rule."""
    try:
        rules_config = config_manager.load_config(current_app.config["RULES_PATH"])
        rules = rules_config.get("rules", {})
        
        if rule_id not in rules:
            return jsonify({"error": "Rule not found"}), 404
        
        updated_rule = request.get_json()
        rules[rule_id] = updated_rule
        rules_config["rules"] = rules
        
        if config_manager.save_config(current_app.config["RULES_PATH"], rules_config):
            return jsonify({"ok": True, "message": "Rule updated"})
        else:
            return jsonify({"error": "Failed to save rule"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.get("/rules/<rule_id>")
def get_rule(rule_id: str):
    """Get a specific rule."""
    rules_config = config_manager.load_config(current_app.config["RULES_PATH"])
    rules = rules_config.get("rules", {})
    
    if rule_id in rules:
        return jsonify(rules[rule_id])
    else:
        return jsonify({"error": "Rule not found"}), 404


# ==================== Columns API ====================

@api_bp.get("/columns")
def get_columns():
    """Get column metadata with caching."""
    columns = config_manager.load_config(current_app.config["COLUMNS_METADATA_PATH"])
    return jsonify(columns)


@api_bp.post("/columns")
def update_columns():
    """Update column metadata."""
    try:
        new_columns = request.get_json()
        if not new_columns:
            return jsonify({"error": "No column data provided"}), 400
        
        if config_manager.save_config(current_app.config["COLUMNS_METADATA_PATH"], new_columns):
            return jsonify({"ok": True, "message": "Columns saved"})
        else:
            return jsonify({"error": "Failed to save columns"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.get("/column-config")
def get_column_config():
    """Get column configuration with caching."""
    config = config_manager.load_config(current_app.config["COLUMN_CONFIG_PATH"])
    return jsonify(config)


@api_bp.post("/column-config")
def update_column_config():
    """Update column configuration."""
    try:
        new_config = request.get_json()
        if not new_config:
            return jsonify({"error": "No config data provided"}), 400
        
        if config_manager.save_config(current_app.config["COLUMN_CONFIG_PATH"], new_config):
            return jsonify({"ok": True, "message": "Column config saved"})
        else:
            return jsonify({"error": "Failed to save config"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== Field Mapping API ====================

@api_bp.post("/auto-map")
def auto_map_fields():
    """Auto-map fields using column metadata."""
    try:
        data = request.get_json()
        headers = data.get('headers', [])
        
        if not headers:
            return jsonify({"error": "No headers provided"}), 400
        
        columns_metadata = config_manager.load_config(current_app.config["COLUMNS_METADATA_PATH"])
        
        mapping = {}
        confidence = {}
        
        for header in headers:
            header_lower = header.lower()
            best_match = None
            best_score = 0
            
            for col_name, col_meta in columns_metadata.items():
                # Check exact match
                if header_lower == col_name.lower():
                    best_match = col_name
                    best_score = 1.0
                    break
                
                # Check alternate names
                alt_names = col_meta.get("alternate_names", [])
                for alt in alt_names:
                    if header_lower == alt.lower():
                        best_match = col_name
                        best_score = 0.9
                        break
                
                if best_score >= 0.9:
                    break
            
            if best_match:
                mapping[header] = best_match
                confidence[header] = best_score
        
        return jsonify({
            "mapping": mapping,
            "confidence": confidence
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

