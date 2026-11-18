# ============================================================
# main.py - Customer Search API
# Hugging Face Dataset + DuckDB Real Search + Web UI + Custom URL
# ============================================================

import os
import duckdb
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from huggingface_hub import HfApi, HfFileSystem
import pyarrow.parquet as pq

# ---------- अपनी फाइलों से import ----------
from database import init_db, get_key_info, update_last_used
from auth_utils import get_current_api_key
from admin_router import router as admin_router


# ============================================================
# 1. ऐप बनाओ और setup करो
# ============================================================
app = FastAPI(
    title="Customer Search API",
    description="Hugging Face dataset real-time search",
    version="4.1.0"
)

init_db()
app.include_router(admin_router)

HF_TOKEN = os.environ.get("HF_TOKEN")
REPO_ID = "Gauravbeniwal0001/Numberinfoapibygauravbeniwal"

api = HfApi(token=HF_TOKEN)
fs = HfFileSystem(token=HF_TOKEN)


# ============================================================
# 🌐 2. वेब इंटरफ़ेस (Frontend UI) - रूट पेज पर
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def home():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Customer Search</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; padding-top: 50px; margin: 0; }
            .container { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 90%; max-width: 500px; }
            h2 { text-align: center; color: #333; margin-bottom: 20px; }
            .search-box { display: flex; gap: 10px; margin-bottom: 20px; }
            input { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 8px; font-size: 16px; outline: none; }
            input:focus { border-color: #007bff; }
            button { padding: 12px 20px; background-color: #007bff; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; font-weight: bold; }
            button:hover { background-color: #0056b3; }
            .result { margin-top: 20px; }
            .card { background: #f9f9f9; border-left: 5px solid #007bff; padding: 15px; margin-bottom: 10px; border-radius: 5px; }
            .card p { margin: 5px 0; color: #555; font-size: 14px; }
            .card strong { color: #333; }
            .error { color: red; text-align: center; font-weight: bold; }
            .loader { display: none; text-align: center; color: #007bff; margin-top: 10px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🔍 Number Search</h2>
            <div class="search-box">
                <input type="text" id="phone" placeholder="Enter 10 digit number" maxlength="10">
                <button onclick="searchNumber()">Search</button>
            </div>
            <div id="loader" class="loader">Searching... (May take 1-2 minutes)</div>
            <div id="result" class="result"></div>
        </div>

        <script>
            async function searchNumber() {
                const phone = document.getElementById('phone').value;
                const resultDiv = document.getElementById('result');
                const loader = document.getElementById('loader');
                
                if(phone.length < 10) {
                    alert("Please enter a valid 10-digit number");
                    return;
                }

                resultDiv.innerHTML = '';
                loader.style.display = 'block';

                try {
                    // यहाँ आपकी नई API Key 'VIVEK' डाल दी गई है
                    const apiKey = "VIVEK"; 
                    
                    // नया URL Format: /num/{phone}?api_key={apiKey}
                    const response = await fetch(`/num/${phone}?api_key=${apiKey}`, {
                        method: 'GET'
                    });

                    const data = await response.json();
                    loader.style.display = 'none';

                    if (response.status !== 200) {
                        resultDiv.innerHTML = `<p class="error">Error: ${data.detail}</p>`;
                        return;
                    }

                    if (data.total_found === 0) {
                        resultDiv.innerHTML = `<p class="error">No records found for this number.</p>`;
                        return;
                    }

                    let html = `<h3>Results Found: ${data.total_found}</h3>`;
                    data.results.forEach(res => {
                        html += `
                        <div class="card">
                            <p><strong>Name:</strong> ${res.name || 'N/A'}</p>
                            <p><strong>Phone:</strong> ${res.phoneNumber}</p>
                            <p><strong>District:</strong> ${res.district || 'N/A'}</p>
                            <p><strong>State:</strong> ${res.state || 'N/A'}</p>
                            <p><strong>Pincode:</strong> ${res.pincode || 'N/A'}</p>
                        </div>`;
                    });
                    resultDiv.innerHTML = html;

                } catch (error) {
                    loader.style.display = 'none';
                    resultDiv.innerHTML = `<p class="error">Server Timeout or Error. Please try again.</p>`;
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content


# ============================================================
# 3. नया Endpoint: /num/{phone}?api_key=YOUR_KEY
# ============================================================
@app.get("/num/{phone}")
async def search_by_path(
    phone: str, 
    api_key: str = Query(..., description="API Key for authentication")
):
    # API Key को Query Parameter (?api_key=xyz) से चेक करें
    row = get_key_info(api_key)
    if not row:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    if not row[3]: # is_active (0 या 1)
        raise HTTPException(status_code=403, detail="API Key is disabled")
    update_last_used(api_key)

    conn = None
    try:
        conn = duckdb.connect()
        conn.execute("INSTALL httpfs;")
        conn.execute("LOAD httpfs;")
        
        if HF_TOKEN:
            conn.execute(f"CREATE SECRET (TYPE HUGGINGFACE, TOKEN '{HF_TOKEN}');")

        # सभी 46 फाइलों में सर्च
        query = f"""
            SELECT name, phoneNumber, district, state, pincode
            FROM read_parquet('hf://datasets/{REPO_ID}/production_indexes/*.parquet')
            WHERE phoneNumber = ?
            LIMIT 10
        """
        
        results = conn.execute(query, [phone]).fetchall()

        if not results:
            return {"status": "success", "query": phone, "total_found": 0, "results": []}

        formatted_results = []
        for r in results:
            formatted_results.append({
                "name": r[0], "phoneNumber": r[1], "district": r[2], "state": r[3], "pincode": r[4]
            })

        return {"status": "success", "query": phone, "total_found": len(formatted_results), "results": formatted_results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
    finally:
        if conn: conn.close()


# ============================================================
# 4. पुराना Search Endpoint (Header Auth के लिए)
# ============================================================
@app.get("/search")
async def search_header_auth(
    phone: str = Query(..., description="Phone number to search"),
    api_key: str = Depends(get_current_api_key)
):
    conn = None
    try:
        conn = duckdb.connect()
        conn.execute("INSTALL httpfs;")
        conn.execute("LOAD httpfs;")
        
        if HF_TOKEN:
            conn.execute(f"CREATE SECRET (TYPE HUGGINGFACE, TOKEN '{HF_TOKEN}');")

        query = f"""
            SELECT name, phoneNumber, district, state, pincode
            FROM read_parquet('hf://datasets/{REPO_ID}/production_indexes/*.parquet')
            WHERE phoneNumber = ?
            LIMIT 10
        """
        
        results = conn.execute(query, [phone]).fetchall()

        if not results:
            return {"status": "success", "query": phone, "total_found": 0, "results": []}

        formatted_results = []
        for r in results:
            formatted_results.append({
                "name": r[0], "phoneNumber": r[1], "district": r[2], "state": r[3], "pincode": r[4]
            })

        return {"status": "success", "query": phone, "total_found": len(formatted_results), "results": formatted_results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
    finally:
        if conn: conn.close()


# ============================================================
# 5. Health Check
# ============================================================
@app.get("/health")
async def health():
    return {"status": "healthy", "hf_token_configured": HF_TOKEN is not None}
