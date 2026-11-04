from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from functools import wraps
from database import (
    verify_admin, create_tables, create_student, verify_student,
    change_password, get_student, get_all_students
)

from werkzeug.utils import secure_filename

from deepface import DeepFace

from datetime import datetime

import os

import base64

import cv2

import numpy as np

import csv
import re
import secrets
import sqlite3
from urllib.parse import quote

from sms_service import send_sms



app = Flask(__name__)
# For deployment, set FLASK_SECRET_KEY to a long random value in the environment.
# This local fallback resets sessions whenever the server restarts.
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

# Ensure student/admin tables exist before handling requests.
create_tables()



# --------------------------------------------------

# PATHS

# --------------------------------------------------



BASE_DIR = os.path.dirname(os.path.abspath(__file__))



DATASET_PATH = os.path.join(BASE_DIR, "dataset")

ATTENDANCE_FOLDER = os.path.join(BASE_DIR, "attendance")

ATTENDANCE_FILE = os.path.join(ATTENDANCE_FOLDER, "attendance.csv")



os.makedirs(DATASET_PATH, exist_ok=True)

os.makedirs(ATTENDANCE_FOLDER, exist_ok=True)



print("Attendance file is saved at:", ATTENDANCE_FILE)

CSV_HEADERS = ["Student ID", "Name", "Date", "Time", "Status"]

TOTAL_IMAGES = 7





# --------------------------------------------------

# CSV SETUP

# --------------------------------------------------



def ensure_attendance_file():

    if not os.path.exists(ATTENDANCE_FILE):

        with open(ATTENDANCE_FILE, "w", newline="", encoding="utf-8") as file:

            writer = csv.writer(file)

            writer.writerow(CSV_HEADERS)





def read_attendance_records():

    ensure_attendance_file()



    with open(ATTENDANCE_FILE, "r", newline="", encoding="utf-8") as file:

        reader = csv.DictReader(file)

        return list(reader)





ensure_attendance_file()





# --------------------------------------------------

# STUDENT HELPERS

# --------------------------------------------------



def get_student_folders():

    """Return dataset folders containing at least one JPG image."""

    students = []



    for folder_name in os.listdir(DATASET_PATH):

        folder_path = os.path.join(DATASET_PATH, folder_name)



        if not os.path.isdir(folder_path):

            continue



        images = [

            file_name for file_name in os.listdir(folder_path)

            if file_name.lower().endswith((".jpg", ".jpeg", ".png"))

        ]



        if images:

            students.append(folder_name)



    return students





def get_student_details(folder_name):

    """

    Web registration uses Name_StudentID folder names.

    Split from the right so names containing underscores can work.

    """

    parts = folder_name.rsplit("_", 1)



    if len(parts) == 2:

        return parts[0], parts[1]



    return folder_name, "Unknown"





def get_dashboard_stats():

    records = read_attendance_records()

    today = datetime.now().strftime("%Y-%m-%d")



    student_folders = get_student_folders()

    total_students = len(student_folders)



    # Count unique registered student IDs marked present today.

    present_ids = {

        record.get("Student ID", "").strip()

        for record in records

        if record.get("Date") == today

        and record.get("Status", "").strip().lower() == "present"

        and record.get("Student ID", "").strip()

    }



    present_today = len(present_ids)

    absent_today = max(total_students - present_today, 0)



    attendance_rate = (

        round((present_today / total_students) * 100)

        if total_students > 0

        else 0

    )



    return {

        "total_students": total_students,

        "present_today": present_today,

        "absent_today": absent_today,

        "attendance_rate": attendance_rate,

    }





# --------------------------------------------------
# ADMIN AUTHENTICATION
# --------------------------------------------------

def admin_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_username"):
            return redirect(url_for("admin_login"))
        return view_function(*args, **kwargs)
    return wrapped_view


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_username"):
        return redirect(url_for("home"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if verify_admin(username, password):
            session.clear()
            session["admin_username"] = username
            return redirect(url_for("home"))
        error = "Invalid username or password. Please try again."

    return render_template("admin_login.html", error=error)


@app.route("/admin-logout", methods=["POST"])
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# --------------------------------------------------

# HOME / DASHBOARD

# --------------------------------------------------



@app.route("/")

@admin_required
def home():

    stats = get_dashboard_stats()



    return render_template(

        "index.html",

        **stats,

        today_date=datetime.now().strftime("%d %B %Y")

    )





# --------------------------------------------------

# STUDENT REGISTRATION PAGE

# --------------------------------------------------



@app.route("/register")

@admin_required
def register():

    return render_template("register.html")





# --------------------------------------------------

# SAVE STUDENT FACE IMAGES

# --------------------------------------------------



@app.route("/save_face", methods=["POST"])

@admin_required
def save_face():

    try:

        data = request.get_json(silent=True) or {}



        student_id = str(data.get("studentId", "")).strip()

        student_name = str(data.get("studentName", "")).strip()

        image_data = data.get("image", "")
        parent_phone = str(data.get("parentPhone", "")).strip()



        if not student_id or not student_name or not image_data:

            return jsonify({

                "success": False,

                "message": "Student ID, name and image are required."

            }), 400



        if not re.fullmatch(r"[6-9]\d{9}", parent_phone):
            return jsonify({
                "success": False,
                "message": "Enter a valid 10-digit Indian mobile number."
            }), 400

        # Prevent folder paths from being supplied as student details.

        safe_id = secure_filename(student_id)

        safe_name = secure_filename(student_name)



        if not safe_id or not safe_name:

            return jsonify({

                "success": False,

                "message": "Please enter a valid student ID and name."

            }), 400



        folder_name = f"{safe_name}_{safe_id}"

        student_folder = os.path.join(DATASET_PATH, folder_name)

        os.makedirs(student_folder, exist_ok=True)



        # Accept either a raw base64 string or a data URL.

        if "," in image_data:

            image_data = image_data.split(",", 1)[1]



        image_bytes = base64.b64decode(image_data, validate=True)

        image_array = np.frombuffer(image_bytes, dtype=np.uint8)

        frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)



        if frame is None:

            return jsonify({

                "success": False,

                "message": "Could not read the captured image. Please try again."

            }), 400



        existing_images = [

            name for name in os.listdir(student_folder)

            if name.lower().endswith((".jpg", ".jpeg", ".png"))

        ]



        image_number = len(existing_images) + 1

        image_path = os.path.join(

            student_folder,

            f"{safe_name}_{image_number}.jpg"

        )



        if not cv2.imwrite(image_path, frame):

            return jsonify({

                "success": False,

                "message": "Could not save the image."

            }), 500



        temporary_password = None
        account_created = False

        if image_number >= TOTAL_IMAGES and not get_student(student_id):
            temporary_password = secrets.token_urlsafe(6)
            create_student(
                student_id,
                student_name,
                temporary_password,
                parent_phone
            )
            account_created = True

        return jsonify({
            "success": True,
            "message": f"Face image saved successfully ({image_number}).",

            "count": image_number,
            "temporary_password": temporary_password,
            "account_created": account_created

        })



    except sqlite3.IntegrityError:
        return jsonify({
            "success": False,
            "message": "A student account with this ID already exists."
        }), 400

    except (ValueError, base64.binascii.Error):

        return jsonify({

            "success": False,

            "message": "Invalid image data. Please capture the image again."

        }), 400



    except Exception as error:

        app.logger.exception("Error saving face image")

        return jsonify({

            "success": False,

            "message": "Could not save the face image. Check the server terminal."

        }), 500





# --------------------------------------------------

# ATTENDANCE PAGE

# --------------------------------------------------



@app.route("/mark-attendance")

@admin_required
def mark_attendance_page():

    return render_template("mark_attendance.html")





# --------------------------------------------------

# RECOGNIZE FACE AND MARK ATTENDANCE

# --------------------------------------------------



@app.route("/recognize_face", methods=["POST"])

@admin_required
def recognize_face():

    try:

        data = request.get_json(silent=True) or {}

        image_data = data.get("image", "")



        if not image_data:

            return jsonify({

                "success": False,

                "message": "No image received. Start the camera and try again."

            }), 400



        if "," in image_data:

            image_data = image_data.split(",", 1)[1]



        image_bytes = base64.b64decode(image_data, validate=True)

        image_array = np.frombuffer(image_bytes, dtype=np.uint8)

        frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)



        if frame is None:

            return jsonify({

                "success": False,

                "message": "Could not read the camera image."

            }), 400



        student_folders = get_student_folders()



        if not student_folders:

            return jsonify({

                "success": False,

                "message": "No registered face images found. Register a student first."

            })



        results = DeepFace.find(

            img_path=frame,

            db_path=DATASET_PATH,

            model_name="VGG-Face",

            detector_backend="opencv",

            enforce_detection=False,

            silent=True

        )



        if results is None:

            return jsonify({

                "success": False,

                "message": "No matching student found."

            })



        # DeepFace.find normally returns a list of DataFrames.

        result_df = results[0] if isinstance(results, list) and results else results



        if result_df is None or result_df.empty:

            return jsonify({

                "success": False,

                "message": "No matching student found."

            })



        identity_path = str(result_df.iloc[0].get("identity", ""))



        if not identity_path:

            return jsonify({

                "success": False,

                "message": "Could not identify the student."

            })



        student_folder = os.path.basename(os.path.dirname(identity_path))



        # Only accept identities from registered dataset folders.

        if student_folder not in student_folders:

            return jsonify({

                "success": False,

                "message": "The recognized identity is not registered."

            })



        student_name, student_id = get_student_details(student_folder)



        if student_id == "Unknown":

            return jsonify({

                "success": False,

                "message": "Student folder name is invalid. Please check the dataset."

            })



        now = datetime.now()

        today = now.strftime("%Y-%m-%d")

        current_time = now.strftime("%H:%M:%S")



        records = read_attendance_records()



        already_marked = any(

            record.get("Student ID", "").strip() == student_id

            and record.get("Date", "").strip() == today

            and record.get("Status", "").strip().lower() == "present"

            for record in records

        )



        if already_marked:

            return jsonify({

                "success": True,

                "message": f"Attendance already marked today for {student_name}.",

                "student_name": student_name,

                "student_id": student_id,

                "already_marked": True

            })



        with open(ATTENDANCE_FILE, "a", newline="", encoding="utf-8") as file:

            writer = csv.writer(file)

            writer.writerow([

                student_id,

                student_name,

                today,

                current_time,

                "Present"

            ])



        return jsonify({

            "success": True,

            "message": f"Attendance marked successfully for {student_name}.",

            "student_name": student_name,

            "student_id": student_id,

            "already_marked": False

        })



    except Exception:

        app.logger.exception("Face recognition or attendance marking failed")

        return jsonify({

            "success": False,

            "message": "Recognition failed. Check the VS Code terminal for details."

        }), 500





# --------------------------------------------------
# MARK ABSENT + SEND SMS TO PARENTS
# --------------------------------------------------

@app.route("/mark-absent", methods=["POST"])
@admin_required
def mark_absent():
    """Mark registered students who are not present today as Absent
    and SMS their parents. Running twice in a day creates no duplicates."""
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M:%S")
    records = read_attendance_records()

    already_today = {
        record.get("Student ID", "").strip()
        for record in records
        if record.get("Date", "").strip() == today
    }

    marked = 0
    sms_sent = 0
    sms_failed = 0

    for student in get_all_students():
        student_id = student["student_id"]

        if student_id in already_today:
            continue

        with open(ATTENDANCE_FILE, "a", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(
                [student_id, student["name"], today, now_time, "Absent"]
            )
        marked += 1

        message = (
            f"Dear Parent, your ward {student['name']} "
            f"(ID: {student_id}) was marked ABSENT on {today}. - SmartAttend"
        )
        ok, _info = send_sms(student.get("parent_phone"), message)
        if ok:
            sms_sent += 1
        else:
            sms_failed += 1

    return jsonify({
        "success": True,
        "marked_absent": marked,
        "sms_sent": sms_sent,
        "sms_failed": sms_failed
    })


# --------------------------------------------------
# NOTIFY PARENT ON WHATSAPP (no API needed)
# --------------------------------------------------

@app.route("/notify-parent/<student_id>")
@admin_required
def notify_parent(student_id):
    student = get_student(student_id)

    if not student:
        return "Student not found.", 404

    phone = str(student.get("parent_phone") or "").strip()

    if not (phone.isdigit() and len(phone) == 10):
        return "Parent mobile number is missing or invalid for this student.", 404

    date = request.args.get("date", "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        date = datetime.now().strftime("%Y-%m-%d")

    message = (
        f"Dear Parent, your ward {student['name']} "
        f"(ID: {student_id}) was marked ABSENT on {date}. - SmartAttend"
    )

    return redirect(f"https://wa.me/91{phone}?text={quote(message)}")


# --------------------------------------------------
# DOWNLOAD ATTENDANCE CSV
# --------------------------------------------------

@app.route("/download-attendance")
@admin_required
def download_attendance():
    ensure_attendance_file()
    return send_file(
        ATTENDANCE_FILE,
        as_attachment=True,
        download_name="attendance.csv"
    )


# --------------------------------------------------

# VIEW ATTENDANCE RECORDS

# --------------------------------------------------



@app.route("/attendance")

@admin_required
def view_attendance():

    records = read_attendance_records()

    return render_template("attendance.html", records=records)






# --------------------------------------------------
# STUDENT LOGIN, PASSWORD CHANGE AND DASHBOARD
# --------------------------------------------------

def student_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not session.get("student_id"):
            return redirect(url_for("student_login"))
        return view_function(*args, **kwargs)
    return wrapped_view


@app.route("/student-login", methods=["GET", "POST"])
def student_login():
    if session.get("student_id"):
        return redirect(url_for("student_dashboard"))

    error = None
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        password = request.form.get("password", "")
        student = verify_student(student_id, password)
        if student:
            session.clear()
            session["student_id"] = student["student_id"]
            if student.get("must_change_password", 1):
                return redirect(url_for("student_change_password"))
            return redirect(url_for("student_dashboard"))
        error = "Invalid student ID or password."

    return render_template("student_login.html", error=error)


@app.route("/student-change-password", methods=["GET", "POST"])
@student_required
def student_change_password():
    error = None
    if request.method == "POST":
        password = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < 8:
            error = "Password must contain at least 8 characters."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            change_password(session["student_id"], password)
            return redirect(url_for("student_dashboard"))
    return render_template("student_change_password.html", error=error)


@app.route("/student-dashboard")
@student_required
def student_dashboard():
    student_id = session["student_id"]
    student = get_student(student_id)
    if not student:
        session.clear()
        return redirect(url_for("student_login"))

    history = [
        row for row in read_attendance_records()
        if row.get("Student ID", "").strip() == student_id
    ]
    present = sum(1 for row in history if row.get("Status", "").strip().lower() == "present")
    absent = sum(1 for row in history if row.get("Status", "").strip().lower() == "absent")
    total_classes = len(history)
    percentage = round((present / total_classes) * 100, 2) if total_classes else 0

    return render_template(
        "student_dashboard.html",
        name=student["name"],
        student_id=student_id,
        today_date=datetime.now().strftime("%d %B %Y"),
        total_classes=total_classes,
        present=present,
        absent=absent,
        percentage=percentage,
        history=history
    )


@app.route("/student-logout", methods=["POST"])
def student_logout():
    if session.get("student_id"):
        session.clear()
    return redirect(url_for("student_login"))


# --------------------------------------------------

# RUN APP

# --------------------------------------------------



if __name__ == "__main__":

    app.run(debug=True)