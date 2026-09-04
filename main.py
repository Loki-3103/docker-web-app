from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
import sqlite3
import string
import random

app = FastAPI()

# ---- Database setup ----
def init_db():
    conn = sqlite3.connect("urls.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            short_code TEXT PRIMARY KEY,
            original_url TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---- Helper: generate a random short code ----
def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# ---- Request body schema ----
class URLRequest(BaseModel):
    url: str

# ---- Homepage (HTML + form) ----
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>URL Shortener</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #1e1e2f;
                color: #f0f0f0;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }
            h1 { color: #61dafb; }
            input, button {
                padding: 10px;
                margin: 10px;
                border-radius: 6px;
                border: none;
                font-size: 1em;
            }
            input { width: 300px; }
            button {
                background-color: #2496ed;
                color: white;
                cursor: pointer;
                font-weight: bold;
            }
            #result { margin-top: 20px; font-size: 1.1em; }
            a { color: #61dafb; }
        </style>
    </head>
    <body>
        <h1>URL Shortener</h1>
        <div>
            <input type="text" id="urlInput" placeholder="Paste your long URL here">
            <button onclick="shortenUrl()">Shorten</button>
        </div>
        <div id="result"></div>

        <script>
            async function shortenUrl() {
                const url = document.getElementById("urlInput").value;
                if (!url) return alert("Please enter a URL");

                const response = await fetch("/shorten", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url: url })
                });
                const data = await response.json();

                if (data.short_url) {
                    const fullLink = window.location.origin + data.short_url;
                    document.getElementById("result").innerHTML =
                        `Short URL: <a href="${fullLink}" target="_blank">${fullLink}</a>`;
                } else {
                    document.getElementById("result").innerHTML = "Something went wrong.";
                }
            }
        </script>
    </body>
    </html>
    """

# ---- Create a short URL ----
@app.post("/shorten")
def shorten_url(request: URLRequest):
    conn = sqlite3.connect("urls.db")
    short_code = generate_short_code()

    # keep generating until we find a code that isn't already used
    while conn.execute("SELECT 1 FROM urls WHERE short_code = ?", (short_code,)).fetchone():
        short_code = generate_short_code()

    conn.execute(
        "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
        (short_code, request.url)
    )
    conn.commit()
    conn.close()

    return {"short_code": short_code, "short_url": f"/{short_code}"}

# ---- Redirect short code to original URL ----
@app.get("/{short_code}")
def redirect_to_url(short_code: str):
    conn = sqlite3.connect("urls.db")
    result = conn.execute(
        "SELECT original_url FROM urls WHERE short_code = ?", (short_code,)
    ).fetchone()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Short URL not found")

    return RedirectResponse(url=result[0])

# ---- Health check ----
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Service is healthy"}