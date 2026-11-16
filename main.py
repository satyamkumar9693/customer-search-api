
from fastapi import FastAPI

app = FastAPI(title="Customer Search API Demo")

# Dummy data only — real customer records nahi
demo_data = [
    {"id": "C001", "name": "Demo User One", "city": "Patna"},
    {"id": "C002", "name": "Demo User Two", "city": "Gaya"},
    {"id": "C003", "name": "Demo User Three", "city": "Delhi"}
]

@app.get("/")
def home():
    return {"message": "API is running"}

@app.get("/health")
def health():
    return {"status": "OK"}

@app.get("/demo/search")
def search(city: str):
    results = [
        item for item in demo_data
        if item["city"].lower() == city.lower()
    ]
    return {"results": results}

