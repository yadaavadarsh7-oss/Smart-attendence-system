"""
Kisi ek student ko poora saaf karta hai (account + face images) taaki
use dobara register kiya ja sake. Attendance records ko nahi chhuta.

Use:  python reset_student.py
"""
import os
import shutil
import sqlite3

from database import DATABASE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "dataset")

student_id = input("Student ID to reset: ").strip()

if not student_id:
    raise SystemExit("Student ID is required.")

# 1) Delete the account from the database
conn = sqlite3.connect(DATABASE)
cursor = conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
conn.commit()
conn.close()
print("Account deleted." if cursor.rowcount else "No account found for this ID.")

# 2) Delete dataset folders named Name_<StudentID>
removed = 0
if os.path.isdir(DATASET_PATH):
    for folder in os.listdir(DATASET_PATH):
        path = os.path.join(DATASET_PATH, folder)
        if os.path.isdir(path) and folder.endswith("_" + student_id):
            shutil.rmtree(path)
            removed += 1
            print("Deleted folder:", folder)

if not removed:
    print("No face-image folder found for this ID.")

print("Done. Now register the student again from /register.")