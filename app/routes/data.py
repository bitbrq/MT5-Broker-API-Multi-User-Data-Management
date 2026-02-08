from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.future import select
from datetime import datetime
from app.calculator import *
from app.middleware import *
from app.utils import *
from app.models import *

router = APIRouter()

# Info Tab 
@router.get("/info")
async def info(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username
    if role != "client": return JSONResponse(content={"success": False, "message": str(role) if role != "admin" else "Insufficient permissions"}, status_code=403)
    try:
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
@router.get("/chart")    
async def chart(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username
    if role != "client": return JSONResponse(content={"success": False, "message": str(role) if role != "admin" else "Insufficient permissions"}, status_code=403)
    try:
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
@router.get("/analytics")
async def analytics(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username
    if role != "client": return JSONResponse(content={"success": False, "message": str(role) if role != "admin" else "Insufficient permissions"}, status_code=403)
    try:
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


# Get Account Details
@router.get("/account_details")
async def account_details(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username
    if role != "client": return JSONResponse(content={"success": False, "message": str(role) if role != "admin" else "Insufficient permissions"}, status_code=403)
    try:
        cursor = connect_db(username)
        db_data = cursor.execute("SELECT * FROM account_details").fetchall()
        if db_data:
            columns = [column[0] for column in cursor.description]
            json_data = [dict(zip(columns, row)) for row in db_data]
            csv_data = create_csv(json_data)
            return JSONResponse(content={"success": True, "data": csv_data}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": "No account_details found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Get History Deals
@router.get("/history_deals")
async def history_deals(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username
    if role != "client": return JSONResponse(content={"success": False, "message": str(role) if role != "admin" else "Insufficient permissions"}, status_code=403)
    try:
        cursor = connect_db(username)
        db_data = cursor.execute("SELECT * FROM history_deals").fetchall()
        if db_data:
            columns = [column[0] for column in cursor.description]
            json_data = [dict(zip(columns, row)) for row in db_data]
            csv_data = create_csv(json_data)
            return JSONResponse(content={"success": True, "data": csv_data}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": "No history_deals found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Get History Orders
@router.get("/history_orders")
async def history_orders(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username
    if role != "client": return JSONResponse(content={"success": False, "message": str(role) if role != "admin" else "Insufficient permissions"}, status_code=403)
    try:
        cursor = connect_db(username)
        db_data = cursor.execute("SELECT * FROM history_orders").fetchall()
        if db_data:
            columns = [column[0] for column in cursor.description]
            json_data = [dict(zip(columns, row)) for row in db_data]
            csv_data = create_csv(json_data)
            return JSONResponse(content={"success": True, "data": csv_data}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": "No history_orders found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Get All Symbol Details
@router.get("/all_symbol_details")
async def all_symbol_details(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username
    if role != "client": return JSONResponse(content={"success": False, "message": str(role) if role != "admin" else "Insufficient permissions"}, status_code=403)
    try:
        cursor = connect_db("all_symbol_details")
        db_data = cursor.execute("SELECT * FROM all_symbol_details").fetchall()
        if db_data:
            columns = [column[0] for column in cursor.description]
            json_data = [dict(zip(columns, row)) for row in db_data]
            csv_data = create_csv(json_data)
            return JSONResponse(content={"success": True, "data": csv_data}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": "No all_symbol_details found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Get EURUSD Rates
@router.get("/eurusd_rates")
async def eurusd_rates(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username
    if role != "client": return JSONResponse(content={"success": False, "message": str(role) if role != "admin" else "Insufficient permissions"}, status_code=403)
    try:
        cursor = connect_db("eurusd_rates")
        
        # Get D1 data
        db_data_d1 = cursor.execute("SELECT * FROM eurusd_rates_d1").fetchall()
        columns_d1 = [column[0] for column in cursor.description] if db_data_d1 else []
        
        # Get M1 data
        db_data_m1 = cursor.execute("SELECT * FROM eurusd_rates_m1").fetchall()
        cursor.execute("SELECT * FROM eurusd_rates_m1 LIMIT 1")  # To get column names
        columns_m1 = [column[0] for column in cursor.description] if db_data_m1 else []
        
        if db_data_d1 or db_data_m1:
            json_data_d1 = [dict(zip(columns_d1, row)) for row in db_data_d1] if db_data_d1 else []
            json_data_m1 = [dict(zip(columns_m1, row)) for row in db_data_m1] if db_data_m1 else []
            combined_data = json_data_d1 + json_data_m1
            if combined_data:
                csv_content = create_csv(combined_data)          
                return JSONResponse(content={"success": True, "data": csv_content}, status_code=200)
            else:
                return JSONResponse(content={"success": False, "message": "No data available"}, status_code=404)
        else:
            return JSONResponse(content={"success": False, "message": "No eurusd_rates found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Get GBPUSD Rates
@router.get("/gbpusd_rates")
async def gbpusd_rates(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username
    if role != "client": return JSONResponse(content={"success": False, "message": str(role) if role != "admin" else "Insufficient permissions"}, status_code=403)
    try:
        cursor = connect_db("gbpusd_rates")
        
        # Get D1 data
        db_data_d1 = cursor.execute("SELECT * FROM gbpusd_rates_d1").fetchall()
        columns_d1 = [column[0] for column in cursor.description] if db_data_d1 else []
        
        # Get M1 data
        db_data_m1 = cursor.execute("SELECT * FROM gbpusd_rates_m1").fetchall()
        cursor.execute("SELECT * FROM gbpusd_rates_m1 LIMIT 1")  # To get column names
        columns_m1 = [column[0] for column in cursor.description] if db_data_m1 else []
        
        if db_data_d1 or db_data_m1:
            json_data_d1 = [dict(zip(columns_d1, row)) for row in db_data_d1] if db_data_d1 else []
            json_data_m1 = [dict(zip(columns_m1, row)) for row in db_data_m1] if db_data_m1 else []
            combined_data = json_data_d1 + json_data_m1
            if combined_data:
                csv_content = create_csv(combined_data)          
                return JSONResponse(content={"success": True, "data": csv_content}, status_code=200)
            else:
                return JSONResponse(content={"success": False, "message": "No data available"}, status_code=404)
        else:
            return JSONResponse(content={"success": False, "message": "No gbpusd_rates found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Get USDJPY Rates
@router.get("/usdjpy_rates")
async def usdjpy_rates(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username
    if role != "client": return JSONResponse(content={"success": False, "message": str(role) if role != "admin" else "Insufficient permissions"}, status_code=403)
    try:
        cursor = connect_db("usdjpy_rates")
        
        # Get D1 data
        db_data_d1 = cursor.execute("SELECT * FROM usdjpy_rates_d1").fetchall()
        columns_d1 = [column[0] for column in cursor.description] if db_data_d1 else []
        
        # Get M1 data
        db_data_m1 = cursor.execute("SELECT * FROM usdjpy_rates_m1").fetchall()
        cursor.execute("SELECT * FROM usdjpy_rates_m1 LIMIT 1")  # To get column names
        columns_m1 = [column[0] for column in cursor.description] if db_data_m1 else []
        
        if db_data_d1 or db_data_m1:
            json_data_d1 = [dict(zip(columns_d1, row)) for row in db_data_d1] if db_data_d1 else []
            json_data_m1 = [dict(zip(columns_m1, row)) for row in db_data_m1] if db_data_m1 else []
            combined_data = json_data_d1 + json_data_m1
            if combined_data:
                csv_content = create_csv(combined_data)          
                return JSONResponse(content={"success": True, "data": csv_content}, status_code=200)
            else:
                return JSONResponse(content={"success": False, "message": "No data available"}, status_code=404)
        else:
            return JSONResponse(content={"success": False, "message": "No usdjpy_rates found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Get EURJPY Rates
@router.get("/eurjpy_rates")
async def eurjpy_rates(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username
    if role != "client": return JSONResponse(content={"success": False, "message": str(role) if role != "admin" else "Insufficient permissions"}, status_code=403)
    try:
        cursor = connect_db("eurjpy_rates")
        
        # Get D1 data
        db_data_d1 = cursor.execute("SELECT * FROM eurjpy_rates_d1").fetchall()
        columns_d1 = [column[0] for column in cursor.description] if db_data_d1 else []
        
        # Get M1 data
        db_data_m1 = cursor.execute("SELECT * FROM eurjpy_rates_m1").fetchall()
        cursor.execute("SELECT * FROM eurjpy_rates_m1 LIMIT 1")  # To get column names
        columns_m1 = [column[0] for column in cursor.description] if db_data_m1 else []
        
        if db_data_d1 or db_data_m1:
            json_data_d1 = [dict(zip(columns_d1, row)) for row in db_data_d1] if db_data_d1 else []
            json_data_m1 = [dict(zip(columns_m1, row)) for row in db_data_m1] if db_data_m1 else []
            combined_data = json_data_d1 + json_data_m1
            if combined_data:
                csv_content = create_csv(combined_data)          
                return JSONResponse(content={"success": True, "data": csv_content}, status_code=200)
            else:
                return JSONResponse(content={"success": False, "message": "No data available"}, status_code=404)
        else:
            return JSONResponse(content={"success": False, "message": "No eurjpy_rates found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Get USDCHF Rates
@router.get("/usdchf_rates")
async def usdchf_rates(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username
    if role != "client": return JSONResponse(content={"success": False, "message": str(role) if role != "admin" else "Insufficient permissions"}, status_code=403)
    try:
        cursor = connect_db("usdchf_rates")
        
        # Get D1 data
        db_data_d1 = cursor.execute("SELECT * FROM usdchf_rates_d1").fetchall()
        columns_d1 = [column[0] for column in cursor.description] if db_data_d1 else []
        
        # Get M1 data
        db_data_m1 = cursor.execute("SELECT * FROM usdchf_rates_m1").fetchall()
        cursor.execute("SELECT * FROM usdchf_rates_m1 LIMIT 1")  # To get column names
        columns_m1 = [column[0] for column in cursor.description] if db_data_m1 else []
        
        if db_data_d1 or db_data_m1:
            json_data_d1 = [dict(zip(columns_d1, row)) for row in db_data_d1] if db_data_d1 else []
            json_data_m1 = [dict(zip(columns_m1, row)) for row in db_data_m1] if db_data_m1 else []
            combined_data = json_data_d1 + json_data_m1
            if combined_data:
                csv_content = create_csv(combined_data)          
                return JSONResponse(content={"success": True, "data": csv_content}, status_code=200)
            else:
                return JSONResponse(content={"success": False, "message": "No data available"}, status_code=404)
        else:
            return JSONResponse(content={"success": False, "message": "No usdchf_rates found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Get MyFX Data
@router.get("/myfx_data")
async def myfx_data(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username
    if role != "client": return JSONResponse(content={"success": False, "message": str(role) if role != "admin" else "Insufficient permissions"}, status_code=403)
    try:
        cursor = connect_db(username)
        db_data = cursor.execute("SELECT * FROM accounts").fetchall()
        if db_data:
            columns = [column[0] for column in cursor.description]
            json_data = [dict(zip(columns, row)) for row in db_data]
            csv_data = create_csv(json_data)
            return JSONResponse(content={"success": True, "data": csv_data}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": "No myfx_data found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()
