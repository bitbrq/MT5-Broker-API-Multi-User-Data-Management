from app.utils import encrypt_password
from app.config import SQLITE3_PATH
import importlib
import inspect
import os

def init_db(db_manager):
    """
    Initialize databases using the EncryptedDBManager.
    
    :param db_manager: An instance of EncryptedDBManager.
    """
    # Dynamically creating Databases
    models_module = importlib.import_module('app.models')
    function_names = [name for name, _ in inspect.getmembers(models_module, inspect.isfunction)]
    for name in function_names:
        if name != "client":
            db_name = f"{name}.db"
            db_file = os.path.join(SQLITE3_PATH, f"{db_name}.enc")
            if os.path.exists(db_file):
                continue
            else:
                # Create a new database in RAM
                db_manager.create_new_database(db_name)
                conn = db_manager.get_db_connection(db_name)
                
                try:
                    # Initialize the database using the corresponding function from models
                    func = getattr(models_module, name)
                    func(conn)
                    if name == "users":
                        dummy_users = [
                            ("mrbb", encrypt_password("bitbrq@gmail.com"), "api_server", "admin", True)
                        ]
                        cursor = conn.cursor()
                        cursor.executemany(
                            """INSERT INTO users (username, password, server, role, is_active)
                            VALUES (?, ?, ?, ?, ?)""",
                            dummy_users
                        )
                        conn.commit()
                        print("Dummy users added to the users database.")


                except Exception as e:
                    print(f"Error initializing database {name}: {e}")
                finally:
                    # Save the database to disk in encrypted form
                    db_manager.explicit_save()
    
        
