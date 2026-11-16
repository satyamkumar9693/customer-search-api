
from fastapi import FastAPI, HTTPException
from huggingface_hub import HfApi
import os

app = FastAPI(
    title="Numberinfo Dataset API",
    version="1.0"
)

REPO_ID = "Gauravbeniwal0001/Numberinfoapibygauravbeniwal"
TOKEN = os.getenv("HF_TOKEN")

@app.get("/")
def home():
    return {
        "message": "Hugging Face Dataset API is running"
    }

@app.get("/health")
def health():
    return {"status": "OK"}

@app.get("/dataset/info")
def dataset_info():
    try:
        api = HfApi(token=TOKEN)

        info = api.dataset_info(
            repo_id=REPO_ID
        )

        return {
            "status": "connected",
            "repository": REPO_ID,
            "private": info.private,
            "sha": info.sha
        }

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail="Hugging Face connection failed"
        )

@app.get("/dataset/files")
def dataset_files():
    try:
        api = HfApi(token=TOKEN)

        files = api.list_repo_files(
            repo_id=REPO_ID,
            repo_type="dataset"
        )

        return {
            "status": "connected",
            "total_files": len(files),
            "files": files
        }

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Could not read dataset file list"
        )
