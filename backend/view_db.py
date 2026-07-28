import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "fitpulse.db")

if not os.path.exists(db_path):
    print("Database file does not exist yet. Please run the app and register first!")
    input("\nPress Enter to exit...")
    exit()

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

print("==========================================================")
print("             FITPULSE DATABASE VIEWER TOOL")
print("==========================================================\n")

print("--- REGISTERED PATIENTS ---")
try:
    users = conn.execute("SELECT id, username, age, gender FROM users").fetchall()
    if not users:
        print("No registered users found.")
    for u in users:
        print(f"User ID: {u['id']} | Username: {u['username']} | Age: {u['age']} | Gender: {u['gender']}")
except Exception as e:
    print("Could not read users table:", e)

print("\n--- RECORDED HEALTH VITALS LOGS ---")
try:
    records = conn.execute("SELECT id, user_id, timestamp, heart_rate, spo2, systolic_bp, diastolic_bp, risk_score, risk_level, anomaly, source FROM health_records").fetchall()
    if not records:
        print("No vitals records found.")
    for r in records:
        bp = f"{r['systolic_bp']:.0f}/{r['diastolic_bp']:.0f}"
        print(f"Log ID: {r['id']} | User ID: {r['user_id']} | Time: {r['timestamp']} | HR: {r['heart_rate']:.0f} bpm | BP: {bp} | SpO2: {r['spo2']:.0f}% | Risk: {r['risk_score']:.0f}/100 ({r['risk_level']}) | Anomaly: {r['anomaly']} | Source: {r['source']}")
except Exception as e:
    print("Could not read health_records table:", e)

conn.close()
print("\n==========================================================")
input("Press Enter to exit...")
