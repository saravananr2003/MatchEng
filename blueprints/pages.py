"""
Page routes blueprint.
"""

from flask import Blueprint, render_template

pages_bp = Blueprint('pages', __name__)


@pages_bp.get("/")
def index():
    return render_template("index.html")


@pages_bp.get("/settings")
def settings_page():
    return render_template("settings.html")


@pages_bp.get("/rules")
def rules_page():
    return render_template("rules.html")


@pages_bp.get("/columns")
def columns_page():
    return render_template("columns.html")


@pages_bp.get("/upload")
def upload_page():
    return render_template("upload.html")


@pages_bp.get("/map_fields")
def map_fields_page():
    return render_template("map_fields.html")


@pages_bp.get("/process")
def process_page():
    return render_template("process.html")


@pages_bp.get("/results")
def results_page():
    return render_template("results.html")


@pages_bp.get("/analytics")
def analytics_page():
    return render_template("analytics.html")

