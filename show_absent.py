"""
Terminal mein absent students ki list dikhata hai (kuch badalta nahi, sirf padhta hai).

Use:
    python show_absent.py                 -> aaj ki date
    python show_absent.py 2026-11-02      -> kisi aur din ki date (YYYY-MM-DD)

Server chalu hona zaroori nahi. Ise project folder mein rakho (app.py ke saath).
"""
import csv
import os
import sqlite3
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "smart_attendance.db")
CSV_FILE = os.path.join(BASE_DIR, "attendance", "attendance.csv")

date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")

# Registered students
conn = sqlite3.connect(DB_FILE)
students = conn.execute(
    "SELECT student_id, name, parent_phone FROM students ORDER BY name"
).fetchall()
conn.close()

# Attendance rows for that date
present_ids = set()
if os.path.exists(CSV_FILE):
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row.get("Date") or "").strip() == date \
                    and (row.get("Status") or "").strip().lower() == "present":
                present_ids.add((row.get("Student ID") or "").strip())

absent = [s for s in students if s[0] not in present_ids]
present = [s for s in students if s[0] in present_ids]

print(f"\nDate: {date}")
print(f"Total students: {len(students)} | Present: {len(present)} | Absent: {len(absent)}\n")

if not students:
    print("No registered students found in the database.")
elif not absent:
    print("Everyone is present.")
else:
    print(f"{'No.':<5}{'Student ID':<14}{'Name':<24}{'Parent Mobile'}")
    print("-" * 62)
    for i, (sid, name, phone) in enumerate(absent, 1):
        print(f"{i:<5}{sid:<14}{name:<24}{phone or '-'}")
print()