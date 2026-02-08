from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from app.config import SQLITE3_PATH, AES_KEY
from threading import Lock
import sqlite3
import atexit
import jwt
import os


# Encrypt the password using Fernet (AES encryption)
def encrypt_password(password: str) -> str:
    fernet = Fernet(AES_KEY.encode())
    return fernet.encrypt(password.encode()).decode()

# Decrypt the password
def decrypt_password(encrypted_password: str) -> str:
    fernet = Fernet(AES_KEY.encode())
    return fernet.decrypt(encrypted_password.encode()).decode()

# Create a JWT token
def create_jwt_token(userdata: str) -> str:
    expiry = datetime.utcnow() + timedelta(minutes=int(os.getenv("TOKEN_EXPIRY")))
    token = jwt.encode({"userdata": userdata, "exp": expiry}, os.getenv("JWT_KEY"), algorithm="HS256")
    return token

# Decode the JWT token and extract userdata
def decode_jwt_token(token: str) -> str:
    try:
        data = jwt.decode(token, os.getenv("JWT_KEY"), algorithms=["HS256"])
        return data.get("userdata", "Invalid token structure")
    except jwt.ExpiredSignatureError:
        return "Token has expired"
    except jwt.InvalidTokenError:
        return "Invalid token"

# Connect_db function available globaly and retrn curser for dbs stored in ram
def connect_db(dbname: str):
    if not db_manager:
        raise Exception("Database Manager is not initialized")
    conn = db_manager.get_db_connection(str(dbname) + ".db")
    cursor = conn.cursor()
    return cursor

# Create CSV File
def create_csv(data):
    csv_output = []
    time_columns = {"time", "time_done", "time_setup"}  # Columns to format as timestamps

    # Extract column names from the first row of data (assuming all rows have the same keys)
    if data:
        columns = data[0].keys()
        csv_output.append(','.join(columns))  # Add header row

        # Format rows
        for row in data:
            formatted_row = []
            for col in columns:
                item = row.get(col)
                if col in time_columns and item is not None:
                    try:
                        # Convert Unix timestamp to human-readable format
                        item = datetime.utcfromtimestamp(int(item)).strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        pass
                formatted_row.append(str(item) if item is not None else '')
            csv_output.append(','.join(formatted_row))  # Add formatted row

    # Create CSV content
    csv_content = '\n'.join(csv_output).strip()
    return csv_content

# Update Database for all MT5 endpoints
def update_database(dbname, tablename, data):
    UNIQUE_IDENTIFIER_MAPPING = {
        'account_details': 'login',
        'history_orders': 'ticket',
        'history_deals': 'ticket',
        'chart': 'date',
        'symbols': 'symbol_name',
        'all_symbol_details': 'name',
        'eurusd_rates_m1': 'time',
        'eurusd_rates_d1': 'time',
        'gbpusd_rates_m1': 'time',
        'gbpusd_rates_d1': 'time',
        'usdjpy_rates_m1': 'time',
        'usdjpy_rates_d1': 'time',
        'usdchf_rates_m1': 'time',
        'usdchf_rates_d1': 'time',
        'eurjpy_rates_m1': 'time',
        'eurjpy_rates_d1': 'time',
        'gbpjpy_rates_m1': 'time',
        'gbpjpy_rates_d1': 'time',
        'eurusd_ticks': 'time',
        'accounts': 'id',
        'dailyGain': 'date',
        'dataDaily': 'date'
    }

    COLUMN_NAME_MAPPING = {
        'select': 'select_bool',
        'order': 'order_no',
    }

    try:
        if isinstance(data, dict):
            data = [data]

        unique_identifier = UNIQUE_IDENTIFIER_MAPPING.get(tablename)
        if not unique_identifier:
            raise ValueError(f"No unique identifier mapping found for table: {tablename}")

        cursor = connect_db(dbname, readonly=False)
        table_info = cursor.execute(f"PRAGMA table_info({tablename})").fetchall()
        table_columns = [column[1] for column in table_info]

        for item in data:
            # Apply column name mapping
            mapped_item = {COLUMN_NAME_MAPPING.get(k, k): v for k, v in item.items()}
            filtered_item = {k: v for k, v in mapped_item.items() if k in table_columns}
            identifier_value = filtered_item.get(unique_identifier)

            if identifier_value is None:
                print(f"Warning: Unique identifier '{unique_identifier}' not found in data. Skipping item.")
                continue

            query = f"SELECT {unique_identifier} FROM {tablename} WHERE {unique_identifier} = '{identifier_value}'"
            result = cursor.execute(query).fetchall()

            if result:
                set_clause = ', '.join([f'"{k}" = \'{v.replace("'", "''")}\'' if isinstance(v, str) else f'"{k}" = {v}' for k, v in filtered_item.items()])
                update_query = f"UPDATE {tablename} SET {set_clause} WHERE {unique_identifier} = '{identifier_value}'"
                cursor.execute(update_query)
                cursor.connection.commit()
            else:
                columns = ', '.join([f'"{k}"' for k in filtered_item.keys()])
                values = ', '.join([f"'{v.replace("'", "''")}'" if isinstance(v, str) else str(v) for v in filtered_item.values()])
                insert_query = f"INSERT INTO {tablename} ({columns}) VALUES ({values})"
                cursor.execute(insert_query)
                cursor.connection.commit()
            

        print(f"Database: {dbname}, Table Name: {tablename} updated completed successfully.")
        return True

    except Exception as e:
        print(f"Error updating database: {e}")
        return False

# DBManager Class
class DBManager:
    def __init__(self, db_directory):
        self.db_directory = db_directory
        self.ram_dbs = {}          # Primary writer connections
        self.reader_conns = {}     # Dedicated reader connections
        self.write_locks = {}      # Per-database write locks
        atexit.register(self.cleanup)

    def cleanup(self):
        self.explicit_save()
        self.ram_dbs.clear()
        self.reader_conns.clear()
        print(f"✅ All RAM Dbs are cleared.")

    def explicit_save(self):
        for db_name, db_conn in self.ram_dbs.items():
            db_path = os.path.join(self.db_directory, f"{db_name}.enc")
            try:
                if db_conn.in_transaction:
                    db_conn.commit()
                    
                with open(db_path, "w") as f:
                    for line in db_conn.iterdump():
                        f.write(f"{line}\n")
                        
                self.encrypt_file(db_path)
                print(f"✅ {db_name} Successfully Written to Disk")
            except Exception as e:
                print(f"[ERROR] Failed to save {db_name}: {e}")

    def encrypt_file(self, db_file):
        fernet = Fernet(os.getenv("AES_KEY").encode())
        with open(db_file, "rb") as file:
            data = file.read()
        encrypted = fernet.encrypt(data)
        with open(db_file, "wb") as file:
            file.write(encrypted)

    def decrypt_file(self, db_file):
        fernet = Fernet(os.getenv("AES_KEY").encode())
        with open(db_file, "rb") as file:
            data = file.read()
        try:
            decrypted = fernet.decrypt(data)
            with open(db_file, "wb") as file:
                file.write(decrypted)
        except Exception:
            print(f"[WARNING] {db_file} is already decrypted or corrupted")

    def get_db_connection(self, db_name, readonly=False):
        """Modified to support both read and write connections"""
        if db_name not in self.ram_dbs:
            raise ValueError(f"Database '{db_name}' not found")
            
        if readonly:
            return self.reader_conns[db_name].cursor()
        else:
            return self.ram_dbs[db_name].cursor()

    def create_new_database(self, db_name):
        if db_name in self.ram_dbs:
            raise ValueError(f"Database '{db_name}' already exists.")
            
        # Writer connection
        self.ram_dbs[db_name] = sqlite3.connect(
            ":memory:",
            check_same_thread=False,
            isolation_level="IMMEDIATE"
        )
        self.ram_dbs[db_name].execute("PRAGMA journal_mode=WAL")
        
        # Reader connection
        self.reader_conns[db_name] = sqlite3.connect(
            ":memory:",
            check_same_thread=False
        )
        # Initial data copy
        self.ram_dbs[db_name].backup(self.reader_conns[db_name])
        
        # Initialize write lock
        self.write_locks[db_name] = Lock()

    def load_all_databases(self):
        for db_file in os.listdir(self.db_directory):
            if db_file.endswith(".enc"):
                db_name = db_file[:-4]
                db_path = os.path.join(self.db_directory, db_file)
                try:
                    self.decrypt_file(db_path)
                    
                    # Create writer connection
                    self.ram_dbs[db_name] = sqlite3.connect(
                        ":memory:",
                        check_same_thread=False,
                        isolation_level="IMMEDIATE"
                    )
                    self.ram_dbs[db_name].execute("PRAGMA journal_mode=WAL")
                    
                    # Load data
                    with open(db_path, "r") as f:
                        sql_script = f.read()
                    self.ram_dbs[db_name].executescript(sql_script)
                    
                    # Create reader connection
                    self.reader_conns[db_name] = sqlite3.connect(
                        ":memory:",
                        check_same_thread=False
                    )
                    self.ram_dbs[db_name].backup(self.reader_conns[db_name])
                    
                    self.encrypt_file(db_path)
                    print(f"✅ Database {db_name} loaded into RAM")
                except Exception as e:
                    print(f"[ERROR] Failed to load {db_name}: {e}")

# Connect_db function
def connect_db(dbname: str, readonly=True):
    if not db_manager:
        raise Exception("Database Manager is not initialized")
    
    full_dbname = f"{dbname}.db"
    cursor = db_manager.get_db_connection(full_dbname, readonly)
    
    if readonly:
        cursor.execute("PRAGMA query_only=ON")  # Enforce read-only
        
    return cursor

# Initialize globally
db_manager = DBManager(db_directory=SQLITE3_PATH)

