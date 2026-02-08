from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.utils import *

router = APIRouter()

# Info Tab 
@router.post("/currency_pair_widget")
async def currency_pair_widget(data: dict):
    allowed_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY']
    try:
        symbol = data.get('symbol')
        if symbol is None:
            return JSONResponse(content={"success": False, "message": "'symbol' required like 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY'"}, status_code=400)
        if symbol not in allowed_symbols:
            return JSONResponse(content={"success": False, "message": "Allowed Symbols Are 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY'"}, status_code=400)
        db_name = f"{symbol.lower()}_rates"
        cursor = connect_db(db_name)
        # Get D1 data of Current and last Month please note order should be by time and time is in unix timestemps
        db_data_d1 = cursor.execute(f"SELECT datetime(time, 'unixepoch') as time, open, high, low, close, tick_volume, spread, real_volume FROM {db_name}_d1 ORDER BY time DESC LIMIT 60").fetchall()
        
        # Get M1 dataof Current and last Day please note order should be by time and time is in unix timestemps
        db_data_m1 = cursor.execute(f"SELECT datetime(time, 'unixepoch') as time, open, high, low, close, tick_volume, spread, real_volume FROM {db_name}_m1 ORDER BY time DESC LIMIT 4320").fetchall()
        
        if db_data_d1 or db_data_m1:
            return JSONResponse(content={"success": True, "data": {"d1": db_data_d1, "m1": db_data_m1} }, status_code=200)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()