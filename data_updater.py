from app.config import API_USER, API_PASS, API_SERVER, API_URL, API_WAIT_TIME, API_DATA_UPDATE_INTERVAL, DUMMY_USER, DUMMY_PASS, DUMMY_SERVER
from datetime import datetime, UTC
from app.utils import *
import httpx
import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler

# ✅ Configure logging
LOG_FILE = "api_logs.txt"
logger = logging.getLogger("API_Logger")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(message)s")

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1048576, backupCount=3)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# ✅ Global variables for authentication
Authorization = None
user_id = None
role = None
user_endpoints = [
    "history_orders",
    "history_deals",
    "account_details",
    "add_gain",
]

async def call_api(endpoint: str, data: dict):
    url = f"{API_URL}{endpoint}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request("POST", url, json=data, headers=Authorization)
            api_data = response.json()
            return api_data
    except Exception as e:
        logger.error(f"API call error for {endpoint}: {str(e)}")
        return {"error": str(e)}
async def refresh_token():
    global Authorization
    logger.info("Refreshing API token...")
    api_login = {"username": API_USER, "password": API_PASS, "server": API_SERVER}
    response = await call_api("/login", api_login)
    if response.get("success"):
        token = response.get("token")
        if token:
            Authorization = {"Authorization": token}
            logger.info("Token refresh successful")
            return True
    logger.error("Token refresh failed")
    return False

async def general_data():
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY']

    logger.info("Logging in to Dummy user to update Currency Pair data")
    await call_api("/mt5_login", data={"username": DUMMY_USER, "password": DUMMY_PASS, "server": DUMMY_SERVER})           
    for symbol in symbols:
        await call_api("/copy_rates_range", data={"symbol": symbol})
        logger.info(f"Updated data for Currency Pair: {symbol}")
    await call_api("/all_symbol_details", data={})

async def user_data():
    logger.info("Updating users Data...")
    current_users_response = await call_api("/current_users", data={})
    users = current_users_response.get("data", [])
    
    for user in users:
        if user["role"] == "client" and user["is_active"] == 1:
            if user["server"] != "myfxbook":
                logger.info(f"Updating MT5 data for Account ID: {user['username']}")
                mt5_login_response = await call_api("/mt5_login", data={
                    "username": user["username"],
                    "password": decrypt_password(user["password"]),
                    "server": user["server"]
                })
                if mt5_login_response.get("success"):
                    for endpoint in user_endpoints:
                        endpoint_response = await call_api(f"/{endpoint}", data={"username": user["username"]})
                        if endpoint_response.get("success"):
                            logger.info(f"{endpoint}: {endpoint_response.get('message')}")
            else:
                logger.info(f"Updating MyFxBook data for User: {user['username']}")
                myfx_login_response = await call_api("/myfx_login", data={
                    "username": user["username"],
                    "password": decrypt_password(user["password"])
                })
                if myfx_login_response.get("success"):
                    session = myfx_login_response.get("session")
                    if session:
                        myfx_data_response = await call_api("/myfx_data", data={
                            "username": user["username"],
                            "session": session
                        })
                        if myfx_data_response.get("success"):
                            logger.info(myfx_data_response.get("message"))
    
    logger.info("Saving Database Changes...")
    await call_api("/explicit_save", data={})
    logger.info("Database save completed")

def should_run_daily_update():
    now = datetime.now(UTC)
    # Run once per day at midnight UTC
    return now.hour == 0 and now.minute < 5  # 5-minute window to ensure it runs

async def main():
    logger.info("Initializing Script...")
    
    # Initial token refresh
    if not await refresh_token():
        logger.error("Initial token refresh failed. Exiting.")
        return
    
    # Initial data updates
    await general_data()
    await user_data()
    
    # Schedule regular updates
    last_token_refresh = datetime.now(UTC)
    last_general_update = datetime.now(UTC)
    last_user_update = datetime.now(UTC)
    
    while True:
        now = datetime.now(UTC)
        
        # Refresh token every hour
        if (now - last_token_refresh) >= timedelta(hours=1):
            await refresh_token()
            last_token_refresh = now
        
        # Update general data every 5 minutes
        if (now - last_general_update) >= timedelta(minutes=5):
            await general_data()
            last_general_update = now
        
        # Update user data once per day at midnight UTC
        if should_run_daily_update() and (now - last_user_update) >= timedelta(hours=12):
            await user_data()
            last_user_update = now
        
        # Wait before next iteration
        await asyncio.sleep(API_WAIT_TIME)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Script terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")