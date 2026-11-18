# ============================================================
# main.py - Customer Search API
# Hugging Face Dataset + DuckDB Real Search + API Key System
# ============================================================

import os
import duckdb
from fastapi import FastAPI, HTTPException, Depends, Query
from huggingface_hub import HfApi, HfFileSystem
import pyarrow.parquet as pq

# ---------- अपनी नई फाइलों से import ----------
from database import init_db
from auth_utils import get_current_api_key
from admin_router import router as admin_router


# ============================================================
# 1. ऐप बनाओ और setup करो
# ============================================================
app = FastAPI(
    title="Customer Search API",
    description="Hugging Face dataset real-time search using DuckDB",
    version="3.2.0"
)

# ---------- Database tables बनाओ (startup पर) ----------
init_db()

# ---------- Admin routes जोड़ो (/admin/... सारे endpoints) ----------
app.include_router(admin_router)

# ---------- Hugging Face setup ----------
HF_TOKEN = os.environ.get("HF_TOKEN")
REPO_ID = "Gauravbeniwal0001/Numberinfoapibygauravbeniwal"

api = HfApi(token=HF_TOKEN)
fs = HfFileSystem(token=HF_TOKEN)


# ============================================================
# 2. पुराने endpoints (जो पहले से काम कर रहे हैं)
# ============================================================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Customer Search API is running",
        "version": "3.2.0"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "hf_token_configured": HF_TOKEN is not None
    }

@app.get("/dataset/info")
async def dataset_info():
    try:
        info = api.dataset_info(REPO_ID)
        return {
            "status": "success",
            "repo_id": REPO_ID,
            "sha": info.sha,
            "last_modified": str(info.lastModified)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dataset/files")
async def list_files():
    try:
        files = api.list_repo_files(repo_id=REPO_ID, repo_type="dataset")
        return {
            "status": "success",
            "total_files": len(files),
            "files": files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dataset/file-info")
async def file_info(filename: str):
    try:
        info = api.dataset_info(REPO_ID)
        for sibling in info.siblings:
            if sibling.rfilename == filename:
                return {
                    "status": "success",
                    "filename": filename,
                    "size_bytes": sibling.size,
                    "size_gb": round(sibling.size / (1024**3), 2) if sibling.size else None
                }
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 3. Parquet Footer (बिना file download किए schema देखना)
# ============================================================

@app.get("/dataset/parquet-footer")
async def parquet_footer(filename: str):
    path = f"datasets/{REPO_ID}/{filename}"
    try:
        with fs.open(path, "rb") as f:
            pf = pq.ParquetFile(f)
            schema = pf.schema_arrow
            metadata = pf.metadata
            return {
                "status": "success",
                "filename": filename,
                "num_rows": metadata.num_rows,
                "num_row_groups": metadata.num_row_groups,
                "num_columns": len(schema.names),
                "schema": [{"name": fld.name, "type": str(fld.type)} for fld in schema]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Footer read error: {str(e)}")


# ============================================================
# 4. असली सर्च (DuckDB Real Data Search - ALL FILES)
# ============================================================

@app.get("/search")
async def search(
    phone: str = Query(..., description="Phone number to search (e.g. 9876543210)"),
    api_key: str = Depends(get_current_api_key)
):
    conn = None
    try:
        conn = duckdb.connect()
        conn.execute("INSTALL httpfs;")
        conn.execute("LOAD httpfs;")
        
        if HF_TOKEN:
            conn.execute(f"CREATE SECRET (TYPE HUGGINGFACE, TOKEN '{HF_TOKEN}');")

        # यहाँ * लगाया गया है ताकि सारी 46 फाइलों में एक साथ सर्च हो
        query = f"""
            SELECT name, phoneNumber, district, state, pincode
            FROM read_parquet('hf://datasets/{REPO_ID}/production_indexes/*.parquet')
            WHERE phoneNumber = ?
            LIMIT 10
        """
        
        results = conn.execute(query, [phone]).fetchall()

        if not results:
            return {
                "status": "success",
                "query": phone,
                "message": "No records found for this phone number in any index file.",
                "total_found": 0,
                "results": []
            }

        formatted_results = []
        for row in results:
            formatted_results.append({
                "name": row[0],
                "phoneNumber": row[1],
                "district": row[2],
                "state": row[3],
                "pincode": row[4]
            })

        return {
            "status": "success",
            "query": phone,
            "total_found": len(formatted_results),
            "results": formatted_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
    
    finally:
        if conn:
            conn.close()
