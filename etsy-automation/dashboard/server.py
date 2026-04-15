"""
Etsy AI Command Center — Web Server
Serves the dashboard UI and a JSON status API polled by the frontend.

Usage:
  cd etsy-automation
  python dashboard/server.py            # starts on http://localhost:7842
  python dashboard/server.py --port 8080

The frontend polls /api/status every 3 seconds for live updates.
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

# Allow imports from etsy-automation root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.agent_logger import get_agent_statuses, read_recent

UI_FILE = Path(__file__).parent / "ui" / "index.html"
DEFAULT_PORT = 7842

app = FastAPI(title="Etsy AI Command Center", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(UI_FILE.read_text(encoding="utf-8"))


@app.get("/api/status")
async def status():
    agent_statuses = get_agent_statuses()
    activity = read_recent(40)

    recent_activity = [
        {
            "time": datetime.fromtimestamp(e["ts"]).strftime("%H:%M:%S"),
            "agent": e["agent"].replace("etsy-", "").replace("-agent", ""),
            "event": e["event"],
            "detail": e["detail"],
        }
        for e in reversed(activity)
    ]

    shop_metrics = _fetch_shop_metrics()
    research_results = _load_research_results()

    return JSONResponse({
        "server_time": datetime.now().strftime("%H:%M:%S"),
        "agent_statuses": agent_statuses,
        "research_results": research_results,
        "recent_activity": recent_activity,
        "shop_metrics": shop_metrics,
    })


@app.get("/api/ping")
async def ping():
    return {"ok": True}


# ── Research results helper ──────────────────────────────────────────────────

RESEARCH_FILE = Path(__file__).parent.parent / "research" / "latest_results.json"

def _load_research_results() -> list | None:
    """Load the most recent research run results (written by product_researcher)."""
    if not RESEARCH_FILE.exists():
        return None
    try:
        return json.loads(RESEARCH_FILE.read_text())
    except Exception:
        return None


# ── Shop metrics helper ──────────────────────────────────────────────────────

def _fetch_shop_metrics() -> dict | None:
    if not os.environ.get("ETSY_API_KEY"):
        return None
    try:
        from api.etsy_client import EtsyClient
        client = EtsyClient()
        transactions = client.get_transactions(limit=100)
        listings = client.get_shop_listings(state="active", limit=100)
        conversations = client.get_conversations(limit=50)

        cutoff = time.time() - 30 * 86400
        gross = net = 0.0
        orders = 0
        for t in transactions:
            if t.get("create_timestamp", 0) < cutoff:
                continue
            price_cents = t.get("price", {}).get("amount", 0)
            divisor = t.get("price", {}).get("divisor", 100) or 100
            price = price_cents / divisor
            qty = t.get("quantity", 1)
            gross += price * qty
            net += (price - price * 0.095 - 0.45) * qty
            orders += qty

        unread = sum(1 for c in conversations if c.get("unread_count", 0) > 0)
        return {
            "gross_30d": round(gross, 2),
            "net_30d": round(net, 2),
            "orders_30d": orders,
            "active_listings": len(listings),
            "unread_messages": unread,
            "margin_30d": round(net / gross * 100, 1) if gross > 0 else 0,
            "avg_order_value": round(gross / orders, 2) if orders > 0 else 0,
        }
    except Exception as exc:
        return {"error": str(exc)[:80]}


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = DEFAULT_PORT
    for arg in sys.argv[1:]:
        if arg.startswith("--port="):
            port = int(arg.split("=")[1])
        elif arg.isdigit():
            port = int(arg)

    print(f"\n  ⚡  Etsy AI Command Center")
    print(f"  → Open in browser: http://localhost:{port}\n")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
