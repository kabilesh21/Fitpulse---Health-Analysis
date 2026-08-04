"""
utils/db.py
Database manager for FitPulse — handles SQLite connection, user accounts, and patient health history.
"""

import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fitpulse.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    
    # 1. Users Table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        age INTEGER DEFAULT 30,
        gender TEXT DEFAULT 'Male',
        role TEXT DEFAULT 'patient',
        purpose TEXT DEFAULT 'Routine Check'
    )
    """)
    
    # 2. Health Records Table (handles HeartRate, BP, SpO2, Temperature, Sleep, Steps, Calories, Stress, Selected Doctor)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS health_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        heart_rate REAL NOT NULL,
        systolic_bp REAL DEFAULT 120.0,
        diastolic_bp REAL DEFAULT 80.0,
        spo2 REAL DEFAULT 98.0,
        temperature REAL DEFAULT 36.6,
        sleep_duration REAL DEFAULT 8.0,
        steps REAL DEFAULT 5000.0,
        calories REAL DEFAULT 2000.0,
        stress_level REAL DEFAULT 3.0,
        risk_score REAL DEFAULT 0.0,
        risk_level TEXT DEFAULT 'Low',
        anomaly TEXT DEFAULT 'No',
        anomaly_reason TEXT DEFAULT '—',
        source TEXT NOT NULL, -- 'manual' or 'csv_upload'
        selected_doctor TEXT DEFAULT 'Dr. K. Albert'
    )
    """)
    
    # 3. Login History Table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS login_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        login_time TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    
    try:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'patient'")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN purpose TEXT DEFAULT 'Routine Check'")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN cleaning_logs TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE health_records ADD COLUMN selected_doctor TEXT DEFAULT 'Dr. K. Albert'")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN reset_token_expiry TEXT")
    except sqlite3.OperationalError:
        pass
    
    # Seed or update Dr. K. Albert and Dr. D. Suganya to ensure correct credentials
    cursor = conn.cursor()
    albert_hash = generate_password_hash("doctoralbert")
    suganya_hash = generate_password_hash("doctorsuganya")
    
    try:
        # Check Albert
        albert_exists = cursor.execute("SELECT id FROM users WHERE username = 'Dr. K. Albert'").fetchone()
        if albert_exists:
            cursor.execute("UPDATE users SET password_hash = ?, role = 'doctor', age = 45, gender = 'Male', purpose = 'Chief Cardiologist', email = 'albert@strataform.med' WHERE username = 'Dr. K. Albert'", (albert_hash,))
        else:
            cursor.execute("INSERT INTO users (username, email, password_hash, age, gender, role, purpose) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           ("Dr. K. Albert", "albert@strataform.med", albert_hash, 45, "Male", "doctor", "Chief Cardiologist"))
                           
        # Check Suganya
        suganya_exists = cursor.execute("SELECT id FROM users WHERE username = 'Dr. D. Suganya'").fetchone()
        if suganya_exists:
            cursor.execute("UPDATE users SET password_hash = ?, role = 'doctor', age = 42, gender = 'Female', purpose = 'Senior Neurology Consultant', email = 'suganya@strataform.med' WHERE username = 'Dr. D. Suganya'", (suganya_hash,))
        else:
            cursor.execute("INSERT INTO users (username, email, password_hash, age, gender, role, purpose) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           ("Dr. D. Suganya", "suganya@strataform.med", suganya_hash, 42, "Female", "doctor", "Senior Neurology Consultant"))
    except Exception as e:
        print("Seeding failed:", e)

    conn.commit()
    conn.close()

def register_user(username, email, password, age=30, gender="Male", role="patient", purpose="Routine Check"):
    conn = get_db()
    password_hash = generate_password_hash(password)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, age, gender, role, purpose) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username.strip(), email.strip().lower() if email else None, password_hash, age, gender, role, purpose)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def verify_user(username_or_email, password):
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR LOWER(email) = ?", 
            (username_or_email.strip(), username_or_email.strip().lower())
        ).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            return dict(user)
        return None
    finally:
        conn.close()

def get_user_by_id(user_id):
    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def add_health_record(user_id, record_dict):
    conn = get_db()
    try:
        cursor = conn.cursor()
        timestamp = record_dict.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        cursor.execute("""
            INSERT INTO health_records (
                user_id, timestamp, heart_rate, systolic_bp, diastolic_bp, 
                spo2, temperature, sleep_duration, steps, calories, 
                stress_level, risk_score, risk_level, anomaly, anomaly_reason, source, selected_doctor
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            timestamp,
            record_dict["heart_rate"],
            record_dict.get("systolic_bp", 120.0),
            record_dict.get("diastolic_bp", 80.0),
            record_dict.get("spo2", 98.0),
            record_dict.get("temperature", 36.6),
            record_dict.get("sleep_duration", 8.0),
            record_dict.get("steps", 5000.0),
            record_dict.get("calories", 2000.0),
            record_dict.get("stress_level", 3.0),
            record_dict.get("risk_score", 0.0),
            record_dict.get("risk_level", "Low"),
            record_dict.get("anomaly", "No"),
            record_dict.get("anomaly_reason", "—"),
            record_dict.get("source", "manual"),
            record_dict.get("selected_doctor", "Dr. K. Albert")
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_user_records(user_id, limit=500):
    conn = get_db()
    try:
        records = conn.execute(
            "SELECT * FROM health_records WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in reversed(records)]  # chronological order for charts
    finally:
        conn.close()

def get_anomaly_history(user_id):
    conn = get_db()
    try:
        records = conn.execute(
            "SELECT * FROM health_records WHERE user_id = ? AND anomaly = 'Yes' ORDER BY timestamp DESC",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in records]
    finally:
        conn.close()

def get_all_patients():
    conn = get_db()
    try:
        patients = conn.execute(
            "SELECT id, username, age, gender, purpose, role FROM users WHERE role = 'patient' ORDER BY username ASC"
        ).fetchall()
        return [dict(p) for p in patients]
    finally:
        conn.close()

def update_user_cleaning_logs(user_id, logs: list):
    import json
    conn = get_db()
    try:
        conn.execute("UPDATE users SET cleaning_logs = ? WHERE id = ?", (json.dumps(logs), user_id))
        conn.commit()
    except Exception as e:
        print("Failed to save cleaning logs:", e)
    finally:
        conn.close()

def get_user_cleaning_logs(user_id) -> list:
    import json
    conn = get_db()
    try:
        user = conn.execute("SELECT cleaning_logs FROM users WHERE id = ?", (user_id,)).fetchone()
        if user and user["cleaning_logs"]:
            try:
                return json.loads(user["cleaning_logs"])
            except Exception:
                return []
        return []
    except Exception:
        return []
    finally:
        conn.close()

def record_login(user_id):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO login_history (user_id, login_time) VALUES (?, ?)",
            (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    except Exception as e:
        print("Failed to record login time:", e)
    finally:
        conn.close()

def get_recent_logins():
    conn = get_db()
    try:
        records = conn.execute("""
            SELECT lh.login_time, u.username, u.purpose, u.age, u.gender, u.role
            FROM login_history lh
            JOIN users u ON lh.user_id = u.id
            ORDER BY lh.login_time DESC
        """).fetchall()
        return [dict(r) for r in records]
    except Exception as e:
        print("Failed to fetch login history:", e)
        return []
    finally:
        conn.close()
