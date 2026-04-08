"""
FitPulse Health Anomaly Detection System
Flask backend — main application entry point
"""

import os
import json
import uuid
from flask import Flask, request, jsonify, render_template, session, send_file
from werkzeug.utils import secure_filename
from utils.data_processor import process_health_data
from utils.anomaly_detector import detect_anomalies
from utils.report_generator import generate_report, generate_pdf_report

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fitpulse-dev-secret-2024")

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-memory session store (replace with Redis/DB in production)
SESSION_STORE = {}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── PAGES ────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload")
def upload_page():
    return render_template("upload.html")


@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


@app.route("/report")
def report_page():
    return render_template("report.html")


# ─── API ENDPOINTS ─────────────────────────────────────────────────────────────

@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Handle file upload, process data, run anomaly detection."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Please upload CSV or Excel (.xlsx/.xls)"}), 400

    # Save file
    filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        # Process and clean data
        df, processing_log = process_health_data(filepath)

        # Detect anomalies
        df, anomaly_stats = detect_anomalies(df)

        # Build session data
        session_id = str(uuid.uuid4())
        records = df.to_dict(orient="records")
        # Convert numpy types to Python native for JSON serialization
        for r in records:
            for k, v in r.items():
                if hasattr(v, "item"):
                    r[k] = v.item()

        SESSION_STORE[session_id] = {
            "records":        records,
            "processing_log": processing_log,
            "anomaly_stats":  anomaly_stats,
            "filename":       file.filename,
        }

        # Cleanup uploaded file
        os.remove(filepath)

        return jsonify({"session_id": session_id, "rows": len(records), "filename": file.filename})

    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": str(e)}), 500


@app.route("/api/dashboard/<session_id>")
def get_dashboard_data(session_id):
    """Return dashboard metrics and chart data."""
    data = SESSION_STORE.get(session_id)
    if not data:
        return jsonify({"error": "Session expired or not found"}), 404

    records = data["records"]
    anomaly_stats = data["anomaly_stats"]

    heart_rates = [r["HeartRate"] for r in records if r.get("HeartRate") is not None]
    steps       = [r["Steps"]     for r in records if r.get("Steps")     is not None]
    anomalies   = [r for r in records if r.get("Anomaly") == "Yes"]

    # Heart rate classification counts
    low_count    = sum(1 for r in records if r.get("HR_Category") == "Low")
    normal_count = sum(1 for r in records if r.get("HR_Category") == "Normal")
    high_count   = sum(1 for r in records if r.get("HR_Category") == "High")

    # Gender breakdown
    gender_counts = {}
    for r in records:
        g = str(r.get("Gender", "Unknown"))
        gender_counts[g] = gender_counts.get(g, 0) + 1

    return jsonify({
        "summary": {
            "total_records":    len(records),
            "avg_heart_rate":   round(sum(heart_rates) / len(heart_rates), 1) if heart_rates else 0,
            "max_heart_rate":   max(heart_rates) if heart_rates else 0,
            "min_heart_rate":   min(heart_rates) if heart_rates else 0,
            "anomaly_count":    len(anomalies),
            "anomaly_pct":      round(len(anomalies) / len(records) * 100, 1) if records else 0,
            "filename":         data["filename"],
        },
        "charts": {
            "heart_rates":    heart_rates[:200],
            "steps":          steps[:200],
            "hr_low":         low_count,
            "hr_normal":      normal_count,
            "hr_high":        high_count,
            "gender_counts":  gender_counts,
            "anomaly_flags":  [1 if r.get("Anomaly") == "Yes" else 0 for r in records[:200]],
        },
        "anomaly_stats": anomaly_stats,
        "processing_log": data["processing_log"],
    })


@app.route("/api/report/<session_id>")
def get_report(session_id):
    """Return detailed report data."""
    data = SESSION_STORE.get(session_id)
    if not data:
        return jsonify({"error": "Session expired or not found"}), 404

    report = generate_report(data["records"], data["anomaly_stats"], data["processing_log"])
    return jsonify(report)


@app.route("/api/report/<session_id>/pdf")
def download_pdf(session_id):
    """Generate and download PDF report."""
    data = SESSION_STORE.get(session_id)
    if not data:
        return jsonify({"error": "Session expired or not found"}), 404

    report = generate_report(data["records"], data["anomaly_stats"], data["processing_log"])
    pdf_path = generate_pdf_report(report, data["filename"])
    return send_file(pdf_path, as_attachment=True, download_name="fitpulse_report.pdf")


@app.route("/api/records/<session_id>")
def get_records(session_id):
    """Return paginated records for data table."""
    data = SESSION_STORE.get(session_id)
    if not data:
        return jsonify({"error": "Session expired or not found"}), 404

    page     = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    records  = data["records"]
    start    = (page - 1) * per_page
    end      = start + per_page

    return jsonify({
        "records":    records[start:end],
        "total":      len(records),
        "page":       page,
        "per_page":   per_page,
        "total_pages": -(-len(records) // per_page),
    })


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)
