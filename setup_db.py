import os
import sys

def setup():
    print("--- SolsticeOps Database Setup ---")
    print("Choose your database:")
    print("1) SQLite (Local file)")
    print("2) MySQL")
    print("3) PostgreSQL")
    
    choice = input("Select option (1-3): ")
    
    if choice == '1':
        db_url = "sqlite:///db.sqlite3"
    elif choice == '2':
        user = input("User: ")
        password = input("Password: ")
        host = input("Host (default localhost): ") or "localhost"
        port = input("Port (default 3306): ") or "3306"
        name = input("Database Name: ")
        # Using mysql-connector engine for better compatibility without C headers
        db_url = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{name}"
    elif choice == '3':
        user = input("User: ")
        password = input("Password: ")
        host = input("Host (default localhost): ") or "localhost"
        port = input("Port (default 5432): ") or "5432"
        name = input("Database Name: ")
        db_url = f"postgres://{user}:{password}@{host}:{port}/{name}"
    else:
        print("Invalid choice")
        sys.exit(1)

    env_path = ".env"
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    
    with open(env_path, "w") as f:
        db_url_found = False
        for line in lines:
            if line.startswith("DATABASE_URL="):
                f.write(f"DATABASE_URL={db_url}\n")
                db_url_found = True
            else:
                f.write(line)
        if not db_url_found:
            f.write(f"DATABASE_URL={db_url}\n")

    print(f"\nSuccess! DATABASE_URL updated in .env")
    print("Now run: python manage.py migrate")

if __name__ == "__main__":
    setup()
