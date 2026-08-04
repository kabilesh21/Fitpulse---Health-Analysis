import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(__file__))

from utils.db import init_db, get_db

print("Starting migration and database seeding...")
init_db()
print("Migration and doctor seeding completed successfully.")

print("Clearing patient user details, vital records, and login histories for a fresh start...")
conn = get_db()
try:
    cursor = conn.cursor()
    # Delete all health records
    cursor.execute("DELETE FROM health_records")
    print("Deleted all vitals from health_records.")
    
    # Delete all login histories
    cursor.execute("DELETE FROM login_history")
    print("Deleted all login history logs.")
    
    # Delete all users that are patients (keep only doctor users)
    cursor.execute("DELETE FROM users WHERE role = 'patient'")
    print("Deleted all patient users.")
    
    conn.commit()
    print("All patient details cleared successfully! System is ready for a fresh login.")
except Exception as e:
    print("Error clearing patient data:", e)
finally:
    conn.close()
