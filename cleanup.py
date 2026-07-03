import os
import shutil
import sqlite3

def cleanup_workspace():
    print("=" * 50)
    print("STARTING WORKSPACE CLEANUP...")
    print("=" * 50)
    
    # 1. Delete SQLite Database
    db_file = "agent_database.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception as e:
            print(f"[WARNING] Could not delete file {db_file} ({e}). Attempting SQLite truncate cleanup...")
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                # Fetch all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence']
                
                # Disable foreign keys temporarily
                cursor.execute("PRAGMA foreign_keys = OFF;")
                
                for table in tables:
                    cursor.execute(f"DELETE FROM {table};")
                    print(f"  - Cleared table records: {table}")
                    
                # Reset autoincrement sequence safely
                try:
                    cursor.execute("DELETE FROM sqlite_sequence;")
                except Exception:
                    pass
                conn.commit()
                conn.close()
                print(f"[SUCCESS] Truncated SQLite database and reset task indices to 1.")
            except Exception as ex:
                print(f"[ERROR] Truncate cleanup fallback failed: {ex}")
    else:
        print(f"[INFO] Database file '{db_file}' does not exist.")
        
    # 2. Clear storage folders
    folders_to_clear = [
        "storage/screenshots",
        "storage/reports",
        "storage/uploads",
        "storage/logs"
    ]
    
    for folder in folders_to_clear:
        if os.path.exists(folder):
            print(f"\nClearing folder: {folder}")
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                        print(f"  - Deleted file: {filename}")
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        print(f"  - Deleted directory: {filename}")
                except Exception as e:
                    print(f"  - [ERROR] Failed to delete {filename}: {e}")
        else:
            print(f"[INFO] Folder '{folder}' does not exist.")
            
    print("\n" + "=" * 50)
    print("CLEANUP COMPLETED SUCCESSFULLY!")
    print("=" * 50)

if __name__ == "__main__":
    cleanup_workspace()
