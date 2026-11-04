
from database import create_admin

if __name__ == "__main__":
    username = input("Create Admin Username: ").strip()
    password = input("Create Admin Password: ")

    if not username or not password:
        print("Username and password cannot be empty.")
    else:
        try:
            create_admin(username, password)
            print("Admin account created successfully!")
        except Exception as error:
            print("Could not create admin:", error)
