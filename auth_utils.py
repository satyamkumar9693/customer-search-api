# auth_utils.py
import os
from fastapi import Header, HTTPException
from database import get_key_info, update_last_used

ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "change-me-in-production")

async def get_current_api_key(x_api_key: str = Header(...)):
    row = get_key_info(x_api_key)
    if not row:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    if not row[3]:  # is_active column index 3 पर है
        raise HTTPException(status_code=403, detail="API Key is disabled")
    update_last_used(x_api_key)
    return x_api_key

async def verify_admin_key(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Admin access required")
    return True
