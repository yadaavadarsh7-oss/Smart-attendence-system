import cv2
import os

# Create dataset folder if it doesn't exist
os.makedirs("dataset", exist_ok=True)

name = input("Enter student name: ").strip()
student_id = input("Enter student ID: ").strip()

if not name or not student_id:
    print("Name and ID cannot be empty.")
    exit()

# Create a folder for this student
student_folder = os.path.join("dataset", f"{student_id}_{name}")
os.makedirs(student_folder, exist_ok=True)

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Camera could not be opened.")
    exit()

print("Camera started.")
print("Look at the camera.")
print("Press Q to stop.")

count = 0
max_images = 10

while count < max_images:
    success, frame = camera.read()

    if not success:
        print("Could not read camera.")
        break

    cv2.imshow("Student Registration", frame)

    key = cv2.waitKey(1) & 0xFF

    # Press S to save a face image
    if key == ord("s"):
        filename = os.path.join(
            student_folder,
            f"{student_id}_{count + 1}.jpg"
        )

        cv2.imwrite(filename, frame)
        count += 1

        print(f"Image {count}/{max_images} saved.")

    # Press Q to quit
    if key == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()

print(f"Registration completed: {count} images saved.")