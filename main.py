import subprocess
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.init_dbs import init_db
from app.utils import db_manager
from app.routes import auth, mt5, myfx, data, widgets, unsecured
import MetaTrader5 as mt5App
import redis
import os

# Function to start the logging script in a separate terminal
def start_logger():
    data_updater_script = "data_updater.py" 
    try:
        # Windows: Open new cmd window
        subprocess.Popen(["cmd.exe", "/c", f"start cmd /k python {data_updater_script}"], shell=True)
    except FileNotFoundError:
        # Linux/macOS: Open terminal and run script
        subprocess.Popen(["gnome-terminal", "--", "python3", data_updater_script])

# Define lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    app.state.db_manager = db_manager
    init_db(db_manager)
    db_manager.load_all_databases()

    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)
    app.state.redis_client = redis_client

    if mt5App.initialize():
        print("MetaTrader 5 is Running")
        #print("Terminal Info:", mt5App.terminal_info())
        #print("MT5 Version:", mt5App.version())
    else:
        print("mt5.initialize() failed")

    start_logger()

    yield  # App runs here

# Initialize FastAPI with lifespan
app = FastAPI(lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(auth.router)
app.include_router(mt5.router)
app.include_router(myfx.router)
app.include_router(data.router)
app.include_router(widgets.router)
app.include_router(unsecured.router)

# Root endpoint
@app.get("/")
async def read_root():
    return {"message": "Welcome to the FastAPI MT5 Project!"}

# Run FastAPI
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=4090, reload=True)