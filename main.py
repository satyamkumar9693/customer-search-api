
from fastapi import FastAPI, HTTPException
from huggingface_hub import HfApi
import os

app = FastAPI(
    title="Numberinfo Dataset API",
    version="1.1"
)

REPO_ID = "Gauravbeniwal0001/Numberinfoapibygauravbeniwal"
TOKEN = os.getenv("HF_TOKEN")


def get_hf_api():
    return HfApi(token=TOKEN)


@app.get("/")
def home():
    return {
        "message": "Hugging Face Dataset API is running",
        "status": "online"
    }


@app.get("/health")
def health():
    return {"status": "OK"}


@app.get("/dataset/info")
def dataset_info():
    try:
        api = get_hf_api()

        info = api.dataset_info(
            repo_id=REPO_ID
        )

        return {
            "status": "connected",
            "repository": REPO_ID,
            "private": info.private,
            "sha": info.sha
        }

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Hugging Face connection failed"
        )


@app.get("/dataset/files")
def dataset_files():
    try:
        api = get_hf_api()

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


@app.get("/dataset/file-info")
def dataset_file_info():
    try:
        api = get_hf_api()

        paths = [
            "part1.parquet",
            "part2a.parquet",
            "part2b_new.parquet",
            "production_indexes/idx_prod_p1_6.parquet"
        ]

        info = api.get_paths_info(
            repo_id=REPO_ID,
            paths=paths,
            repo_type="dataset"
        )

        return {
            "status": "success",
            "files": [
                {
                    "name": item.path,
                    "size_bytes": item.size
                }
                for item in info
            ]
        }

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Could not inspect dataset files"
        )
