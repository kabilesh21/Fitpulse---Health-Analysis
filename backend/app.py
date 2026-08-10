"""
app.py
Flask main application for Strataform Clinical Analytics Suite.
"""

import os
import uuid
import tempfile
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file, redirect, session, url_for
from werkzeug.utils import secure_filename
import numpy as np

from utils.data_processor import process_health_data
from utils.anomaly_detector import detect_anomalies, calculate_risk_and_explain
from utils.report_generator import generate_report, generate_pdf_report
from utils.ml_compare import compare_models
from utils.db import (
    init_db, register_user, verify_user, add_health_record, 
    get_user_records, get_user_by_id, get_anomaly_history, get_all_patients,
    update_user_cleaning_logs, get_user_cleaning_logs,
    record_login, get_recent_logins, get_db
)

# Initialize database tables
init_db()

def sanitize_data(obj):
    if isinstance(obj, dict):
        return {k: sanitize_data(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_data(v) for v in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return sanitize_data(obj.tolist())
    else:
        return obj

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fitpulse-secret-key-12345")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# Keep sessions cache in-memory mapping to DB records for report exports
SESSIONS_CACHE = {}

# ── ROUTE WRAPPER / AUTH CHECK ────────────────────────────────────────────
def login_required(f):
    import functools
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    return render_template("index.html")

# ── AUTHENTICATION ENDPOINTS ──────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        age = int(request.form.get("age", 30))
        gender = request.form.get("gender", "Male")
        purpose = request.form.get("purpose", "Routine Check")
        
        if not username or not password or not email:
            return render_template("login.html", register_error="Please fill out all registration fields including Email.")
            
        user_id = register_user(username, email, password, age, gender, role="patient", purpose=purpose)
        if user_id:
            record_login(user_id)
            session["user_id"] = user_id
            session["username"] = username
            session["role"] = "patient"
            return redirect(url_for("upload"))
        else:
            return render_template("login.html", register_error="Username or Email already exists.")
            
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username_or_email = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        user = verify_user(username_or_email, password)
        if user:
            record_login(user["id"])
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            
            if user["role"] == "doctor":
                return redirect(url_for("doctor_dashboard"))
            else:
                return redirect(url_for("upload"))
        else:
            return render_template("login.html", login_error="Invalid credentials.")
            
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ── APP SECURED PAGES ─────────────────────────────────────────────────────
@app.route("/upload")
@login_required
def upload():
    return render_template("upload.html")

@app.route("/dashboard")
@login_required
def dashboard():
    # If Doctor logged in, they must view a patient's dashboard
    if session.get("role") == "doctor" and not request.args.get("patient_id"):
        return redirect(url_for("doctor_dashboard"))
    return render_template("dashboard.html")

@app.route("/report")
@login_required
def report():
    if session.get("role") == "doctor" and not request.args.get("patient_id"):
        return redirect(url_for("doctor_dashboard"))
    return render_template("report.html")

@app.route("/doctor_dashboard")
@login_required
def doctor_dashboard():
    if session.get("role") != "doctor":
        return redirect(url_for("upload"))
    return render_template("doctor_dashboard.html")

@app.route("/services")
def services():
    return render_template("services.html")

@app.route("/about")
def about():
    return render_template("about.html")

# ── REALTIME DATA ANALYSIS & IMPORTS ──────────────────────────────────────
@app.route("/api/session_check", methods=["GET"])
def api_session_check():
    if "user_id" not in session:
        return jsonify({"logged_in": False})
        
    patient_id = request.args.get("patient_id")
    if session.get("role") == "doctor" and patient_id:
        user_id = int(patient_id)
    else:
        user_id = session["user_id"]
        
    user_info = get_user_by_id(user_id)
    if not user_info:
        return jsonify({"logged_in": True, "has_data": False, "role": session.get("role")})
        
    records = get_user_records(user_id)
    if not records:
        return jsonify({
            "logged_in": True, 
            "has_data": False, 
            "role": session.get("role"),
            "username": user_info["username"],
            "age": user_info["age"],
            "gender": user_info["gender"],
            "purpose": user_info["purpose"]
        })
        
    # Recompile report data from user history
    history_df = pd.DataFrame(records)
    history_df = history_df.rename(columns={
        "heart_rate": "HeartRate",
        "steps": "Steps",
        "spo2": "SpO2",
        "temperature": "Temperature",
        "sleep_duration": "SleepDuration",
        "stress_level": "StressLevel",
        "systolic_bp": "SystolicBP",
        "diastolic_bp": "DiastolicBP",
        "calories": "CaloriesBurned"
    })
    
    _, final_anomaly_stats = detect_anomalies(history_df)
    sanitized_records = sanitize_data(records)
    cleaning_log = get_user_cleaning_logs(user_id) or ["Restored clinical session from patient database logs."]
    report_data = sanitize_data(generate_report(sanitized_records, final_anomaly_stats, cleaning_log))
    
    session_id = str(uuid.uuid4())
    SESSIONS_CACHE[session_id] = {
        "filename": "Database Patient Log",
        "report": report_data,
        "records": sanitized_records
    }
    
    return jsonify({
        "logged_in": True,
        "has_data": True,
        "role": session.get("role"),
        "username": user_info["username"],
        "age": user_info["age"],
        "gender": user_info["gender"],
        "purpose": user_info["purpose"],
        "session_id": session_id,
        "filename": "Database Patient Log",
        "report": report_data,
        "records": sanitized_records[-300:]
    })

@app.route("/api/upload", methods=["POST"])
@login_required
def api_upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected for uploading"}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("csv", "xlsx", "xls"):
        return jsonify({"error": "Unsupported file format. Please upload a CSV or Excel file."}), 400

    try:
        # Save file to a secure temporary directory
        filename = secure_filename(file.filename)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{filename}")
        file.save(temp_path)

        # 1. Clean and process raw health data
        df_clean, cleaning_log = process_health_data(temp_path)

        # 2. Run anomaly detection
        df_analyzed, anomaly_stats = detect_anomalies(df_clean)

        # Remove the temporary uploaded file
        try:
            os.remove(temp_path)
        except Exception:
            pass

        # If doctor logged in and patient_id is passed, upload for that patient
        patient_id = request.form.get("patient_id")
        selected_doctor = request.form.get("selected_doctor", "Dr. K. Albert")
        if session.get("role") == "doctor" and patient_id:
            user_id = int(patient_id)
        else:
            user_id = session["user_id"]
        
        # Save each row in DB
        for _, row in df_analyzed.iterrows():
            record_dict = {
                "heart_rate": float(row["HeartRate"]),
                "systolic_bp": float(row["SystolicBP"]),
                "diastolic_bp": float(row["DiastolicBP"]),
                "spo2": float(row["SpO2"]),
                "temperature": float(row["Temperature"]),
                "sleep_duration": float(row["SleepDuration"]),
                "steps": float(row["Steps"]),
                "calories": float(row["CaloriesBurned"]),
                "stress_level": float(row["StressLevel"]),
                "risk_score": float(row["Risk_Score"]),
                "risk_level": str(row["Risk_Level"]),
                "anomaly": str(row["Anomaly"]),
                "anomaly_reason": str(row["Anomaly_Reason"]),
                "source": "csv_upload",
                "selected_doctor": selected_doctor
            }
            add_health_record(user_id, record_dict)

        # Retrieve user history
        history_records = get_user_records(user_id)
        history_df = pd.DataFrame(history_records)
        history_df = history_df.rename(columns={
            "heart_rate": "HeartRate",
            "steps": "Steps",
            "spo2": "SpO2",
            "temperature": "Temperature",
            "sleep_duration": "SleepDuration",
            "stress_level": "StressLevel",
            "systolic_bp": "SystolicBP",
            "diastolic_bp": "DiastolicBP",
            "calories": "CaloriesBurned"
        })
        
        _, final_anomaly_stats = detect_anomalies(history_df)
        sanitized_records = sanitize_data(history_records)
        update_user_cleaning_logs(user_id, cleaning_log)
        report_data = sanitize_data(generate_report(sanitized_records, final_anomaly_stats, cleaning_log))

        # Create session ID
        session_id = str(uuid.uuid4())
        SESSIONS_CACHE[session_id] = {
            "filename": filename,
            "report": report_data,
            "records": sanitized_records
        }

        return jsonify({
            "session_id": session_id,
            "filename": filename,
            "report": report_data,
            "records": sanitized_records[-300:]
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/manual_entry", methods=["POST"])
@login_required
def api_manual_entry():
    try:
        data = request.json or {}
        patient_id = data.get("patient_id")
        selected_doctor = data.get("selected_doctor", "Dr. K. Albert")
        
        if session.get("role") == "doctor" and patient_id:
            user_id = int(patient_id)
        else:
            user_id = session["user_id"]
        
        mapped_row = {
            "HeartRate": data["heart_rate"],
            "Steps": data["steps"],
            "SpO2": data["spo2"],
            "Temperature": data["temperature"],
            "SleepDuration": data["sleep_duration"],
            "StressLevel": data["stress_level"],
            "SystolicBP": data["systolic_bp"],
            "DiastolicBP": data["diastolic_bp"],
            "CaloriesBurned": data["calories"]
        }
        
        risk_score, risk_level, anomaly_reason = calculate_risk_and_explain(mapped_row)
        anomaly = "No"
        if risk_level == "High" or data["heart_rate"] > 150 or data["heart_rate"] < 40 or data["spo2"] < 90:
            anomaly = "Yes"
            
        record_dict = {
            "heart_rate": data["heart_rate"],
            "systolic_bp": data["systolic_bp"],
            "diastolic_bp": data["diastolic_bp"],
            "spo2": data["spo2"],
            "temperature": data["temperature"],
            "sleep_duration": data["sleep_duration"],
            "steps": data["steps"],
            "calories": data["calories"],
            "stress_level": data["stress_level"],
            "risk_score": risk_score,
            "risk_level": risk_level,
            "anomaly": anomaly,
            "anomaly_reason": anomaly_reason,
            "source": "manual",
            "selected_doctor": selected_doctor
        }
        
        add_health_record(user_id, record_dict)
        history_records = get_user_records(user_id)
        
        history_df = pd.DataFrame(history_records)
        history_df = history_df.rename(columns={
            "heart_rate": "HeartRate",
            "steps": "Steps",
            "spo2": "SpO2",
            "temperature": "Temperature",
            "sleep_duration": "SleepDuration",
            "stress_level": "StressLevel",
            "systolic_bp": "SystolicBP",
            "diastolic_bp": "DiastolicBP",
            "calories": "CaloriesBurned"
        })
        
        _, final_anomaly_stats = detect_anomalies(history_df)
        sanitized_records = sanitize_data(history_records)
        manual_logs = ["Manual vitals entry added to medical log."]
        update_user_cleaning_logs(user_id, manual_logs)
        report_data = sanitize_data(generate_report(sanitized_records, final_anomaly_stats, manual_logs))
        
        session_id = str(uuid.uuid4())
        SESSIONS_CACHE[session_id] = {
            "filename": "Manual Vitals Log",
            "report": report_data,
            "records": sanitized_records
        }
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "report": report_data,
            "records": sanitized_records[-300:]
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/clear_data", methods=["POST"])
@login_required
def api_clear_data():
    data = request.json or {}
    patient_id = data.get("patient_id")
    if session.get("role") == "doctor" and patient_id:
        user_id = int(patient_id)
    else:
        user_id = session["user_id"]
        
    from utils.db import get_db
    conn = get_db()
    try:
        conn.execute("DELETE FROM health_records WHERE user_id = ?", (user_id,))
        conn.execute("UPDATE users SET cleaning_logs = '[]' WHERE id = ?", (user_id,))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/patients", methods=["GET"])
@login_required
def api_patients():
    if session.get("role") != "doctor":
        return jsonify({"error": "Unauthorized Access"}), 403
        
    patients = get_all_patients()
    patient_list = []
    
    for p in patients:
        recs = get_user_records(p["id"])
        latest_risk = "N/A"
        latest_time = "N/A"
        if recs:
            latest_risk = recs[-1].get("risk_level", "Low")
            latest_time = recs[-1].get("timestamp", "")
            
        patient_list.append({
            "id": p["id"],
            "username": p["username"],
            "age": p["age"],
            "gender": p["gender"],
            "purpose": p["purpose"],
            "records_count": len(recs),
            "latest_risk": latest_risk,
            "latest_time": latest_time
        })
        
    return jsonify(sanitize_data(patient_list))

@app.route("/api/login_history", methods=["GET"])
@login_required
def api_login_history():
    if session.get("role") != "doctor":
        return jsonify({"error": "Unauthorized Access"}), 403
        
    history = get_recent_logins()
    filtered_logins = []
    seen_logins = set()
    
    for r in history:
        # Exclude doctor accounts
        if r.get("role") == "doctor" or r["username"].startswith("Dr. "):
            continue
            
        # Parse date to de-duplicate multiple logins on the same day
        date_str = r["login_time"].split(" ")[0] if " " in r["login_time"] else r["login_time"]
        key = (r["username"], date_str)
        if key in seen_logins:
            continue
            
        seen_logins.add(key)
        filtered_logins.append(r)
        
    return jsonify({
        "logins": sanitize_data(filtered_logins)
    })

@app.route("/api/ml_comparison", methods=["GET"])
@login_required
def api_ml_comparison():
    patient_id = request.args.get("patient_id")
    if session.get("role") == "doctor" and patient_id:
        user_id = int(patient_id)
    else:
        user_id = session["user_id"]
        
    records = get_user_records(user_id)
    results = compare_models(records)
    return jsonify(sanitize_data(results))

# ── AI CLINICAL CHAT ASSISTANT ────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    data = request.json or {}
    message = data.get("message", "").lower()
    patient_id = data.get("patient_id")
    
    if session.get("role") == "doctor" and patient_id:
        user_id = int(patient_id)
    else:
        user_id = session["user_id"]
        
    records = get_user_records(user_id)
    
    if not records:
        return jsonify({"reply": "I don't have any health logs to query. Please enter vitals manually or upload a CSV file!"})
        
    latest = records[-1]
    
    if "risk" in message or "anomaly" in message or "why" in message:
        score = latest.get("risk_score", 0)
        level = latest.get("risk_level", "Low")
        reason = latest.get("anomaly_reason", "Normal Vitals")
        if level == "Low":
            reply = f"The latest vital diagnostics indicate a <b>Low Risk Profile</b> ({score:.0f}/100). All parameters look normal!"
        else:
            reply = f"The latest assessment indicates a <b>{level} Risk Profile</b> ({score:.0f}/100). This was flagged due to: <i>{reason}</i>."
            
    elif "sleep" in message:
        avg_sleep = sum(r.get("sleep_duration", 8.0) for r in records) / len(records)
        latest_sleep = latest.get("sleep_duration", 8.0)
        reply = f"The average sleep duration across records is <b>{avg_sleep:.1f} hours</b>. In the latest log, it was <b>{latest_sleep:.1f} hours</b>. Doctors recommend 7-9 hours of deep sleep."
        
    elif "heart" in message or "hr" in message or "pulse" in message:
        avg_hr = sum(r.get("heart_rate", 72.0) for r in records) / len(records)
        latest_hr = latest.get("heart_rate", 72.0)
        reply = f"The average resting heart rate is <b>{avg_hr:.1f} bpm</b>. The latest reading is <b>{latest_hr:.0f} bpm</b> (Normal target range: 60-100 bpm)."
        
    elif "oxygen" in message or "spo2" in message:
        avg_spo2 = sum(r.get("spo2", 98.0) for r in records) / len(records)
        latest_spo2 = latest.get("spo2", 98.0)
        reply = f"The average oxygen saturation is <b>{avg_spo2:.1f}%</b>. The latest reading is <b>{latest_spo2:.1f}%</b>. Anything below 95% warrants monitoring, and below 90% is considered low."
        
    elif "stress" in message:
        avg_stress = sum(r.get("stress_level", 3.0) for r in records) / len(records)
        latest_stress = latest.get("stress_level", 3.0)
        reply = f"The average stress level score is <b>{avg_stress:.1f} / 10</b>. In the latest log, it was recorded at <b>{latest_stress:.0f} / 10</b>."
        
    elif "steps" in message or "activity" in message:
        avg_steps = sum(r.get("steps", 5000.0) for r in records) / len(records)
        reply = f"The average physical activity level is <b>{avg_steps:.0f} steps/day</b>. Active targets of 7,500+ steps are associated with excellent cardiovascular health."
        
    else:
        reply = "I understand you are asking about patient vitals. You can ask me about: <b>heart rate</b>, <b>sleep</b>, <b>oxygen saturation (SpO2)</b>, <b>stress level</b>, or <b>risk score</b>."
        
    return jsonify({"reply": reply})

@app.route("/api/report/<session_id>/pdf", methods=["GET"])
@login_required
def api_download_pdf(session_id):
    session_data = SESSIONS_CACHE.get(session_id)
    if not session_data:
        # Fallback database reload if cache was cleared/restarted
        patient_id = request.args.get("patient_id")
        if session.get("role") == "doctor" and patient_id:
            user_id = int(patient_id)
        else:
            user_id = session.get("user_id")
            
        if not user_id:
            return jsonify({"error": "Unauthorized session context"}), 401
            
        records = get_user_records(user_id)
        if not records:
            return jsonify({"error": "No diagnostics logs found in database"}), 404
            
        # Re-compile report
        history_df = pd.DataFrame(records)
        history_df = history_df.rename(columns={
            "heart_rate": "HeartRate",
            "steps": "Steps",
            "spo2": "SpO2",
            "temperature": "Temperature",
            "sleep_duration": "SleepDuration",
            "stress_level": "StressLevel",
            "systolic_bp": "SystolicBP",
            "diastolic_bp": "DiastolicBP",
            "calories": "CaloriesBurned"
        })
        
        _, final_anomaly_stats = detect_anomalies(history_df)
        sanitized_records = sanitize_data(records)
        report_data = sanitize_data(generate_report(sanitized_records, final_anomaly_stats, ["Restored clinical session for PDF generation."]))
        
        session_data = {
            "filename": "Database Patient Log",
            "report": report_data,
            "records": sanitized_records
        }
        SESSIONS_CACHE[session_id] = session_data

    try:
        report_data = session_data["report"]
        filename = session_data["filename"]
        
        pdf_path = generate_pdf_report(report_data, filename, session_data.get("records", []))
        
        download_name = f"strataform_report_{session_id[:8]}.pdf"
        if pdf_path.endswith(".txt"):
            download_name = f"strataform_report_{session_id[:8]}.txt"
            
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=download_name
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate report file: {str(e)}"}), 500

@app.route("/api/profile_info", methods=["GET"])
def api_profile_info():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized Access"}), 401
        
    user_id = session.get("user_id")
    conn = get_db()
    try:
        user = conn.execute("SELECT username, age, gender, purpose, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({
            "username": user["username"],
            "age": user["age"],
            "gender": user["gender"],
            "purpose": user["purpose"],
            "role": user["role"]
        })
    except Exception as e:
        print("Fetch profile error:", e)
        return jsonify({"error": "Database error fetching profile"}), 500
    finally:
        conn.close()

@app.route("/api/update_profile", methods=["POST"])
def api_update_profile():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized Access"}), 401
        
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    age_raw = data.get("age")
    gender = data.get("gender")
    purpose = data.get("purpose")
    
    if not username:
        return jsonify({"error": "Username cannot be empty"}), 400
        
    try:
        age = int(age_raw) if age_raw is not None else 30
    except (ValueError, TypeError):
        age = 30
        
    user_id = session.get("user_id")
    conn = get_db()
    try:
        exists = conn.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id)).fetchone()
        if exists:
            return jsonify({"error": "Username is already taken"}), 400
            
        conn.execute("""
            UPDATE users 
            SET username = ?, age = ?, gender = ?, purpose = ?
            WHERE id = ?
        """, (username, age, gender, purpose, user_id))
        conn.commit()
        
        session["username"] = username
        
        return jsonify({"success": True, "username": username})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Database error updating profile: {str(e)}"}), 500
    finally:
        conn.close()

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            return render_template("forgot_password.html", error="Email is required.")
            
        token = generate_and_save_reset_token(email)
        if token:
            reset_link = url_for("reset_password", token=token, _external=True)
            import threading
            threading.Thread(target=send_reset_email, args=(email, reset_link), daemon=True).start()
            return render_template("forgot_password.html", success="A reset link has been successfully sent to your email.")
        else:
            return render_template("forgot_password.html", error="Email address not registered in our clinical system.")
            
    return render_template("forgot_password.html")

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    token = request.args.get("token") or request.form.get("token")
    if not token:
        return redirect(url_for("login"))
        
    from datetime import datetime
    conn = get_db()
    user = conn.execute("SELECT id, reset_token_expiry FROM users WHERE reset_token = ?", (token,)).fetchone()
    conn.close()
    
    if not user or user["reset_token_expiry"] < datetime.now().isoformat():
        return render_template("reset_password.html", error="The reset link is invalid or has expired.", show_form=False)
        
    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        if not password or len(password) < 6:
            return render_template("reset_password.html", token=token, error="Password must be at least 6 characters.", show_form=True)
            
        if password != confirm_password:
            return render_template("reset_password.html", token=token, error="Passwords do not match.", show_form=True)
            
        success, msg = reset_user_password_by_token(token, password)
        if success:
            return render_template("reset_password.html", success=msg, show_form=False)
        else:
            return render_template("reset_password.html", token=token, error=msg, show_form=True)
            
    return render_template("reset_password.html", token=token, show_form=True)

def send_reset_email(to_email, reset_link):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    sender_email = "postmanmail21@gmail.com"
    sender_password = "wecw dxpw xsjo upgt"
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Strataform Password Reset Request"
    msg["From"] = f"Strataform Care Team <{sender_email}>"
    msg["To"] = to_email
    
    text = f"""
Hello,

You requested a password reset for your Strataform Clinical Labs account.
Please click the link below to reset your password. This link is valid for 1 hour.

{reset_link}

If you did not request this, please ignore this email.

Best regards,
Strataform Clinic Team
"""
    html = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eeeeee; border-radius: 10px;">
    <h2 style="color: #ea580c; border-bottom: 2px solid #ea580c; padding-bottom: 10px; font-family: 'Outfit', sans-serif;">Strataform Vitals Portal</h2>
    <p>Hello,</p>
    <p>You requested a password reset for your Strataform Clinical Labs account.</p>
    <p>Please click the button below to choose a new password. This reset link is valid for 1 hour.</p>
    <div style="margin: 25px 0; text-align: center;">
      <a href="{reset_link}" style="background: linear-gradient(135deg, #f97316, #ea580c); color: white; text-decoration: none; padding: 12px 30px; border-radius: 99px; font-weight: bold; display: inline-block; box-shadow: 0 4px 15px rgba(249, 115, 22, 0.2);">Reset Password</a>
    </div>
    <p>Or copy and paste this link in your browser:</p>
    <p style="background-color: #f8fafc; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 13px; word-break: break-all;"><a href="{reset_link}">{reset_link}</a></p>
    <p>If you did not request this, please ignore this email and your password will remain unchanged.</p>
    <br>
    <p style="border-top: 1px solid #eeeeee; padding-top: 15px; font-size: 12px; color: #666666;">
      Strataform Clinical Labs — Vitals & Anomaly Diagnostics<br>
      12/32 Nethaji Street, Kodambakkam, 600 024 | Phone: 044 2454 2454
    </p>
  </body>
</html>
"""
    
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10.0)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print(f"Reset email successfully sent to {to_email}")
        return True
    except Exception as e:
        print("Failed to send email:", e)
        return False

def generate_and_save_reset_token(email):
    import secrets
    from datetime import datetime, timedelta
    
    token = secrets.token_urlsafe(32)
    expiry = (datetime.now() + timedelta(hours=1)).isoformat()
    
    conn = get_db()
    try:
        user = conn.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email.lower().strip(),)).fetchone()
        if not user:
            return None
        
        conn.execute(
            "UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?",
            (token, expiry, user["id"])
        )
        conn.commit()
        return token
    except Exception as e:
        print("Error saving reset token:", e)
        return None
    finally:
        conn.close()

def reset_user_password_by_token(token, new_password):
    from datetime import datetime
    from werkzeug.security import generate_password_hash
    
    password_hash = generate_password_hash(new_password)
    now_str = datetime.now().isoformat()
    
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, reset_token_expiry FROM users WHERE reset_token = ?", 
            (token,)
        ).fetchone()
        
        if not user:
            return False, "Invalid or expired reset token."
            
        expiry_str = user["reset_token_expiry"]
        if expiry_str < now_str:
            return False, "The reset link has expired. Please request a new one."
            
        conn.execute(
            "UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expiry = NULL WHERE id = ?",
            (password_hash, user["id"])
        )
        conn.commit()
        return True, "Your password has been successfully reset."
    except Exception as e:
        print("Error resetting password:", e)
        return False, "Database error resetting password."
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, host="127.0.0.1", port=5000)



