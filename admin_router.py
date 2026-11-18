from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from auth_utils import verify_admin_key
from database import create_key, create_custom_key, list_keys, toggle_key, get_key_info

router = APIRouter(prefix="/admin", dependencies=[Depends(verify_admin_key)])

class KeyCreate(BaseModel):
    label: str = "default"
    custom_key: Optional[str] = None

@router.post("/keys")
async def new_key(payload: KeyCreate):
    if payload.custom_key:
        if len(payload.custom_key) < 5:
            raise HTTPException(status_code=400, detail="Custom key must be at least 5 characters long")
        
        if get_key_info(payload.custom_key):
            raise HTTPException(status_code=400, detail="This custom key already exists")
            
        key = create_custom_key(payload.custom_key, payload.label)
        return {"status": "created", "key": key, "label": payload.label, "type": "custom"}
    else:
        key = create_key(payload.label)
        return {"status": "created", "key": key, "label": payload.label, "type": "random"}

@router.get("/keys")
async def all_keys():
    rows = list_keys()
    return {
        "total": len(rows),
        "keys": [
            {
                "id": r[0], "key": r[1], "label": r[2],
                "is_active": bool(r[3]),
                "created_at": r[4], "last_used_at": r[5]
            }
            for r in rows
        ]
    }

@router.patch("/keys/{key}/toggle")
async def toggle(key: str):
    info = get_key_info(key)
    if not info:
        raise HTTPException(404, "Key not found")
    new_state = not bool(info[3])
    toggle_key(key, new_state)
    return {"key": key, "is_active": new_state}
