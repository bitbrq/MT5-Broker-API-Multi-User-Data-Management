from app.config import API_USER, API_PASS, API_SERVER, API_URL, DUMMY_USER, DUMMY_PASS, DUMMY_SERVER
from datetime import datetime, UTC, time, timedelta
from app.utils import *
import httpx
import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler

# Configure logging (unchanged)
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

# Global variables (unchanged)
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
    """Your original API call function (unchanged)"""
    url = f"{API_URL}{endpoint}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request("POST", url, json=data, headers=Authorization)
            api_data = response.json()
            return api_data
    except Exception as e:
        logger.error(f"API call error for {endpoint}: {str(e)}")
        return {"error": str(e)}

async def general_data():
    """Your original general_data function (unchanged)"""
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY']
    for symbol in symbols:
        await call_api(f"/copy_rates_range", data={"symbol": symbol})
        logger.info(f"Updating data for Currency Pair: {symbol}")
    await call_api(f"/all_symbol_details", data={})

async def token_refresh_task():
    """Handles hourly token refresh"""
    global Authorization, role
    while True:
        try:
            now = datetime.now(UTC)
            # Calculate sleep until next hour
            next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
            sleep_seconds = (next_hour - now).total_seconds()
            await asyncio.sleep(sleep_seconds)
            
            logger.info("Performing hourly token refresh...")
            response = await call_api("/login", {
                "username": API_USER,
                "password": API_PASS,
                "server": API_SERVER
            })
            
            if response.get("success"):
                Authorization = {"Authorization": response["token"]}
                role = response.get("role")
                logger.info("Token refresh successful")
            else:
                raise Exception("Login failed")
                
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            await asyncio.sleep(60)  # Retry after 1 minute

async def midnight_updates_task():
    """Handles daily midnight updates"""
    while True:
        try:
            now = datetime.now(UTC)
            # Calculate sleep until 00:15 UTC
            target_time = time(0, 15, tzinfo=UTC)
            if now.time() >= target_time:
                next_day = now.date() + timedelta(days=1)
                target_datetime = datetime.combine(next_day, target_time)
            else:
                target_datetime = datetime.combine(now.date(), target_time)
            
            sleep_seconds = (target_datetime - now).total_seconds()
            await asyncio.sleep(sleep_seconds)
            
            logger.info("Starting midnight updates...")
            current_users_response = await call_api("/current_users", data={})
            users = current_users_response.get("data", [])
            
            for user in users:
                if user["role"] == "client" and user["is_active"] == 1:
                    # Your original user update logic
                    if user["server"] != "myfxbook":
                        logger.info(f"Updating MT5 account: {user['username']}")
                        mt5_login = await call_api("/mt5_login", {
                            "username": user["username"],
                            "password": decrypt_password(user["password"]),
                            "server": user["server"]
                        })
                        if mt5_login.get("success"):
                            for endpoint in user_endpoints:
                                await call_api(f"/{endpoint}", {"username": user["username"]})
                    else:
                        logger.info(f"Updating MyFxBook: {user['username']}")
                        myfx_login = await call_api("/myfx_login", {
                            "username": user["username"],
                            "password": decrypt_password(user["password"])
                        })
                        if myfx_login.get("success") and myfx_login.get("session"):
                            await call_api("/myfx_data", {
                                "username": user["username"],
                                "session": myfx_login["session"]
                            })
            
            await call_api("/explicit_save", data={})
            logger.info("Midnight updates completed")
            
        except Exception as e:
            logger.error(f"Midnight updates error: {str(e)}")
            await asyncio.sleep(300)  # Wait 5 minutes before retry

async def general_data_task():
    """Handles 5-minute general data updates"""
    while True:
        try:
            start_time = datetime.now(UTC)
            logger.info("Starting general data update...")
            
            # Your original general data logic
            await call_api("/mt5_login", {
                "username": DUMMY_USER,
                "password": DUMMY_PASS,
                "server": DUMMY_SERVER
            })
            await general_data()
            
            elapsed = (datetime.now(UTC) - start_time).total_seconds()
            sleep_time = max(300 - elapsed, 5)  # Minimum 5 second sleep
            await asyncio.sleep(sleep_time)
            
        except Exception as e:
            logger.error(f"General data error: {str(e)}")
            await asyncio.sleep(60)  # Wait 1 minute before retry

async def main():
    """Main function to run all tasks"""
    # Create all tasks
    tasks = [
        asyncio.create_task(token_refresh_task()),
        asyncio.create_task(midnight_updates_task()),
        asyncio.create_task(general_data_task())
    ]
    
    # Run forever
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())