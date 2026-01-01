import csv
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request, send_file, session
from werkzeug.utils import secure_filename


def load_json_config(file_path: str) -> Dict[str, Any]:
    """Load JSON configuration file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json_config(file_path: str, data: Dict[str, Any]) -> bool:
    """Save JSON configuration file."""
    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception:
        return False


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Configuration paths
    base_dir = Path(__file__).parent
    config_dir = base_dir / "config"
    app.config["SETTINGS_PATH"] = str(config_dir / "settings.json")
    app.config["RULES_PATH"] = str(config_dir / "rules.json")
    app.config["COLUMNS_METADATA_PATH"] = str(config_dir / "columns_metadata.json")
    app.config["COLUMN_CONFIG_PATH"] = str(config_dir / "column_config.json")
    
    # File paths
    app.config["UPLOAD_FOLDER"] = str(base_dir / "datafiles" / "incoming")
    app.config["OUTPUT_FOLDER"] = str(base_dir / "datafiles" / "output")
    app.config["PROCESS_FOLDER"] = str(base_dir / "datafiles" / "process")
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB
    
    # Ensure directories exist
    config_dir.mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["OUTPUT_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["PROCESS_FOLDER"]).mkdir(parents=True, exist_ok=True)

    # ==================== Pages ====================

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/settings")
    def settings_page():
        return render_template("settings.html")
    
    @app.get("/rules")
    def rules_page():
        return render_template("rules.html")
    
    @app.get("/columns")
    def columns_page():
        return render_template("columns.html")
    
    @app.get("/upload")
    def upload_page():
        return render_template("upload.html")
    
    @app.get("/map_fields")
    def map_fields_page():
        return render_template("map_fields.html")
    
    @app.get("/process")
    def process_page():
        return render_template("process.html")
    
    @app.get("/results")
    def results_page():
        return render_template("results.html")
    
    @app.get("/analytics")
    def analytics_page():
        return render_template("analytics.html")

    # ==================== File Upload API ====================

    @app.post("/api/upload")
    def upload_file():
        """Handle file upload."""
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
        file_path = Path(app.config["UPLOAD_FOLDER"]) / stored_filename
        
        try:
            file.save(str(file_path))
            
            # Read preview
            preview_rows = []
            headers = []
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                for i, row in enumerate(reader):
                    if i >= 10:  # Preview first 10 rows
                        break
                    preview_rows.append(dict(row))
            
            # Count total rows
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                total_rows = sum(1 for _ in f) - 1  # Subtract header
            
            # Store in session
            session['current_file'] = stored_filename
            session['file_headers'] = headers
            
            return jsonify({
                "ok": True,
                "file_id": file_id,
                "filename": filename,
                "stored_filename": stored_filename,
                "headers": headers,
                "preview": preview_rows,
                "total_rows": total_rows
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.get("/api/files")
    def list_files():
        """List uploaded files."""
        upload_dir = Path(app.config["UPLOAD_FOLDER"])
        files = []
        
        for f in upload_dir.glob("*.csv"):
            stat = f.stat()
            files.append({
                "filename": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return jsonify(sorted(files, key=lambda x: x['modified'], reverse=True))
    
    @app.delete("/api/files/<filename>")
    def delete_file(filename: str):
        """Delete an uploaded file."""
        file_path = Path(app.config["UPLOAD_FOLDER"]) / secure_filename(filename)
        
        if file_path.exists():
            file_path.unlink()
            return jsonify({"ok": True, "message": "File deleted"})
        else:
            return jsonify({"error": "File not found"}), 404
    
    @app.get("/api/file-preview/<filename>")
    def file_preview(filename: str):
        """Get preview of a file."""
        file_path = Path(app.config["UPLOAD_FOLDER"]) / secure_filename(filename)
        
        if not file_path.exists():
            return jsonify({"error": "File not found"}), 404
        
        try:
            preview_rows = []
            headers = []
            total_rows = 0
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                for i, row in enumerate(reader):
                    total_rows = i + 1
                    if i < 100:
                        preview_rows.append(dict(row))
            
            return jsonify({
                "headers": headers,
                "preview": preview_rows,
                "total_rows": total_rows
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==================== File Processing API ====================
    
    @app.post("/api/process-file")
    def process_uploaded_file():
        """Process an uploaded file: standardize columns and generate analytics."""
        try:
            data = request.get_json()
            if data is None:
                return jsonify({"error": "Invalid JSON or missing Content-Type header"}), 400
            
            filename = data.get('filename')
            
            if not filename:
                return jsonify({"error": "No file specified"}), 400
            
            input_path = Path(app.config["UPLOAD_FOLDER"]) / secure_filename(filename)
            if not input_path.exists():
                return jsonify({"error": "File not found"}), 404
        except Exception:
            return jsonify({"error": "Invalid request format"}), 400
        
        try:
            from file_processor import process_file
            
            result = process_file(
                input_path=str(input_path),
                output_dir=app.config["PROCESS_FOLDER"],
                columns_metadata_path=app.config["COLUMNS_METADATA_PATH"]
            )
            
            if "error" in result:
                return jsonify(result), 500
            
            # Store in session
            session['processed_file'] = result.get('processed_filename')
            session['analytics_file'] = result.get('analytics_filename')
            
            return jsonify(result)
        except Exception as e:
            import traceback
            # Log full traceback server-side for debugging
            app.logger.error(f"Error processing file: {str(e)}\n{traceback.format_exc()}")
            # Return safe error message to client (no sensitive information)
            return jsonify({"error": "Failed to process file. Please check the file format and try again."}), 500
    
    @app.get("/api/processed-files")
    def list_processed_files():
        """List processed files."""
        process_dir = Path(app.config["PROCESS_FOLDER"])
        files = []
        
        for f in process_dir.glob("*_processed.csv"):
            stat = f.stat()
            # Check for corresponding analytics file
            analytics_name = f.name.replace("_processed.csv", "_analytics.json")
            analytics_path = process_dir / analytics_name
            
            files.append({
                "filename": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "has_analytics": analytics_path.exists(),
                "analytics_filename": analytics_name if analytics_path.exists() else None
            })
        
        return jsonify(sorted(files, key=lambda x: x['modified'], reverse=True))
    
    @app.get("/api/processed-file-preview/<filename>")
    def processed_file_preview(filename: str):
        """Get preview of a processed file."""
        # Validate filename format
        safe_filename = secure_filename(filename)
        if not safe_filename.endswith('_processed.csv'):
            return jsonify({"error": "Invalid file format. Expected filename ending with '_processed.csv'"}), 400
        
        from file_processor import get_processed_file_preview
        
        result = get_processed_file_preview(
            processed_filename=safe_filename,
            process_dir=app.config["PROCESS_FOLDER"]
        )
        
        if "error" in result:
            return jsonify(result), 404
        
        return jsonify(result)
    
    @app.get("/api/analytics/<filename>")
    def get_analytics(filename: str):
        """Get analytics for a processed file."""
        # Validate filename format
        safe_filename = secure_filename(filename)
        if not safe_filename.endswith('_analytics.json'):
            return jsonify({"error": "Invalid file format. Expected filename ending with '_analytics.json'"}), 400
        
        from file_processor import load_analytics
        
        result = load_analytics(
            analytics_filename=safe_filename,
            process_dir=app.config["PROCESS_FOLDER"]
        )
        
        if "error" in result:
            return jsonify(result), 404
        
        return jsonify(result)
    
    @app.delete("/api/processed-files/<filename>")
    def delete_processed_file(filename: str):
        """Delete a processed file and its analytics."""
        # Validate filename format
        safe_filename = secure_filename(filename)
        if not safe_filename.endswith('_processed.csv'):
            return jsonify({"error": "Invalid file format. Expected filename ending with '_processed.csv'"}), 400
        
        process_dir = Path(app.config["PROCESS_FOLDER"])
        file_path = process_dir / safe_filename
        
        if not file_path.exists():
            return jsonify({"error": "File not found"}), 404
        
        # Delete the processed file
        file_path.unlink()
        
        # Delete corresponding analytics file if exists
        # Derive analytics name from sanitized filename to prevent path traversal
        analytics_name = safe_filename.replace("_processed.csv", "_analytics.json")
        analytics_path = process_dir / analytics_name
        if analytics_path.exists():
            analytics_path.unlink()
        
        return jsonify({"ok": True, "message": "File deleted"})

    # ==================== Field Mapping API ====================
    
    @app.post("/api/auto-map")
    def auto_map_fields():
        """Auto-map source columns to standard columns."""
        data = request.get_json()
        source_headers = data.get('headers', [])
        
        columns_metadata = load_json_config(app.config["COLUMNS_METADATA_PATH"])
        
        mapping = {}
        confidence = {}
        
        for source_col in source_headers:
            source_upper = source_col.upper().strip()
            best_match = None
            best_score = 0
            
            for std_col, meta in columns_metadata.items():
                # Check exact match
                if source_upper == std_col.upper():
                    best_match = std_col
                    best_score = 100
                    break
                
                # Check alternate names
                alternates = [a.upper() for a in meta.get('alternate_columns', [])]
                if source_upper in alternates:
                    best_match = std_col
                    best_score = 95
                    break
                
                # Check partial match
                if std_col.upper() in source_upper or source_upper in std_col.upper():
                    if best_score < 70:
                        best_match = std_col
                        best_score = 70
            
            if best_match and best_score >= 70:
                mapping[source_col] = best_match
                confidence[source_col] = best_score
        
        return jsonify({
            "mapping": mapping,
            "confidence": confidence
        })

    # ==================== Processing API ====================
    
    @app.post("/api/process")
    def run_process():
        """Run the matching process."""
        try:
            data = request.get_json()
            if data is None:
                return jsonify({"error": "Invalid JSON or missing Content-Type header"}), 400
            
            # Check if this is a processed file from analytics
            processed_filename = data.get('processed_filename')
            if processed_filename:
                # Validate filename format
                safe_filename = secure_filename(processed_filename)
                if not safe_filename.endswith('_processed.csv'):
                    return jsonify({"error": "Invalid file format. Expected filename ending with '_processed.csv'"}), 400
                
                input_path = Path(app.config["PROCESS_FOLDER"]) / safe_filename
                if not input_path.exists():
                    return jsonify({"error": "Processed file not found"}), 404
                
                # No field mapping needed for processed files (already standardized)
                field_mapping = None
            else:
                # Legacy upload flow
                filename = data.get('filename')
                if not filename:
                    return jsonify({"error": "No file specified"}), 400
                
                input_path = Path(app.config["UPLOAD_FOLDER"]) / secure_filename(filename)
                if not input_path.exists():
                    return jsonify({"error": "File not found"}), 404
                
                field_mapping = data.get('field_mapping', {})
            
            output_columns = data.get('output_columns', [])
            
            # Generate output filename
            output_id = str(uuid.uuid4())[:8]
            output_filename = f"matched_{output_id}.csv"
            output_path = Path(app.config["OUTPUT_FOLDER"]) / output_filename
            
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
                # Log full traceback server-side for debugging
                app.logger.error(f"Error running matching process: {str(e)}\n{traceback.format_exc()}")
                # Return safe error message to client (no sensitive information)
                return jsonify({"error": "Failed to process matching. Please check your configuration and try again."}), 500
        except Exception:
            return jsonify({"error": "Invalid request format"}), 400
    
    @app.get("/download/<filename>")
    def download_file(filename: str):
        """Download output file."""
        file_path = Path(app.config["OUTPUT_FOLDER"]) / secure_filename(filename)
        
        if not file_path.exists():
            return jsonify({"error": "File not found"}), 404
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename
        )
    
    @app.get("/api/output-files")
    def list_output_files():
        """List output files."""
        output_dir = Path(app.config["OUTPUT_FOLDER"])
        files = []
        
        for f in output_dir.glob("*.csv"):
            stat = f.stat()
            files.append({
                "filename": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "download_url": f"/download/{f.name}"
            })
        
        return jsonify(sorted(files, key=lambda x: x['modified'], reverse=True))

    # ==================== Settings API ====================
    
    @app.get("/api/settings")
    def get_settings():
        """Get all settings."""
        settings = load_json_config(app.config["SETTINGS_PATH"])
        return jsonify(settings)
    
    @app.post("/api/settings")
    def update_settings():
        """Update settings."""
        try:
            new_settings = request.get_json()
            if not new_settings:
                return jsonify({"error": "No settings data provided"}), 400
            
            if save_json_config(app.config["SETTINGS_PATH"], new_settings):
                return jsonify({"ok": True, "message": "Settings saved successfully"})
            else:
                return jsonify({"error": "Failed to save settings"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.patch("/api/settings/<section>")
    def update_settings_section(section: str):
        """Update a specific settings section."""
        try:
            settings = load_json_config(app.config["SETTINGS_PATH"])
            section_data = request.get_json()
            
            if not section_data:
                return jsonify({"error": "No data provided"}), 400
            
            settings[section] = section_data
            
            if save_json_config(app.config["SETTINGS_PATH"], settings):
                return jsonify({"ok": True, "message": f"Section '{section}' updated"})
            else:
                return jsonify({"error": "Failed to save settings"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==================== Rules API ====================
    
    @app.get("/api/rules")
    def get_rules():
        """Get all matching rules."""
        rules_config = load_json_config(app.config["RULES_PATH"])
        return jsonify(rules_config)
    
    @app.post("/api/rules")
    def update_rules():
        """Update all rules."""
        try:
            new_rules = request.get_json()
            if not new_rules:
                return jsonify({"error": "No rules data provided"}), 400
            
            if save_json_config(app.config["RULES_PATH"], new_rules):
                return jsonify({"ok": True, "message": "Rules saved successfully"})
            else:
                return jsonify({"error": "Failed to save rules"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.get("/api/rules/<rule_id>")
    def get_rule(rule_id: str):
        """Get a specific rule."""
        rules_config = load_json_config(app.config["RULES_PATH"])
        rules = rules_config.get("rules", {})
        
        if rule_id in rules:
            return jsonify(rules[rule_id])
        else:
            return jsonify({"error": "Rule not found"}), 404
    
    @app.put("/api/rules/<rule_id>")
    def update_rule(rule_id: str):
        """Update or create a specific rule."""
        try:
            rule_data = request.get_json()
            if not rule_data:
                return jsonify({"error": "No rule data provided"}), 400
            
            rules_config = load_json_config(app.config["RULES_PATH"])
            if "rules" not in rules_config:
                rules_config["rules"] = {}
            
            rule_data["id"] = rule_id
            rules_config["rules"][rule_id] = rule_data
            
            if save_json_config(app.config["RULES_PATH"], rules_config):
                return jsonify({"ok": True, "message": f"Rule '{rule_id}' saved"})
            else:
                return jsonify({"error": "Failed to save rule"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.delete("/api/rules/<rule_id>")
    def delete_rule(rule_id: str):
        """Delete a specific rule."""
        try:
            rules_config = load_json_config(app.config["RULES_PATH"])
            rules = rules_config.get("rules", {})
            
            if rule_id in rules:
                del rules[rule_id]
                rules_config["rules"] = rules
                
                if save_json_config(app.config["RULES_PATH"], rules_config):
                    return jsonify({"ok": True, "message": f"Rule '{rule_id}' deleted"})
                else:
                    return jsonify({"error": "Failed to save changes"}), 500
            else:
                return jsonify({"error": "Rule not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.patch("/api/rules/<rule_id>/toggle")
    def toggle_rule(rule_id: str):
        """Toggle a rule's enabled status."""
        try:
            rules_config = load_json_config(app.config["RULES_PATH"])
            rules = rules_config.get("rules", {})
            
            if rule_id in rules:
                rules[rule_id]["enabled"] = not rules[rule_id].get("enabled", True)
                rules_config["rules"] = rules
                
                if save_json_config(app.config["RULES_PATH"], rules_config):
                    status = "enabled" if rules[rule_id]["enabled"] else "disabled"
                    return jsonify({"ok": True, "message": f"Rule '{rule_id}' {status}", "enabled": rules[rule_id]["enabled"]})
                else:
                    return jsonify({"error": "Failed to save changes"}), 500
            else:
                return jsonify({"error": "Rule not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==================== Columns Metadata API ====================
    
    @app.get("/api/columns")
    def get_columns():
        """Get columns metadata."""
        columns = load_json_config(app.config["COLUMNS_METADATA_PATH"])
        return jsonify(columns)
    
    @app.post("/api/columns")
    def update_columns():
        """Update columns metadata."""
        try:
            new_columns = request.get_json()
            if not new_columns:
                return jsonify({"error": "No columns data provided"}), 400
            
            if save_json_config(app.config["COLUMNS_METADATA_PATH"], new_columns):
                return jsonify({"ok": True, "message": "Columns metadata saved"})
            else:
                return jsonify({"error": "Failed to save columns"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.get("/api/columns/<column_name>")
    def get_column(column_name: str):
        """Get a specific column's metadata."""
        columns = load_json_config(app.config["COLUMNS_METADATA_PATH"])
        
        if column_name in columns:
            return jsonify(columns[column_name])
        else:
            return jsonify({"error": "Column not found"}), 404
    
    @app.put("/api/columns/<column_name>")
    def update_column(column_name: str):
        """Update or create a column's metadata."""
        try:
            column_data = request.get_json()
            if not column_data:
                return jsonify({"error": "No column data provided"}), 400
            
            columns = load_json_config(app.config["COLUMNS_METADATA_PATH"])
            columns[column_name] = column_data
            
            if save_json_config(app.config["COLUMNS_METADATA_PATH"], columns):
                return jsonify({"ok": True, "message": f"Column '{column_name}' saved"})
            else:
                return jsonify({"error": "Failed to save column"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.delete("/api/columns/<column_name>")
    def delete_column(column_name: str):
        """Delete a column's metadata."""
        try:
            columns = load_json_config(app.config["COLUMNS_METADATA_PATH"])
            
            if column_name in columns:
                del columns[column_name]
                
                if save_json_config(app.config["COLUMNS_METADATA_PATH"], columns):
                    return jsonify({"ok": True, "message": f"Column '{column_name}' deleted"})
                else:
                    return jsonify({"error": "Failed to save changes"}), 500
            else:
                return jsonify({"error": "Column not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==================== Column Config API ====================
    
    @app.get("/api/column-config")
    def get_column_config():
        """Get column configuration (groups and display settings)."""
        config = load_json_config(app.config["COLUMN_CONFIG_PATH"])
        return jsonify(config)
    
    @app.post("/api/column-config")
    def update_column_config():
        """Update column configuration."""
        try:
            new_config = request.get_json()
            if not new_config:
                return jsonify({"error": "No config data provided"}), 400
            
            if save_json_config(app.config["COLUMN_CONFIG_PATH"], new_config):
                return jsonify({"ok": True, "message": "Column config saved"})
            else:
                return jsonify({"error": "Failed to save config"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)

