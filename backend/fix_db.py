from utils.db import get_db

conn = get_db()

# Remove default/test users and their health records
conn.execute("DELETE FROM health_records WHERE user_id IN (SELECT id FROM users WHERE username IN ('patient1', 'test_upload_user'))")
conn.execute("DELETE FROM users WHERE username IN ('patient1', 'test_upload_user')")

# Update Dr. D. Suganya's profession
conn.execute("UPDATE users SET purpose = 'Senior Neurology Consultant' WHERE username = 'Dr. D. Suganya'")

conn.commit()
conn.close()
print("Done: removed default users, updated Dr. Suganya's profession to Senior Neurology Consultant")

# Verify
conn2 = get_db()
suganya = conn2.execute("SELECT username, purpose FROM users WHERE username = 'Dr. D. Suganya'").fetchone()
remaining = conn2.execute("SELECT username, role FROM users ORDER BY role, username").fetchall()
conn2.close()

print("Suganya:", dict(suganya) if suganya else "NOT FOUND")
print("All users:")
for u in remaining:
    print(" -", dict(u))
