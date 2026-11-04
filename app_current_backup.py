from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from functools import wraps
from database import verify_admin
from werkzeug.utils import secure_filename
from deepface import DeepFace
from datetime import datetime
import os
import base64
import cv2
import numpy as np
import csv

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "dataset")
ATTENDANCE_FOLDER = os.path.join(BASE_DIR, "attendance")
ATTENDANCE_FILE = os.path.join(ATTENDANCE_FOLDER, "attendance.csv")
os.makedirs(DATASET_PATH, exist_ok=True)
os.makedirs(ATTENDANCE_FOLDER, exist_ok=True)
CSV_HEADERS = ["Student ID", "Name", "Date", "Time", "Status"]


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_username"):
            if request.path.startswith(("/save_face", "/recognize_face")):
                return jsonify({"success": False, "message": "Admin login required."}), 401
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


def ensure_attendance_file():
    if not os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "w", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(CSV_HEADERS)


def read_attendance_records():
    ensure_attendance_file()
    with open(ATTENDANCE_FILE, "r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))

ensure_attendance_file()


def get_student_folders():
    students = []
    for folder_name in os.listdir(DATASET_PATH):
        folder_path = os.path.join(DATASET_PATH, folder_name)
        if not os.path.isdir(folder_path):
            continue
        images = [name for name in os.listdir(folder_path)
                  if name.lower().endswith((".jpg", ".jpeg", ".png"))]
        if images:
            students.append(folder_name)
    return students


def get_student_details(folder_name):
    parts = folder_name.rsplit("_", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return folder_name, "Unknown"


def get_dashboard_stats():
    records = read_attendance_records()
    today = datetime.now().strftime("%Y-%m-%d")
    total_students = len(get_student_folders())
    present_ids = {
        record.get("Student ID", "").strip()
        for record in records
        if record.get("Date") == today
        and record.get("Status", "").strip().lower() == "present"
        and record.get("Student ID", "").strip()
    }
    present_today = len(present_ids)
    absent_today = max(total_students - present_today, 0)
    attendance_rate = round((present_today / total_students) * 100) if total_students else 0
    return {
        "total_students": total_students,
        "present_today": present_today,
        "absent_today": absent_today,
        "attendance_rate": attendance_rate,
    }


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_username"):
        return redirect(url_for("home"))