# llm-api/app.py
import os
import time
import json
import threading
from typing import AsyncGenerator

import requests
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434/api/generate")
API_KEY = os.environ.get("API_KEY", "please-change-me")
RATE_LIMIT_CAPACITY = int(os.environ.get("RATE_LIMIT_CAPACITY", "10"))
RATE_LIMIT_REFILL_SECONDS = int(os.environ.get("RATE_LIMIT_REFILL_SECONDS", "60"))
RATE_LIMIT_TOKENS_PER_REFILL = int(os.environ.get("RATE_LIMIT_TOKENS_PER_REFILL", "10"))

app = FastAPI(title="Llama Ollama Proxy (CPU) with Search")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # your frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # allow GET, POST, etc.
    allow_headers=["*"],  # allow custom headers like X-API-KEY
)

logging.basicConfig(level=logging.INFO)

# ============================
# TOKEN BUCKET RATE LIMITER
# ============================
class TokenBucket:
    def __init__(self, capacity: int, refill_tokens: int, refill_period: int):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_tokens = refill_tokens
        self.refill_period = refill_period
        self.lock = threading.Lock()
        self.last_refill = time.time()

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        if elapsed >= self.refill_period:
            with self.lock:
                periods = int(elapsed // self.refill_period)
                self.tokens = min(self.capacity, self.tokens + periods * self.refill_tokens)
                self.last_refill += periods * self.refill_period

    def consume(self, amount: int = 1) -> bool:
        self._refill()
        with self.lock:
            if self.tokens >= amount:
                self.tokens -= amount
                return True
            return False

_buckets = {}
_buckets_lock = threading.Lock()

def get_bucket_for_key(api_key: str) -> TokenBucket:
    with _buckets_lock:
        if api_key not in _buckets:
            _buckets[api_key] = TokenBucket(RATE_LIMIT_CAPACITY, RATE_LIMIT_TOKENS_PER_REFILL, RATE_LIMIT_REFILL_SECONDS)
        return _buckets[api_key]

def require_api_key(x_api_key: str = Header(None)):
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Missing API key header 'x-api-key'")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    bucket = get_bucket_for_key(x_api_key)
    if not bucket.consume(1):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return x_api_key

# ============================
# MODELS
# ============================
class SearchRequest(BaseModel):
    query: str
    max_results: int = 5

class FetchRequest(BaseModel):
    url: str

# ============================
# SEARCH ENDPOINT (DuckDuckGo)
# ============================
@app.post("/search")
def search(request: SearchRequest, x_api_key: str = Header(None)):
    require_api_key(x_api_key)
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Empty search query")

    try:
        url = f"https://api.duckduckgo.com/?q={query}&format=json&no_redirect=1&skip_disambig=1"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()

        results = []
        related = data.get("RelatedTopics", [])
        for item in related:
            if len(results) >= request.max_results:
                break
            if "Text" in item and "FirstURL" in item:
                results.append({"title": item["Text"], "link": item["FirstURL"]})
            elif "Topics" in item:
                for sub in item["Topics"]:
                    if "Text" in sub and "FirstURL" in sub:
                        results.append({"title": sub["Text"], "link": sub["FirstURL"]})
        return {"query": query, "results": results[:request.max_results]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================
# FETCH ENDPOINT
# ============================
@app.post("/fetch")
def fetch(request: FetchRequest, x_api_key: str = Header(None)):
    require_api_key(x_api_key)
    url = request.url.strip()
    if url.startswith("http://localhost") or url.startswith("http://127.0.0.1"):
        raise HTTPException(status_code=400, detail="Local URLs are blocked")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return {"content": response.text[:4000]}  # first 4000 chars
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================
# GENERATE ENDPOINT (LLM)
# ============================
@app.get("/health")
async def health_check():
    return {"status": "ok"}
    
@app.post("/generate")
async def generate(request: Request, x_api_key: str = Header(None)):
    require_api_key(x_api_key)

    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    if "prompt" not in body:
        raise HTTPException(status_code=400, detail="Missing 'prompt' in request body")
    if "model" not in body:
        body["model"] = "llama3"

    # optional: include search results in prompt
    search_results_text = ""
    if body.get("search_query"):
        try:
            sr_response = search(SearchRequest(query=body["search_query"], max_results=3), x_api_key=x_api_key)
            snippets = [f"{r['title']} ({r['link']})" for r in sr_response["results"]]
            search_results_text = "\n".join(snippets)
            body["prompt"] += f"\n\nUse the following search results to answer:\n{search_results_text}"
        except Exception:
            pass  # ignore search failures

    try:
        upstream = requests.post(OLLAMA_URL, json=body, stream=True, timeout=300)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error contacting Ollama: {e}")

    if upstream.status_code != 200 and upstream.status_code != 204:
        text = upstream.text[:1000]
        raise HTTPException(status_code=upstream.status_code, detail=f"Ollama error: {text}")

    def event_stream() -> AsyncGenerator[bytes, None]:
        try:
            for line in upstream.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    chunk = data.get("response") or data.get("delta") or data.get("text") or ""
                    if chunk:
                        yield chunk.encode("utf-8")
                    else:
                        yield (line + "\n").encode("utf-8")
                except json.JSONDecodeError:
                    yield (line + "\n").encode("utf-8")
        finally:
            upstream.close()

    return StreamingResponse(event_stream(), media_type="text/plain; charset=utf-8")
