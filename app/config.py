import os
from dotenv import load_dotenv

# Load environment variables from the root directory
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env"))
load_dotenv(dotenv_path=dotenv_path)

# Security
AES_KEY = os.getenv("AES_KEY")
JWT_KEY = os.getenv("JWT_KEY")
TOKEN_EXPIRY = int(os.getenv("TOKEN_EXPIRY", 3600))  # Default to 3600 if not set

# API
API_USER= os.getenv("API_USER")
API_PASS=os.getenv("API_PASS")
API_SERVER=os.getenv("API_SERVER")
API_URL=os.getenv("API_URL")
API_WAIT_TIME=int(os.getenv("API_WAIT_TIME"))
API_DATA_UPDATE_INTERVAL=os.getenv("API_DATA_UPDATE_INTERVAL")

#DUMMY USER
DUMMY_USER=os.getenv("DUMMY_USER")
DUMMY_PASS=os.getenv("DUMMY_PASS")
DUMMY_SERVER=os.getenv("DUMMY_SERVER")

# Database
SQLITE3_PATH = os.getenv("SQLITE3_PATH")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")

