from fastapi import APIRouter, Depends
from cryptography.fernet import Fernet, InvalidToken
from fastapi.responses import JSONResponse
from app.middleware import *
from app.utils import *
from app.config import AES_KEY
import importlib

router = APIRouter()

# Login
@router.post("/login")
async def login(data: dict):
    try:
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            return JSONResponse(content={"success": False, "message": "Missing username, password"}, status_code=400)

        cursor = connect_db("users")
        result = cursor.execute(f"SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if not result:
            return JSONResponse(content={"success": False, "message": "User not found"}, status_code=404)

        if decrypt_password(result[1]) != password:
            return JSONResponse(content={"success": False, "message": "Incorrect password"}, status_code=401)

        userdata = {"username": result[0], "role": result[3]}
        token = create_jwt_token(userdata)

        return JSONResponse(content={"success": True, "token": token, "role": result[3]}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Internal server error: {str(e)}"}, status_code=500)
    finally:
        cursor.close()

# Logout
@router.post("/logout")
async def logout():
    return JSONResponse(content={"success": True, "message": "Logged out successfully"}, status_code=200)

# Add User (OK)
@router.post("/add_user")
async def add_user(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username 
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    # Validate input data
    username = data.get('username')
    password = data.get('password')
    server = data.get('server')
    user_role = data.get('role')
    is_active = data.get('is_active')

    if not all([username, password, server, user_role, is_active is not None]):
        return JSONResponse(content={"success": False, "message": "Missing required fields"}, status_code=400)

    try:
        cursor = connect_db("users", readonly=False)
        
        # Use parameterized queries to prevent SQL injection
        result = cursor.execute(f"SELECT * FROM users WHERE username = '{username}'").fetchall()
        if result:
            return JSONResponse(content={"success": False, "message": "Username already exists"}, status_code=409)
        # Insert new user
        cursor.execute("""
            INSERT INTO users (username, password, server, role, is_active) 
            VALUES (?, ?, ?, ?, ?)
        """, (username, encrypt_password(password), server, user_role, is_active))
        
        # Create a new database for the user
        db_manager.create_new_database(f"{username}.db")
        conn = db_manager.get_db_connection(f"{username}.db")
        
        # Dynamically import the models module and call the function
        models_module = importlib.import_module('app.models')
        function_name = 'myfx_data' if server == "myfxbook" else 'client'

        # Ensure that the function exists before calling it
        if hasattr(models_module, function_name):
            func = getattr(models_module, function_name)
            func(conn)
        db_manager.explicit_save()
        
        return JSONResponse(content={"success": True, "message": "User  saved successfully and database created"}, status_code=201)

    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()
    
# Update Users (OK)
@router.post("/update_user")
async def update_user(data: dict, role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username 
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        username = data.get('username')
        password = data.get('password')
        server = data.get('server')
        user_role = data.get('role')
        is_active = data.get('is_active')

        if not username or not password or not server or not user_role or is_active is None:
            return JSONResponse(content={"success": False, "message": "Missing required fields"}, status_code=400)

        cursor = connect_db("users", readonly=False)
        result = cursor.execute(f"SELECT * FROM users WHERE username = '{username}'").fetchall()
        
        if not result:
            return JSONResponse(content={"success": False, "message": "User not found"}, status_code=404)
        try:
            fernet = Fernet(AES_KEY.encode())
            fernet.decrypt(password.encode()) 
            verified_password = password
        except InvalidToken:
            verified_password = fernet.encrypt(password.encode()).decode() 
        cursor.execute(f"""
            UPDATE users SET 
            password = '{verified_password}', 
            server = '{server}', 
            role = '{user_role}', 
            is_active = {is_active}
            WHERE username = '{username}'
        """)
        cursor.connection.commit()
        return JSONResponse(content={"success": True, "message": "User updated successfully"}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

# Current Users (OK)
@router.post("/current_users")
async def current_users(role_username: tuple = Depends(jwt_middleware)):
    if isinstance(role_username, JSONResponse):  return role_username
    role, username = role_username 
    if role != "admin": return JSONResponse(content={"success": False, "message": str(role) if role != "client" else "Insufficient permissions"}, status_code=403)
    try:
        cursor = connect_db("users")
        result = cursor.execute("SELECT * FROM users WHERE username != 'mrbb'").fetchall()
        user_data = [{
            'username': user[0],
            'password': user[1],
            'server': user[2],
            'role': user[3],
            'is_active': user[4]
        } for user in result]

        if user_data:
            return JSONResponse(content={"success": True, "data": user_data}, status_code=200)
        return JSONResponse(content={"success": False, "message": "No User Data found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
    finally:
        cursor.close()

@router.post("/explicit_save")
async def explicit_save(role_username: tuple = Depends(jwt_middleware)):
    try:
       db_manager.explicit_save()
       return JSONResponse(content={"success": True, "message": "Database save completed."}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
