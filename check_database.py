import sqlite3

conn = sqlite3.connect("logminer.db")
cursor = conn.cursor()

tables = [
    "log_files",
    "log_entries",
    "log_templates",
    "anomalies",
    "incidents",
    "reports"
]

print("DATABASE CHECK")
print("=" * 40)

print("\nTables found:")
cursor.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
)

for row in cursor.fetchall():
    print(" -", row[0])

print("\nRecord counts:")
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f" - {table}: {count}")

conn.close()

print("\nDatabase check completed.")