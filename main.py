
from fastapi import FastAPI, HTTPException
from huggingface_hub import HfApi, hf_hub_url
import requests
import os

app = FastAPI(
    title="Dataset Inspector API",
    version="2.0"
)

REPO_ID = "Gauravbeniwal0001/Numberinfoapibygauravbeniwal"
TOKEN = os.getenv("HF_TOKEN")

@app.get("/")
def home():
    return {"status": "online"}

@app.get("/health")
def health():
    return {"status": "OK"}

@app.get("/dataset/info")
def dataset_info():
    try:
        api = HfApi(token=TOKEN)
        info = api.dataset_info(repo_id=REPO_ID)

        return {
            "status": "connected",
            "repository": REPO_ID,
            "private": info.private,
            "sha": info.sha
        }
    except Exception:
        raise HTTPException(502, "Hugging Face connection failed")

@app.get("/dataset/index-metadata")
def index_metadata():
    filename = "production_indexes/idx_prod_p1_6.parquet"

    try:
        api = HfApi(token=TOKEN)

        files = api.get_paths_info(
            repo_id=REPO_ID,
            paths=[filename],
            repo_type="dataset"
        )

        if not files:
            raise HTTPException(404, "File not found")

        url = hf_hub_url(
            repo_id=REPO_ID,
            filename=filename,
            repo_type="dataset"
        )

        headers = {}
        if TOKEN:
            headers["Authorization"] = f"Bearer {TOKEN}"

        response = requests.head(
            url,
            headers=headers,
            allow_redirects=True,
            timeout=30
        )
        response.raise_for_status()

        return {
            "status": "success",
            "filename": filename,
            "size_bytes": files[0].size,
            "content_type": response.headers.get("Content-Type"),
            "file_access": "verified",
            "note": "Metadata checked; file contents not downloaded"
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Could not inspect index metadata")
        
