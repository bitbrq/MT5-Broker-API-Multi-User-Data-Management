from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.utils import *
import MetaTrader5 as mt5App

router = APIRouter()

# Info Tab 
@router.post("/user_info")
async def info(data: dict):
    try:
        username = data.get("username")
        cursor = connect_db(username)
        db_data = cursor.execute("SELECT * FROM account_details").fetchall()
        if db_data:
            columns = [column[0] for column in cursor.description]
            json_data = [dict(zip(columns, row)) for row in db_data]

            return JSONResponse(content={"success": True, "data": json_data}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": "No account details found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Chart Tab
@router.post("/user_chart")    
async def chart(data: dict):
    try:
        username = data.get("username")
        cursor = connect_db(username)
        # profit
        profit = cursor.execute(""" 
                SELECT DATE(datetime(time, 'unixepoch')) AS date, net_profit AS profit
                FROM history_deals
                GROUP BY DATE(datetime(time, 'unixepoch'))
                """).fetchall()
        # Remove rows with zero net_profit values
        profit = [row for row in profit if row[1] is not None and row[1] > 0]
        # Round profit values to 2 decimal places
        profit = [
            [row[0], round(row[1] if row[1] is not None else 0, 2)]
            for row in profit
        ]    
        
        # balance
        balance = cursor.execute(""" 
                SELECT DATE(datetime(time, 'unixepoch')) AS date, net_balance AS balance
                FROM history_deals
                GROUP BY DATE(datetime(time, 'unixepoch'))
                """).fetchall()
        # Round balance values to 2 decimal places
        balance = [
            [row[0], round(row[1] if row[1] is not None else 0, 2)]
            for row in balance
        ]
        
        # Drawdown
        drawdown = cursor.execute("""
            SELECT DATE(datetime(time, 'unixepoch')) AS date,
                SUM(current_balance) AS drawdown
            FROM history_deals
            WHERE symbol = '' AND profit < 0
            GROUP BY DATE(datetime(time, 'unixepoch'))
            """).fetchall()
        # Round drawdown to 2 decimal places
        drawdown = [
            [row[0], round(row[1] if row[1] is not None else 0, 2)]
            for row in drawdown
        ]

        # Deposits
        deposit = cursor.execute("""
            SELECT DATE(datetime(time, 'unixepoch')) AS date,
                SUM(profit) AS deposit
            FROM history_deals
            WHERE symbol = '' AND profit > 0
            GROUP BY DATE(datetime(time, 'unixepoch'))
            """).fetchall()
        # Round deposits to 2 decimal places
        deposit = [
            [row[0], round(row[1] if row[1] is not None else 0, 2)]
            for row in deposit
        ]

        # Gain
        growth = cursor.execute("""
            SELECT DATE(datetime(time, 'unixepoch')) AS date, gain AS growth FROM history_deals WHERE gain IS NOT NULL
            GROUP BY DATE(datetime(time, 'unixepoch'))
            ORDER BY DATE(datetime(time, 'unixepoch')) ASC
            """).fetchall()

        if profit and balance and drawdown and deposit and growth:
            return JSONResponse(content={"success": True, "data": {
                    "profit": profit,
                    "balance": balance,
                    "drawdown": drawdown,
                    "deposit": deposit,
                    "growth": growth
                } }, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": "No account details found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Monthly Analysis Tab
@router.post("/user_analytics")
async def analytics(data: dict):
    try:
        username = data.get("username")
        cursor = connect_db(username)
        month_map = {'01': 'jan', '02': 'feb', '03': 'mar', '04': 'apr', '05': 'may', '06': 'jun',
                    '07': 'jul', '08': 'aug', '09': 'sep', '10': 'oct', '11': 'nov', '12': 'dec'}

        profit_by_year = {}
        for year, month, profit in cursor.execute("""
            SELECT strftime('%Y', datetime(time, 'unixepoch')) AS year,
                strftime('%m', datetime(time, 'unixepoch')) AS month,
                SUM(current_profit) AS total_profit
            FROM history_deals
            GROUP BY year, month
            ORDER BY year, month;
        """).fetchall():
            profit_by_year.setdefault(year, {m: 0 for m in month_map.values()})[month_map[month]] = profit

        years = list(profit_by_year.keys())
        year_months = [{"year": y, "months": profit_by_year[y]} for y in years]


        # Return the organized data as a JSON response
        if year and year_months:
            return JSONResponse(content={"success": True, "data": {"years": years, "year_months":year_months}}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": "No profit data found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Order Calculate Margin (Verified)  (Just Calculator so no database required)
@router.post('/user_order_calc_margin')
def user_order_calc_margin(data: dict):
    allowed_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY']
    try:
        symbol = data.get('symbol')
        if symbol is None:
            return JSONResponse(content={"success": False, "message": "'symbol' required like 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY'"}, status_code=400)
        volume = data.get('volume')
        if volume is None:
            return JSONResponse(content={"success": False, "message": "'volume' required in integer or Float Format"}, status_code=400)
        action = data.get('action')
        if action is None:
            return JSONResponse(content={"success": False, "message": "'action' required in integer Format. Reference 'ORDER_TYPE_BUY': 0, 'ORDER_TYPE_SELL': 1, 'ORDER_TYPE_BUY_LIMIT': 2, 'ORDER_TYPE_SELL_LIMIT': 3, 'ORDER_TYPE_BUY_STOP': 4, 'ORDER_TYPE_SELL_STOP': 5, 'ORDER_TYPE_BUY_STOP_LIMIT': 6, 'ORDER_TYPE_SELL_STOP_LIMIT': 7, 'ORDER_TYPE_CLOSE_BY': 8"}, status_code=400)
        price_open = data.get('price_open')
        if price_open is None:
            return JSONResponse(content={"success": False, "message": "'price_open' required in integer or Float Format"}, status_code=400)
        if symbol not in allowed_symbols:
            return JSONResponse(content={"success": False, "message": "Allowed Symbols Are 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY'"}, status_code=400)
        if not isinstance(symbol, str) or not isinstance(volume, (int, float)) or not isinstance(action, int) or not isinstance(price_open, (int, float)):
            return JSONResponse(content={"success": False, "message": "Invalid parameter types"}, status_code=400)

        margin = mt5App.order_calc_margin(action, symbol, volume, price_open)
        if margin is None:
            return JSONResponse(content={"success": False, "message": "Error calculating margin"}, status_code=400)
        else:
            return JSONResponse(content={"success": True, "data": {"margin": margin}}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
       
# Order Calculate Profit (Verified)  (Just Calculator so no database required)
@router.post('/user_order_calc_profit')
def user_order_calc_profit(data: dict):
    allowed_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY']
    try:
        symbol = data.get('symbol')
        if symbol is None:
            return JSONResponse(content={"success": False, "message": "'symbol' required like 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY'"}, status_code=400)
        volume = data.get('volume')
        if volume is None:
            return JSONResponse(content={"success": False, "message": "'volume' required in integer or Float Format"}, status_code=400)
        action = data.get('action')
        if action is None:
            return JSONResponse(content={"success": False, "message": "'action' required in integer Format. Reference 'ORDER_TYPE_BUY': 0, 'ORDER_TYPE_SELL': 1, 'ORDER_TYPE_BUY_LIMIT': 2, 'ORDER_TYPE_SELL_LIMIT': 3, 'ORDER_TYPE_BUY_STOP': 4, 'ORDER_TYPE_SELL_STOP': 5, 'ORDER_TYPE_BUY_STOP_LIMIT': 6, 'ORDER_TYPE_SELL_STOP_LIMIT': 7, 'ORDER_TYPE_CLOSE_BY': 8"}, status_code=400)
        price_open = data.get('price_open')
        if price_open is None:
            return JSONResponse(content={"success": False, "message": "'price_open' required in integer or Float Format"}, status_code=400)
        price_close = data.get('price_close')
        if price_close is None:
            return JSONResponse(content={"success": False, "message": "'price_close' required in integer or Float Format"}, status_code=400)
        if symbol not in allowed_symbols:
            return JSONResponse(content={"success": False, "message": "Allowed Symbols Are 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY'"}, status_code=400)

        if not isinstance(symbol, str) or not isinstance(volume, (int, float)) or not isinstance(action, int) or not isinstance(price_open, (int, float)) or not isinstance(price_close, (int, float)):
            return JSONResponse(content={"success": False, "message": "Invalid parameter types"}, status_code=400)

        profit = mt5App.order_calc_profit(action, symbol, volume, price_open, price_close)
        if profit is None:
            return JSONResponse(content={"success": False, "message": "Error calculating profit"}, status_code=400)
        else:
            return JSONResponse(content={"success": True, "data": {"profit": profit}}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)

