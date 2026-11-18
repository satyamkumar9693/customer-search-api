# ============================================================
# main.py - Customer Search API
# Hugging Face Dataset + API Key System + Admin Panel
# ============================================================

import os
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
    description="Hugging Face dataset search with API key protection",
    version="2.0.0"
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
    """Root endpoint - API चालू है या नहीं"""
    return {
        "status": "ok",
        "message": "Customer Search API is running",
        "version": "2.0.0"
    }


@app.get("/health")
async def health():
    """Health check - Render और monitoring के लिए"""
    return {
        "status": "healthy",
        "hf_token_configured": HF_TOKEN is not None
    }


@app.get("/dataset/info")
async def dataset_info():
    """Hugging Face repository की जानकारी (SHA, files count आदि)"""
    try:
        info = api.dataset_info(REPO_ID)
        return {
            "status": "success",
            "repo_id": REPO_ID,
            "sha": info.sha,
            "last_modified": str(info.lastModified),
            "private": info.private,
            "downloads": info.downloads,
            "likes": info.likes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dataset/files")
async def list_files():
    """Dataset में कुल कितनी फाइलें हैं"""
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
    """किसी एक फाइल का size और type"""
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dataset/index-metadata")
async def index_metadata(
    filename: str = "production_indexes/idx_prod_p1_6.parquet"
):
    """
    production_indexes की किसी फाइल का metadata check
    (पूरी फाइल download नहीं होती, सिर्फ headers)
    """
    try:
        info = api.dataset_info(REPO_ID)
        for sibling in info.siblings:
            if sibling.rfilename == filename:
                return {
                    "status": "success",
                    "filename": filename,
                    "size_bytes": sibling.size,
                    "content_type": "application/octet-stream",
                    "file_access": "verified",
                    "note": "Metadata checked; file contents not downloaded"
                }
        raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 3. नया endpoint: Parquet Footer (बिना file download किए)
# ============================================================

@app.get("/dataset/parquet-footer")
async def parquet_footer(filename: str):
    """
    किसी भी Parquet फाइल का schema, rows, column stats पढ़ता है
    बिना पूरी file download किए (सिर्फ footer पढ़ता है)।

    यह सबसे ज़रूरी endpoint है - इससे पता चलेगा कि
    production_indexes असली index है या ordinary Parquet।
    """
    path = f"datasets/{REPO_ID}/{filename}"
    try:
        # HfFileSystem के ज़रिए remote file खोलो
        with fs.open(path, "rb") as f:
            pf = pq.ParquetFile(f)
            schema = pf.schema_arrow
            metadata = pf.metadata

            # Column statistics (min/max) निकालो अगर उपलब्ध हों
            column_stats = {}
            if metadata.num_row_groups > 0:
                first_rg = metadata.row_group(0)
                for i in range(len(schema.names)):
                    col = first_rg.column(i)
                    stats = col.statistics
                    column_stats[schema.names[i]] = {
                        "min": str(stats.min) if stats and stats.min is not None else None,
                        "max": str(stats.max) if stats and stats.max is not None else None,
                        "null_count": stats.null_count if stats else None,
                    }

            return {
                "status": "success",
                "filename": filename,
                "num_rows": metadata.num_rows,
                "num_row_groups": metadata.num_row_groups,
                "num_columns": len(schema.names),
                "schema": [
                    {"name": fld.name, "type": str(fld.type)}
                    for fld in schema
                ],
                "column_stats": column_stats
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Footer read error: {str(e)}")


# ============================================================
# 4. नया endpoint: Search (अभी सिर्फ API key check)
# ============================================================

@app.get("/search")
async def search(
    phone: str = Query(..., description="Phone number to search"),
    api_key: str = Depends(get_current_api_key)
):
    """
    असली search endpoint - API key से protect है।
    अभी सिर्फ authorization test करता है।
    DuckDB search अगले step में जोड़ेंगे।
    """
    return {
        "status": "authorized",
        "query": phone,
        "api_key_used": api_key[:8] + "***",  # सिर्फ पहले 8 chars दिखाओ
        "note": "DuckDB search will be added in next step"
    }
