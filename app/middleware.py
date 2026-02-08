from fastapi import Request, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from app.utils import decode_jwt_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def jwt_middleware(request: Request):
    token = request.headers.get("Authorization")

    if not token:
        return JSONResponse(content={"success": False, "message": "Not authorized"}, status_code=401)

    userdata = decode_jwt_token(token)

    if userdata in ["Token has expired", "Invalid token", "Invalid token structure"]:
        return JSONResponse(content={"success": False, "message": userdata}, status_code=401)

    role = userdata.get("role") if isinstance(userdata, dict) else None
    username = userdata.get("username") if isinstance(userdata, dict) else None

    if role is None or username is None:
        return JSONResponse(content={"success": False, "message": "Could not validate credentials"}, status_code=401)

    return role, username