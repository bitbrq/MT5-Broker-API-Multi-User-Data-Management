from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.future import select
from datetime import datetime
import MetaTrader5 as mt5App
from app.middleware import *
from app.utils import *
from app.models import *
import pandas as pd

router = APIRouter()

#Add Gain And copy Rate Ranges have Write access of dbs

# Mt5 Account Login
@router.post("/mt5_login")
async def mt5_login(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        username = data.get("username")
        password = data.get("password")
        server = data.get("server")

        if not username or not password or not server:
            return JSONResponse(content={"success": False, "message": "Missing username, password, or server"}, status_code=400)

        cursor = connect_db("users")
        result = cursor.execute(f"SELECT * FROM users WHERE username = '{username}'").fetchall()

        if not result:
            return JSONResponse(content={"success": False, "message": "User not found"}, status_code=404)

        user = result[0]

        if decrypt_password(user[1]) != password:
            return JSONResponse(content={"success": False, "message": "Incorrect password"}, status_code=401)

        if server != user[2]:
            return JSONResponse(content={"success": False, "message": "Server mismatch"}, status_code=403)
        
        authorized = mt5App.login(int(username), password=password, server=server)
        if authorized:
            return JSONResponse(content={"success": True, "message": "Login Successful. Now your data can be updated."}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": mt5App.last_error()}, status_code=400)

    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Internal server error: {str(e)}"}, status_code=500)
    finally:
        cursor.close()

# GENERAL DATA ENDPOINTS --------------------------------------------------------------------------------------------------------------------------------------------------------------

# All Symbol Details (Verified)
@router.post("/all_symbol_details")
def all_symbol_details(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        symbols = mt5App.symbols_get()
        all_symbol_info = [symbol._asdict() for symbol in symbols]
        if all_symbol_info:
            update_database("all_symbol_details", "all_symbol_details", all_symbol_info)
            return JSONResponse(content={"success": True, "message": f"All Symbol Details are Updated on {datetime.now()}"}, status_code=200)
        return JSONResponse(content={"success": False, "message": "No symbols found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)

# Copy Rates Range (Verified) (Default 4 hours timeframe is used)
@router.post('/copy_rates_range')
def copy_rates_range(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        symbol = data.get('symbol')
        if symbol is None:
            return JSONResponse(content={"success": False, "message": "'symbol' required like 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY'"}, status_code=400)

        db_name = f"{symbol.lower()}_rates"
        cursor = connect_db(db_name, readonly=False)

        tablename_m1 = f"{symbol.lower()}_rates_m1"
        tablename_d1 = f"{symbol.lower()}_rates_d1"
        timeframe_m1 = "TIMEFRAME_M1"
        timeframe_d1 = "TIMEFRAME_D1"
        timeframe_m1_constant = getattr(mt5App, timeframe_m1, None)
        timeframe_d1_constant = getattr(mt5App, timeframe_d1, None)
        
        # Code for updating Minutes Rates Database
        last_time_m1 = cursor.execute(f"SELECT MAX(time) FROM {tablename_m1}").fetchone()[0]
        from_date_m1 = datetime.fromtimestamp(last_time_m1 + 1) if last_time_m1 else datetime.now() - timedelta(days=30)
        to_date_m1 = datetime.now()

        rates_m1 = mt5App.copy_rates_range(symbol, timeframe_m1_constant, from_date_m1, to_date_m1)
        if rates_m1 is not None:
            rates_frame_m1 = pd.DataFrame(rates_m1)
            rates_frame_m1['time'] = rates_frame_m1['time'].astype(int).astype(str)
            rates_json_m1 = rates_frame_m1.to_dict(orient='records')
            success_m1 = update_database(db_name, tablename_m1, rates_json_m1)
            # Delete records older than 1 month
            one_month_ago = int((datetime.now() - timedelta(days=30)).timestamp())
            cursor.execute(f"DELETE FROM {tablename_m1} WHERE time < ?", (one_month_ago,))
            cursor.connection.commit()
        else:
            return JSONResponse(content={"success": False, "message": "Failed to retrieve M1 rates"}, status_code=404)
        

        # Code for updating Daily Rates Database
        last_time_d1 = cursor.execute(f"SELECT MAX(time) FROM {tablename_d1}").fetchone()[0]
        from_date_d1 = datetime.fromtimestamp(last_time_d1 + 1) if last_time_d1 else datetime(2000, 1, 1)
        to_date_d1 = datetime.now()

        rates_d1 = mt5App.copy_rates_range(symbol, timeframe_d1_constant, from_date_d1, to_date_d1)
        if rates_d1 is not None:
            rates_frame_d1 = pd.DataFrame(rates_d1)
            rates_frame_d1['time'] = rates_frame_d1['time'].astype(int).astype(str)
            rates_json_d1 = rates_frame_d1.to_dict(orient='records')
            success_d1 = update_database(db_name, tablename_d1, rates_json_d1)
        else:
            return JSONResponse(content={"success": False, "message": "Failed to retrieve D1 rates"}, status_code=404)
            
        if success_m1 and success_d1:
            cursor.connection.commit()
            return JSONResponse(content={"success": True, "message": f"{symbol} Rates are Updated on {datetime.now()}"}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()
        
# Copy Ticks Range (Verified) (Default COPY_TICKS_ALL is used) (start date is from 01-jan-2025 us used and data retured id ~225MB)
@router.post('/copy_ticks_range')
async def copy_ticks_range(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        symbol = data.get('symbol')
        if symbol is None:
            return JSONResponse(content={"success": False, "message": "'symbol' required like 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY'"}, status_code=400)
        #tick = data.get('tick')
        #if tick is None:
        #    return JSONResponse(content={"success": False, "message": "'tick' required. Reference: COPY_TICKS_ALL (Copy all ticks), COPY_TICKS_INFO (Copy informational ticks), COPY_TICKS_TRADE (Copy trade-related ticks), COPY_TICKS_BID (Filter ticks to include bid price changes), COPY_TICKS_ASK (Filter ticks to include ask price changes), COPY_TICKS_LAST (Filter ticks to include last price changes), COPY_TICKS_VOLUME (Filter ticks to include volume changes), COPY_TICKS_BUY (Filter ticks to include buy trade events), COPY_TICKS_SELL (Filter ticks to include sell trade events)"}, status_code=400)
        # Remove comments from above 3 lines if other Tick is required Default COPY_TICKS_ALL is used
        tick = "COPY_TICKS_ALL"
        db_name =  f"{symbol.lower()}_ticks"
        cursor = connect_db(db_name)
        last_time = cursor.execute(f"SELECT MAX(time) FROM {db_name}").fetchone()[0]
        from_date = datetime.fromtimestamp(last_time + 1) if last_time else datetime(2025, 1, 1)
        to_date = datetime.now()

        tick_constant = getattr(mt5App, tick, None)
        if tick_constant is None:
            return JSONResponse(content={"success": False, "message": "Invalid tick"}, status_code=400)
        try:
            ticks = mt5App.copy_ticks_range(symbol, from_date, to_date, tick_constant)
            if ticks is not None:
                ticks_frame = pd.DataFrame(ticks)
                ticks_frame['time'] = ticks_frame['time'].astype(int).astype(str)
                ticks_json = ticks_frame.to_dict(orient='records')
                update_database(db_name, db_name, ticks_json)
                return JSONResponse(content={"success": True, "message": f"{symbol} Rates are Updated on {datetime.now()}"}, status_code=200)
            else:
                return JSONResponse(content={"success": False, "message": "Failed to retrieve ticks"}, status_code=404)
        except Exception as e:
            print(f"Exception in copy_ticks_range: {e}")
            return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Order Calculate Margin (Verified)  (Just Calculator so no database required)
@router.post('/order_calc_margin')
def order_calc_margin(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
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
@router.post('/order_calc_profit')
def order_calc_profit(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
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

# USER SPECIFIC ENDPOINTS ------------------------------------------------------------------------------------------------------------------------------------------------------------

# MT5 Account info (Verified)
@router.post('/account_details')
async def account_details(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        username = data.get('username')
        if username:
            cursor = connect_db(username)
            # For total_swap
            swap_result = cursor.execute("SELECT SUM(swap) FROM history_deals").fetchone()
            total_swap = swap_result[0] if swap_result and swap_result[0] is not None else 0
            
            # For deposits
            net_deposits_results = cursor.execute("SELECT SUM(profit) FROM history_deals WHERE symbol = '' AND profit > 0").fetchone()
            deposits = net_deposits_results[0] if net_deposits_results and net_deposits_results[0] is not None else 0
            
            # For withdrawals
            net_withdrawal_results = cursor.execute("SELECT SUM(profit) FROM history_deals WHERE symbol = '' AND profit < 0").fetchone()
            withdrawals = net_withdrawal_results[0] if net_withdrawal_results and net_withdrawal_results[0] is not None else 0
            
            #for highest_balance
            net_balance_result = cursor.execute("SELECT net_balance FROM history_deals ORDER BY ticket DESC LIMIT 1").fetchone()
            highest_balance = net_balance_result[0] if net_balance_result and net_balance_result[0] is not None else 0  

            # For last_net_profit
            net_profit_result = cursor.execute("SELECT net_profit FROM history_deals WHERE symbol != '' ORDER BY ticket DESC LIMIT 1").fetchone()
            last_net_profit = net_profit_result[0] if net_profit_result and net_profit_result[0] is not None else 0

            account_info = mt5App.account_info()._asdict()
            if account_info:
                account_info["deposits"] = round(deposits - abs(total_swap), 2)
                account_info["withdrawals"] = round(abs(withdrawals), 2)
                account_info["net_profit"] = round(last_net_profit + abs(total_swap), 2)
                account_info["highest_balance"] = round(highest_balance, 2)
                account_info["abs_gain"] = round((account_info["net_profit"] /  account_info["deposits"]) * 100, 2)
                update_database(username, "account_details", account_info)
                return JSONResponse(content={"success": True, "message": f"{username} Account Details Updated on {datetime.now()}"}, status_code=200)
            else:
                return JSONResponse(content={"success": False, "message": "No Account found"}, status_code=404)
        else:
            return JSONResponse(content={"success": False, "message": "'username' Required"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# History Orders Get (Verified)
@router.post('/history_orders')
async def history_orders(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        username = data.get('username')
        if username:
            cursor = connect_db(username)
            last_time = cursor.execute(f"SELECT MAX(time_done) FROM history_orders").fetchone()[0]
            from_date = datetime.fromtimestamp(last_time + 1) if last_time else datetime(2000, 1, 1)
            to_date = datetime.now()

            history_orders = mt5App.history_orders_get(from_date, to_date)
            if history_orders is not None:
                history_orders_list = [order._asdict() for order in history_orders]
                update_database(username, "history_orders", history_orders_list)
                return JSONResponse(content={"success": True, "message": f"{username} History Orders Data Updated on {to_date}"}, status_code=200)
            else:
                return JSONResponse(content={"success": False, "message": "No orders found"}, status_code=404)
        else:
            return JSONResponse(content={"success": False, "message": "'username' Required"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# History Deals Get (Verified)
@router.post('/history_deals')
async def history_deals(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        username = data.get('username')
        if username:
            cursor = connect_db(username)
            last_time = cursor.execute(f"SELECT MAX(time) FROM history_deals").fetchone()[0]
            from_date = datetime.fromtimestamp(last_time + 1) if last_time else datetime(2000, 1, 1)
            to_date = datetime.now()
            
            mt5_history_deals = mt5App.history_deals_get(from_date, to_date)
            if mt5_history_deals is not None:
                history_deals = [deal._asdict() for deal in mt5_history_deals]  
                # Getting Existing Values of Net Profit and Net Balance
                cursor = connect_db(username)
                net_profit_result = cursor.execute("SELECT net_profit FROM history_deals ORDER BY ticket DESC LIMIT 1").fetchone()
                net_profit = net_profit_result[0] if net_profit_result and net_profit_result[0] is not None else 0
                net_balance_result = cursor.execute("SELECT net_balance FROM history_deals ORDER BY ticket DESC LIMIT 1").fetchone()
                net_balance = net_balance_result[0] if net_balance_result and net_balance_result[0] is not None else 0

                for deal in history_deals:
                    # Adding current balance and net balance
                    deal["current_balance"] = deal["profit"] + deal["swap"] - deal["fee"] - deal["commission"]
                    net_balance += deal["current_balance"]
                    deal["net_balance"] = net_balance
                    # Addding current profit and net profit
                    if deal["symbol"] != "":
                        deal["current_profit"] = deal["profit"] + deal["swap"] - deal["fee"] - deal["commission"]
                        net_profit += deal["current_profit"]
                        deal["net_profit"] = net_profit
                update_database(username, "history_deals", history_deals)
                return JSONResponse(content={"success": True, "message": f"{username} History Deals Data Updated on {to_date}"}, status_code=200)
            else:
                return JSONResponse(content={"success": False, "message": "No Deals found"}, status_code=404) 
        else:
            return JSONResponse(content={"success": False, "message": "'username' Required"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Calculate Gain (Verified)
@router.post('/add_gain')
async def add_gain(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        username = data.get('username')
        if username:
            cursor = connect_db(username, readonly=False)
            current_date = datetime.now().strftime("%Y-%m-%d")

            # Fetch unique trade dates excluding the current day
            trade_dates_query = "SELECT DISTINCT DATE(datetime(time, 'unixepoch')) AS trade_date FROM history_deals WHERE DATE(datetime(time, 'unixepoch')) != ? ORDER BY trade_date ASC;"
            cursor.execute(trade_dates_query, (current_date,))
            trade_dates = [row[0] for row in cursor.fetchall()]
            if not trade_dates:
                return JSONResponse(content={"success": False, "message": "No trade data found (excluding current day)"}, status_code=404)

            mid_value = 1
            for trade_date in trade_dates:
                # Fetch daily profit
                daily_profit = cursor.execute("SELECT SUM(current_profit) AS total_profit FROM history_deals WHERE DATE(datetime(time, 'unixepoch')) = ?;", (trade_date,)).fetchone()[0] or 0

                # Fetch latest ticket and net_balance for the day
                ticket_net_balance = cursor.execute("SELECT ticket, net_balance FROM history_deals WHERE DATE(datetime(time, 'unixepoch')) = ? ORDER BY ticket DESC LIMIT 1;", (trade_date,)).fetchone()
                net_balance = ticket_net_balance[1] if ticket_net_balance else 0
                ticket = ticket_net_balance[0] if ticket_net_balance else 0

                # Calculate HPR and gain
                hpr = (1 + (daily_profit / (net_balance - daily_profit))) if net_balance != 0 else 0
                mid_value *= hpr
                gain = round(((mid_value - 1) * 100), 2)

                if gain:
                    cursor.execute("UPDATE history_deals SET gain = ?WHERE ticket = ?;", (gain, ticket))
            cursor.execute("UPDATE account_details SET gain = ? WHERE login = ?;", (gain, username)) 
            cursor.connection.commit()
            return JSONResponse(content={"success": True, "message": f"{username} Gain Updated on {datetime.now()}"}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

            
# Positions Get (Verified) (Database Not Created as its response is current positions)
@router.post('/positions_get')
async def positions_get(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        username = data.get('username')
        if username:
            positions = mt5App.positions_get()
            if positions is not None:
                positions_list = [position._asdict() for position in positions]
                return JSONResponse(content={"success": True, "data": positions_list}, status_code=200)
            else:
                return JSONResponse(content={"success": False, "message": "No Position found"}, status_code=404)
        else:
            return JSONResponse(content={"success": False, "message": "'username' Required"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)


# From Here Old schema As given endpoints are not currently required. 

# Total orders (OK)
@router.post('/orders_total')
async def orders_total(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        userID = data.get('userID', None)
        if userID and userID > 0:
            user_result = await db.execute(select(User).filter_by(id=userID))
            verified_user = user_result.scalars().first()
            if not verified_user:
                return JSONResponse(content={"success": False, "message": "User not found"}, status_code=404)
        else:
            return JSONResponse(content={"success": False, "message": "'userID' Required"}, status_code=400)
        # Get the total number of orders
        total_orders = mt5App.orders_total()
        if total_orders:
            return JSONResponse(content={"success": True, "data": total_orders}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": "No orders found"}, status_code=404)

    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)

# Positions Total (OK)
@router.post('/positions_total')
async def positions_total(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        userID = data.get('userID', None)
        if userID and userID > 0:
            user_result = await db.execute(select(User).filter_by(id=userID))
            verified_user = user_result.scalars().first()
            if not verified_user:
                return JSONResponse(content={"success": False, "message": "User not found"}, status_code=404)
        else:
            return JSONResponse(content={"success": False, "message": "'userID' Required"}, status_code=400)
        total_positions = mt5App.positions_total()
        if total_positions:
            return JSONResponse(content={"success": True, "data": total_positions}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": "No Positions found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    
# Market Book Add (OK)
@router.post('/market_book_add')
async def market_book_add(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        symbol = data.get('symbol')
        if not symbol:
            return JSONResponse(content={"success": False, "message": "'symbol' required like 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY'"}, status_code=400)
        result = mt5App.market_book_add(symbol)
        if result:
            return JSONResponse(content={"success": True, "message": f"Subscribed to Market Depth for symbol: {symbol}"}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": mt5App.last_error()}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)

# Market Book Release (OK)
@router.post('/market_book_release')
async def market_book_release(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        userID = data.get('userID', None)
        if userID and userID > 0:
            user_result = await db.execute(select(User).filter_by(id=userID))
            verified_user = user_result.scalars().first()
            if not verified_user:
                return JSONResponse(content={"success": False, "message": "User not found"}, status_code=404)
        else:
            return JSONResponse(content={"success": False, "message": "'userID' Required"}, status_code=400)
        symbol = data.get('symbol')
        if symbol is None:
            return JSONResponse(content={"success": False, "message": "'symbol' parameter required like 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY'"}, status_code=400)
        result = mt5App.market_book_release(symbol)
        if result:
            return JSONResponse(content={"success": True, "message": f"Released Market Depth subscription for symbol: {symbol}"}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": f"Failed to release Market Depth subscription for symbol: {symbol}"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    
# Order Check ------>>>> VIP it cannot be tested as it checks order directly using account
@router.post('/order_check')
async def order_check(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        userID = data.get('userID', None)
        if userID and userID > 0:
            user_result = await db.execute(select(User).filter_by(id=userID))
            verified_user = user_result.scalars().first()
            if not verified_user:
                return JSONResponse(content={"success": False, "message": "User not found"}, status_code=404)
        else:
            return JSONResponse(content={"success": False, "message": "'userID' Required"}, status_code=400)
        order_request = data.get('order_request')
        if order_request is None:
            return JSONResponse(content={"success": False, "message": "'order_request' parameter required"}, status_code=400)
        if not order_request or not isinstance(order_request, dict):
            return JSONResponse(content={"success": False, "message": "Invalid or missing order_request"}, status_code=400)
        result = mt5App.order_check(order_request)
        if result:
            return JSONResponse(content={"success": True, "data": result._asdict()}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": "Error checking order"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)

# Order Send ------>>>> VIP it cannot be tested as it sends order directly using account
@router.post('/order_send')
async def order_send(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        userID = data.get('userID', None)
        if userID and userID > 0:
            user_result = await db.execute(select(User).filter_by(id=userID))
            verified_user = user_result.scalars().first()
            if not verified_user:
                return JSONResponse(content={"success": False, "message": "User not found"}, status_code=404)
        else:
            return JSONResponse(content={"success": False, "message": "'userID' Required"}, status_code=400)
        order_request = data.get('order_request')
        if not order_request or not isinstance(order_request, dict):
            return JSONResponse(content={"success": False, "message": "Invalid or missing order_request"}, status_code=400)
        result = mt5App.order_check(order_request)
        if result:
            return JSONResponse(content={"success": True, "data": result._asdict()}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": "Error checking order"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)

# Orders Get ------>>>> VIP it cannot be tested as it gets order directly using account
@router.post('/orders_get')
async def orders_get(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        userID = data.get('userID', None)
        if userID and userID > 0:
            user_result = await db.execute(select(User).filter_by(id=userID))
            verified_user = user_result.scalars().first()
            if not verified_user:
                return JSONResponse(content={"success": False, "message": "User not found"}, status_code=404)
        else:
            return JSONResponse(content={"success": False, "message": "'userID' Required"}, status_code=400)
        symbol = data.get('symbol')
        ticket = data.get('ticket')
        if symbol or ticket:
            orders = mt5App.orders_get(symbol=symbol, ticket=ticket)
        else:
            orders = mt5App.orders_get()
        if orders:
            orders_list = [order._asdict() for order in orders]
            return JSONResponse(content={"success": True, "data": orders_list}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": "No active orders OR 'symbol' required like 'EURUSD', 'GBPUSD' OR Invalid or missing 'ticket'"},status_code=400)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)

# Market Book Get (OK)
@router.post('/market_book_get')
async def market_book_get(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, admin_username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        symbol = data.get('symbol')
        if symbol is None:
            return JSONResponse(content={"success": False, "message": "'symbol' required like 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'EURJPY', 'GBPJPY'"}, status_code=400)
        book = mt5App.market_book_get(symbol)
        if book:
            market_book = [entry._asdict() for entry in book]
            return JSONResponse(content={"success": True, "data": market_book}, status_code=200)
        else:
            error = mt5App.last_error()
            return JSONResponse(content={"success": False, "message": error}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
