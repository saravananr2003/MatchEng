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


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", str(10 * 1024 * 1024)))
    app.config["DATA_DIR"] = os.getenv("DATA_DIR", str(Path(__file__).parent / "data"))
    app.config["OUTPUT_DIR"] = os.getenv("OUTPUT_DIR", str(Path(__file__).parent / "outputs"))
    app.config["DB_PATH"] = os.getenv(
        "DB_PATH", str(Path(app.config["DATA_DIR"]) / "matches.db")
    )

    Path(app.config["DATA_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["OUTPUT_DIR"]).mkdir(parents=True, exist_ok=True)

    ensure_db(app.config["DB_PATH"])

    @app.get("/")
    def index():
        return render_template("index.html")

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
        # IMPORTANT: Do not filter out whitespace-only lines before CSV parsing.
        # Multi-line quoted fields can legally contain blank/whitespace-only lines,
        # and removing them corrupts the CSV structure.
        raw = raw.lstrip("\ufeff")
        if not raw.strip():
            return jsonify({"error": "Uploaded CSV is empty"}), 400

        import csv
        from io import StringIO

        reader = csv.DictReader(StringIO(raw, newline=""))

        required = {
            "Source Type",
            "Source ID",
            "Company Name",
            "Address",
            "Phone Number",
        }
        missing = [c for c in required if c not in (reader.fieldnames or [])]
        if missing:
            return (
                jsonify(
                    {
                        "error": "Missing required columns",
                        "missing": missing,
                        "found": reader.fieldnames or [],
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

        for row in reader:
            # Skip completely empty rows (e.g., stray blank lines between records).
            if not row or not any((v or "").strip() for v in row.values()):
                continue
            stats["processed"] += 1
            try:
                source_type = (row.get("Source Type") or "").strip()
                source_id = (row.get("Source ID") or "").strip()
                company_name_raw = (row.get("Company Name") or "").strip()
                address_raw = (row.get("Address") or "").strip()
                phone_raw = (row.get("Phone Number") or "").strip()

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
