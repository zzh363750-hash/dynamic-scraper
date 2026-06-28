"""
Dynamic Scraper API — SaaS MVP
Run: uvicorn main:app --host 0.0.0.0 --port 8000
"""

import os
import sys
import time
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Depends, Request, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

# Add parent dir to path for scraper
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from scrape import (
    scrape_mobile_ua, scrape_desktop_ua, scrape_chrome,
    extract_title, extract_content, extract_meta,
    extract_images, extract_links, get_site_config, detect_site
)

# ─── Config ───────────────────────────────────────────────────────────

API_KEYS_FILE = Path(__file__).parent / "api_keys.json"
USAGE_FILE = Path(__file__).parent / "usage.json"

# Rate limits: requests per day
PLANS = {
    "free": 10,
    "basic": 1000,
    "pro": 999999,
}

# ─── Storage (simple JSON file-based) ────────────────────────────────

def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}

def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def get_api_keys() -> dict:
    return load_json(API_KEYS_FILE)

def save_api_keys(keys: dict):
    save_json(API_KEYS_FILE, keys)

def get_usage() -> dict:
    return load_json(USAGE_FILE)

def save_usage(usage: dict):
    save_json(USAGE_FILE, usage)

# ─── API Key Management ──────────────────────────────────────────────

def generate_api_key() -> str:
    return f"ds_{secrets.token_hex(20)}"

def get_plan_for_key(api_key: str) -> str:
    keys = get_api_keys()
    return keys.get(api_key, {}).get("plan", "free")

def check_rate_limit(api_key: str) -> bool:
    usage = get_usage()
    today = datetime.now().strftime("%Y-%m-%d")
    plan = get_plan_for_key(api_key)
    limit = PLANS.get(plan, PLANS["free"])

    key_usage = usage.get(api_key, {})
    daily_count = key_usage.get(today, 0)

    return daily_count < limit

def increment_usage(api_key: str):
    usage = get_usage()
    today = datetime.now().strftime("%Y-%m-%d")

    if api_key not in usage:
        usage[api_key] = {}
    usage[api_key][today] = usage[api_key].get(today, 0) + 1

    # Clean old entries (keep last 30 days)
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    usage[api_key] = {k: v for k, v in usage[api_key].items() if k >= cutoff}

    save_usage(usage)

# ─── Auth dependency ──────────────────────────────────────────────────

async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    keys = get_api_keys()
    if x_api_key not in keys:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not check_rate_limit(x_api_key):
        raise HTTPException(status_code=429, detail="Daily rate limit exceeded")

    return x_api_key

# ─── App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Dynamic Scraper API",
    description="从动态渲染的网页中提取内容，支持微信公众号、知乎、B站等",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ───────────────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    url: str
    images: bool = False
    links: bool = False
    meta: bool = False

class ScrapeResponse(BaseModel):
    success: bool
    url: str
    site: str
    title: Optional[str] = None
    content: Optional[str] = None
    meta: Optional[dict] = None
    images: Optional[list] = None
    links: Optional[list] = None
    error: Optional[str] = None

class CreateKeyRequest(BaseModel):
    plan: str = "free"

# ─── Routes ───────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    return """<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dynamic Scraper API</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, sans-serif; background: #0a0a0a; color: #fff; min-height: 100vh; }
        .container { max-width: 800px; margin: 0 auto; padding: 60px 20px; }
        h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .subtitle { color: #888; font-size: 1.1rem; margin-bottom: 40px; }
        .badge { display: inline-block; background: #22c55e; color: #000; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; margin-bottom: 30px; }
        .section { margin-bottom: 40px; }
        .section h2 { color: #22c55e; margin-bottom: 15px; font-size: 1.3rem; }
        .code { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 20px; font-family: 'SF Mono', monospace; font-size: 0.9rem; overflow-x: auto; }
        .code .comment { color: #666; }
        .code .string { color: #22c55e; }
        .code .keyword { color: #c084fc; }
        .plans { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 20px; }
        .plan { background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 20px; text-align: center; }
        .plan.popular { border-color: #22c55e; }
        .plan h3 { margin-bottom: 10px; }
        .plan .price { font-size: 2rem; font-weight: bold; color: #22c55e; }
        .plan .limit { color: #888; margin-top: 5px; }
        .btn { display: inline-block; background: #22c55e; color: #000; padding: 12px 30px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 15px; }
        .features { list-style: none; margin-top: 20px; }
        .features li { padding: 8px 0; border-bottom: 1px solid #222; }
        .features li::before { content: "✓ "; color: #22c55e; }
        @media (max-width: 600px) { .plans { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Dynamic Scraper API</h1>
        <p class="subtitle">从动态渲染的网页中提取内容，支持微信公众号、知乎、B站等</p>
        <span class="badge">v1.0.0</span>

        <div class="section">
            <h2>快速开始</h2>
            <div class="code">
<span class="comment"># 1. 获取 API Key</span>
curl -X POST https://your-domain.com/api/keys \\
  -H "Content-Type: application/json" \\
  -d '{"plan": "free"}'

<span class="comment"># 2. 调用 API</span>
curl -X POST https://your-domain.com/api/scrape \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: ds_xxxxxxxxxxxx" \\
  -d '{"url": "https://mp.weixin.qq.com/s/xxx"}'
            </div>
        </div>

        <div class="section">
            <h2>套餐</h2>
            <div class="plans">
                <div class="plan">
                    <h3>Free</h3>
                    <div class="price">¥0</div>
                    <div class="limit">10 次/天</div>
                </div>
                <div class="plan popular">
                    <h3>Basic</h3>
                    <div class="price">¥9.9</div>
                    <div class="limit">1,000 次/月</div>
                </div>
                <div class="plan">
                    <h3>Pro</h3>
                    <div class="price">¥49</div>
                    <div class="limit">无限次</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>支持的网站</h2>
            <ul class="features">
                <li>微信公众号文章</li>
                <li>知乎专栏 / 回答</li>
                <li>B站专栏</li>
                <li>掘金文章</li>
                <li>CSDN 博客</li>
                <li>其他 SPA 网站（通用）</li>
            </ul>
        </div>
    </div>
</body>
</html>"""


@app.post("/api/scrape", response_model=ScrapeResponse)
async def scrape(req: ScrapeRequest, api_key: str = Depends(verify_api_key)):
    """Scrape a dynamically rendered web page."""
    try:
        # Fetch HTML
        html_text = scrape_mobile_ua(req.url)
        if not html_text:
            html_text = scrape_desktop_ua(req.url)
        if not html_text:
            html_text = scrape_chrome(req.url)
        if not html_text:
            return ScrapeResponse(
                success=False, url=req.url, site="unknown",
                error="Could not fetch page content"
            )

        config = get_site_config(req.url)
        site = detect_site(req.url)

        result = ScrapeResponse(
            success=True,
            url=req.url,
            site=site,
            title=extract_title(html_text, config),
            content=extract_content(html_text, config),
        )

        if req.meta:
            result.meta = extract_meta(html_text, config)
        if req.images:
            result.images = extract_images(html_text, req.url)
        if req.links:
            result.links = extract_links(html_text, req.url)

        # Count usage
        increment_usage(api_key)

        return result

    except Exception as e:
        return ScrapeResponse(
            success=False, url=req.url, site="unknown",
            error=str(e)
        )


@app.post("/api/keys")
async def create_api_key(req: CreateKeyRequest):
    """Create a new API key."""
    if req.plan not in PLANS:
        raise HTTPException(400, f"Invalid plan. Choose from: {list(PLANS.keys())}")

    api_key = generate_api_key()
    keys = get_api_keys()
    keys[api_key] = {
        "plan": req.plan,
        "created": datetime.now().isoformat(),
    }
    save_api_keys(keys)

    return {
        "api_key": api_key,
        "plan": req.plan,
        "daily_limit": PLANS[req.plan],
        "docs": "https://your-domain.com/docs",
    }


@app.get("/api/usage")
async def get_usage_info(api_key: str = Depends(verify_api_key)):
    """Get current usage stats."""
    usage = get_usage()
    today = datetime.now().strftime("%Y-%m-%d")
    plan = get_plan_for_key(api_key)
    limit = PLANS.get(plan, PLANS["free"])

    key_usage = usage.get(api_key, {})
    daily_count = key_usage.get(today, 0)
    total_count = sum(key_usage.values())

    return {
        "plan": plan,
        "daily_limit": limit,
        "daily_used": daily_count,
        "daily_remaining": max(0, limit - daily_count),
        "total_used": total_count,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# ─── Init demo key on startup ────────────────────────────────────────

@app.on_event("startup")
async def startup():
    keys = get_api_keys()
    if not keys:
        demo_key = "ds_demo_free_key_12345"
        keys[demo_key] = {
            "plan": "free",
            "created": datetime.now().isoformat(),
            "note": "Demo key for testing",
        }
        save_api_keys(keys)
        print(f"✅ Demo API key created: {demo_key}")
