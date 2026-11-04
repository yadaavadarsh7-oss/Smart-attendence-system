CSV_HEADERS = ["Student ID", "Name", "Date", "Time", "Status"]





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
