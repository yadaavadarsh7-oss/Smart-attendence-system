import cv2
import os
import csv
from datetime import datetime
from deepface import DeepFace

DATASET_PATH = "dataset"
ATTENDANCE_FOLDER = "attendance"
ATTENDANCE_FILE = os.path.join(
    ATTENDANCE_FOLDER,
    "attendance.csv"
)

os.makedirs(ATTENDANCE_FOLDER, exist_ok=True)

# Create attendance file if it doesn't exist
if not os.path.exists(ATTENDANCE_FILE):
    with open(ATTENDANCE_FILE, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Student ID",
            "Name",
            "Date",
            "Time",
            "Status"
        ])


def mark_attendance(student_folder):
    parts = student_folder.split("_", 1)

    student_id = parts[0]
    name = parts[1] if len(parts) > 1 else "Unknown"

    today = datetime.now().strftime("%Y-%m-%d")

    # Check whether attendance is already marked today
    with open(ATTENDANCE_FILE, "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if (
                row["Student ID"] == student_id
                and row["Date"] == today
            ):
                return False

    now = datetime.now()

    with open(ATTENDANCE_FILE, "a", newline="") as file:
        writer = csv.writer(file)

        writer.writerow([
            student_id,
            name,
            today,
            now.strftime("%H:%M:%S"),
            "Present"
        ])

    print(f"Attendance marked: {student_id} - {name}")
    return True


camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Camera could not be opened.")
    exit()

print("Smart Attendance System started.")
print("Look at the camera.")
print("Press Q to exit.")

last_recognition = ""

while True:
    success, frame = camera.read()

    if not success:
        break

    try:
        results = DeepFace.find(
            img_path=frame,
            db_path=DATASET_PATH,
            model_name="VGG-Face",
            detector_backend="opencv",
            enforce_detection=False,
            silent=True
        )

        if len(results) > 0 and len(results[0]) > 0:

            identity = results[0].iloc[0]["identity"]

            student_folder = os.path.basename(
                os.path.dirname(identity)
            )

            if student_folder != last_recognition:
                mark_attendance(student_folder)
                last_recognition = student_folder

            cv2.putText(
                frame,
                f"Present: {student_folder}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

    except Exception:
        pass

    cv2.imshow(
        "Smart Attendance System",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()

print("Attendance system stopped.")