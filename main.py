import os
import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from huggingface_hub import HfApi, HfFileSystem

from database import init_db
from admin_router import router as admin_router

app = FastAPI(title="Customer Search API", version="5.0.0")
init_db()
app.include_router(admin_router)

HF_TOKEN = os.environ.get("HF_TOKEN")
REPO_ID = "Gauravbeniwal0001/Numberinfoapibygauravbeniwal"
api = HfApi(token=HF_TOKEN)
fs = HfFileSystem(token=HF_TOKEN)

# ============================================================
# 🌐 वेबसाइट (Frontend UI)
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Customer Search</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f4f7f6; display: flex; justify-content: center; padding-top: 50px; margin: 0; }
            .container { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 90%; max-width: 500px; }
            h2 { text-align: center; color: #333; }
            .search-box { display: flex; gap: 10px; margin-bottom: 20px; }
            input { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 8px; font-size: 16px; }
            button { padding: 12px 20px; background: #007bff; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; font-weight: bold; }
            .card { background: #f9f9f9; border-left: 5px solid #007bff; padding: 15px; margin-bottom: 10px; border-radius: 5px; }
            .error { color: red; text-align: center; font-weight: bold; }
            .loader { display: none; text-align: center; color: #007bff; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🔍 Number Search</h2>
            <div class="search-box">
                <input type="text" id="phone" placeholder="Enter 10 digit number" maxlength="10">
                <button onclick="searchNumber()">Search</button>
            </div>
            <div id="loader" class="loader">Searching... (Wait 1-2 minutes)</div>
            <div id="result" class="result"></div>
        </div>
        <script>
            async function searchNumber() {
                const phone = document.getElementById('phone').value;
                const resultDiv = document.getElementById('result');
                const loader = document.getElementById('loader');
                
                if(phone.length < 10) { alert("Enter 10 digit number"); return; }

                resultDiv.innerHTML = '';
                loader.style.display = 'block';

                try {
                    const response = await fetch(`/num/${phone}?api_key=VIVEK`);
                    const data = await response.json();
                    loader.style.display = 'none';

                    if (response.status !== 200) {
                        resultDiv.innerHTML = `<p class="error">Error: ${data.detail}</p>`;
                        return;
                    }
                    if (data.total_found === 0) {
                        resultDiv.innerHTML = `<p class="error">No records found.</p>`;
                        return;
                    }
                    let html = `<h3>Results: ${data.total_found}</h3>`;
                    data.results.forEach(res => {
                        html += `<div class="card">
                            <p><strong>Name:</strong> ${res.name || 'N/A'}</p>
                            <p><strong>Phone:</strong> ${res.phoneNumber}</p>
                            <p><strong>District:</strong> ${res.district || 'N/A'}</p>
                        </div>`;
                    });
                    resultDiv.innerHTML = html;
                } catch (error) {
                    loader.style.display = 'none';
                    resultDiv.innerHTML = `<p class="error">Server Timeout. Please try again.</p>`;
                }
            }
        </script>
    </body>
    </html>
    """

# ============================================================
# 🔍 सर्च एंडपॉइंट (VIVEK Key Hardcoded)
# ============================================================
@app.get("/num/{phone}")
async def search_by_path(phone: str, api_key: str = Query(...)):
    # सीधे VIVEK की चेक करो, डेटाबेस में जाने की ज़रूरत नहीं
    if api_key != "VIVEK":
        raise HTTPException(status_code=401, detail="Invalid API Key. Use VIVEK")

    conn = None
    try:
        conn = duckdb.connect()
        conn.execute("INSTALL httpfs;")
        conn.execute("LOAD httpfs;")
        if HF_TOKEN:
            conn.execute(f"CREATE SECRET (TYPE HUGGINGFACE, TOKEN '{HF_TOKEN}');")

        # फिलहाल हम सिर्फ 1 बड़ी फाइल (part1.parquet) में सर्च कर रहे हैं 
        # ताकि Render का फ्री सर्वर टाइमआउट न हो
        query = f"""
            SELECT name, phoneNumber, district, state, pincode
            FROM read_parquet('hf://datasets/{REPO_ID}/part1.parquet')
            WHERE phoneNumber = ?
            LIMIT 10
        """
        results = conn.execute(query, [phone]).fetchall()

        if not results:
            return {"status": "success", "query": phone, "total_found": 0, "results": []}

        formatted = [{"name": r[0], "phoneNumber": r[1], "district": r[2], "state": r[3], "pincode": r[4]} for r in results]
        return {"status": "success", "query": phone, "total_found": len(formatted), "results": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn: conn.close()

@app.get("/health")
async def health():
    return {"status": "healthy"}
