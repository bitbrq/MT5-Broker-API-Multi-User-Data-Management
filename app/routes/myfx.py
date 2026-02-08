from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.middleware import *
from app.utils import *
from app.models import *
import requests
import json

router = APIRouter()

# MYFX Account Login (OK)
@router.post("/myfx_login")
async def mt5_login(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return JSONResponse(content={"success": False, "message": "Missing username, password"}, status_code=400)

        cursor = connect_db("users")
        result = cursor.execute(f"SELECT * FROM users WHERE username = '{username}'").fetchall()

        if not result:
            return JSONResponse(content={"success": False, "message": "User not found"}, status_code=404)

        user = result[0]

        if decrypt_password(user[1]) != password:
            return JSONResponse(content={"success": False, "message": "Incorrect password"}, status_code=401)
        
        myfxbook_api_url = "https://www.myfxbook.com/api/login.json"
        params = {"email": username, "password": password}
        response = requests.get(myfxbook_api_url, params=params)
        myfx_response = response.json()
        session = myfx_response.get("session")
        if session:
            return JSONResponse(content={"success": True, "session": session}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "message": "Error in Accessing MYFXBook"}, status_code=400)

    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Internal server error: {str(e)}"}, status_code=500)


# MYFX Account info (Verified)
@router.post('/myfx_data')
async def account_details(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  
        return role_username
    
    role, username = role_username
    if role != "admin":  
        return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)

    try:
        username = data.get('username')
        session = data.get('session')
        myfxbook_api_url = "https://www.myfxbook.com/api/get-my-accounts.json"
        params = {"session": session}
        response = requests.get(myfxbook_api_url, params=params)
        myfx_response = response.json()

        accounts = myfx_response.get("accounts", [])
        if accounts:
            formatted_accounts = []
            for account in accounts:
                if isinstance(account.get("server"), dict):  
                    account["server"] = json.dumps(account["server"])
                formatted_accounts.append(account)
            for account in formatted_accounts:
                update_database(username, "accounts", account)
        return JSONResponse(content={"success": True, "message": "MyFx Book Data updated Successfully"}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)

    return JSONResponse(content={"success": True, "message": "Data updated successfully"}, status_code=200)
