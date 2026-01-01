"""
Matching Engine Flask Application - Refactored with modular structure.
"""

import os
from pathlib import Path

from flask import Flask

from blueprints import pages_bp, api_bp


def create_app() -> Flask:
    """Create and configure Flask application."""
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
    
    # Register blueprints
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)
    
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)

