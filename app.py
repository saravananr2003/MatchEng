import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request


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
    
    # Configuration paths
    config_dir = Path(__file__).parent / "config"
    app.config["SETTINGS_PATH"] = str(config_dir / "settings.json")
    app.config["RULES_PATH"] = str(config_dir / "rules.json")
    app.config["COLUMNS_METADATA_PATH"] = str(config_dir / "columns_metadata.json")
    app.config["COLUMN_CONFIG_PATH"] = str(config_dir / "column_config.json")
    
    # Ensure config directory exists
    config_dir.mkdir(parents=True, exist_ok=True)

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

