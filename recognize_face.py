import cv2
import os
from deepface import DeepFace

DATASET_PATH = "dataset"

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Camera could not be opened.")
    exit()

print("Face recognition started.")
print("Press Q to exit.")

while True:
    success, frame = camera.read()

    if not success:
        print("Could not read camera.")
        break

    cv2.imshow("Smart Attendance - Face Recognition", frame)

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

            # Get student's folder name
            student_folder = os.path.basename(
                os.path.dirname(identity)
            )

            cv2.putText(
                frame,
                f"Recognized: {student_folder}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

    except Exception as e:
        pass

    cv2.imshow("Smart Attendance - Face Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
