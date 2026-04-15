"""
Etsy AI Command Center
A rich terminal dashboard showing live shop metrics, agent status, and activity.

Usage:
  python dashboard/command_center.py           # print snapshot once and exit
  python dashboard/command_center.py --watch   # live-refresh every 10s (Ctrl+C to quit)
  python dashboard/command_center.py --json    # machine-readable JSON (for Claude to parse)

The dashboard shows:
  - Shop Metrics      (revenue, net, orders, unread messages, active listings)
  - Agent Status      (last run, current status, last action for each agent)
  - Recent Activity   (timeline of agent events from activity.jsonl)
  - Quick Commands    (copy-paste shortcuts)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow running from project root or from dashboard/ directory
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from rich import box
    from rich.align import Align
    from rich.columns import Columns
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.table import Table
    from rich.text import Text
except ImportError:
    sys.exit(
        "[command_center] 'rich' is not installed.\n"
        "Run: pip install rich"
    )

from dashboard.agent_logger import get_agent_statuses, read_recent

AGENT_META = [
    ("etsy-research-agent",          "Research",        "🔬"),
    ("etsy-listing-agent",           "Listing",         "📝"),
    ("etsy-customer-service-agent",  "Customer Service","💬"),
    ("etsy-analytics-agent",         "Analytics",       "📊"),
]

STATUS_STYLES = {
    "start":    ("● Running", "bold green"),
    "complete": ("✓ Done",    "green"),
    "error":    ("✗ Error",   "bold red"),
    "info":     ("ℹ Info",    "cyan"),
    "idle":     ("○ Idle",    "dim"),
}

EVENT_STYLES = {
    "start":    "yellow",
    "complete": "green",
    "error":    "red",
    "info":     "cyan",
}


# ─────────────────────────────────────────────────────────────────────────────
# Shop metrics (from Etsy API — gracefully degrades if not configured)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_shop_metrics() -> dict | None:
    """
    Pull live metrics from Etsy API.
    Returns None if ETSY_API_KEY is not set.
    Returns {"error": "..."} on API failure.
    """
    if not os.environ.get("ETSY_API_KEY"):
        return None
    try:
        from api.etsy_client import EtsyClient
        client = EtsyClient()

        transactions = client.get_transactions(limit=100)
        listings = client.get_shop_listings(state="active", limit=100)
        conversations = client.get_conversations(limit=50)

        now_ts = time.time()
        cutoff_30d = now_ts - 30 * 86400

        gross_30d = 0.0
        net_30d = 0.0
        orders_30d = 0

        for t in transactions:
            if t.get("create_timestamp", 0) >= cutoff_30d:
                price_cents = t.get("price", {}).get("amount", 0)
                divisor = t.get("price", {}).get("divisor", 100) or 100
                price = price_cents / divisor
                qty = t.get("quantity", 1)
                gross = price * qty
                # Simple net: subtract 6.5% transaction + 3% payment + $0.20 + $0.25
                net = (price - price * 0.095 - 0.45) * qty
                gross_30d += gross
                net_30d += net
                orders_30d += qty

        unread = sum(1 for c in conversations if c.get("unread_count", 0) > 0)

        return {
            "gross_30d": round(gross_30d, 2),
            "net_30d": round(net_30d, 2),
            "orders_30d": orders_30d,
            "active_listings": len(listings),
            "unread_messages": unread,
            "margin_30d": round(net_30d / gross_30d * 100, 1) if gross_30d > 0 else 0,
        }
    except Exception as exc:
        return {"error": str(exc)[:80]}


# ─────────────────────────────────────────────────────────────────────────────
# Panel builders
# ─────────────────────────────────────────────────────────────────────────────

def _panel_header(timestamp: str) -> Text:
    t = Text(justify="center")
    t.append("⚡  ETSY AI COMMAND CENTER  ⚡\n", style="bold white")
    t.append(f"Last refresh: {timestamp}", style="dim")
    return t


def _panel_metrics(metrics: dict | None) -> Panel:
    if metrics is None:
        body = Text(
            "\n  API key not configured.\n\n"
            "  1. Copy etsy-automation/.env.example → .env\n"
            "  2. Add your ETSY_API_KEY and ETSY_SHOP_ID\n"
            "  3. Run: python api/etsy_client.py --auth\n",
            style="dim yellow",
        )
        return Panel(body, title="[bold magenta]SHOP METRICS[/bold magenta]",
                     border_style="magenta", padding=(0, 1))

    if "error" in metrics:
        body = Text(f"\n  API error: {metrics['error']}", style="red")
        return Panel(body, title="[bold red]SHOP METRICS[/bold red]",
                     border_style="red", padding=(0, 1))

    body = Text()
    body.append("\n")
    body.append("  Revenue (30d)    ", style="dim")
    body.append(f"${metrics['gross_30d']:.2f}\n", style="bold green")
    body.append("  Net Revenue      ", style="dim")
    body.append(f"${metrics['net_30d']:.2f}", style="bold green")
    body.append(f"  ({metrics['margin_30d']}% margin)\n", style="dim green")
    body.append("  Orders           ", style="dim")
    body.append(f"{metrics['orders_30d']}\n", style="white")
    body.append("  Active Listings  ", style="dim")
    body.append(f"{metrics['active_listings']}\n", style="white")
    body.append("  Unread Messages  ", style="dim")
    msgs = metrics["unread_messages"]
    body.append(f"{msgs}\n", style="bold yellow" if msgs > 0 else "white")

    return Panel(body, title="[bold magenta]SHOP METRICS[/bold magenta]",
                 border_style="magenta", padding=(0, 1))


def _panel_agent_status(statuses: dict) -> Panel:
    table = Table(show_header=True, header_style="bold cyan",
                  box=box.SIMPLE_HEAD, padding=(0, 1))
    table.add_column("Agent",       style="bold", min_width=16)
    table.add_column("Status",      min_width=12)
    table.add_column("Last Action", min_width=35)
    table.add_column("When",        style="dim", min_width=8)

    for name, label, icon in AGENT_META:
        s = statuses.get(name, {})
        raw_status = s.get("status", "idle")
        label_str, style = STATUS_STYLES.get(raw_status, ("○ Idle", "dim"))
        status_text = Text(label_str, style=style)
        detail = s.get("detail", "—")[:40]
        ago = s.get("ago", "—")
        table.add_row(f"{icon} {label}", status_text, detail, ago)

    return Panel(table, title="[bold cyan]AGENT STATUS[/bold cyan]",
                 border_style="cyan", padding=(0, 1))


def _panel_activity(entries: list) -> Panel:
    table = Table(show_header=True, header_style="bold yellow",
                  box=box.SIMPLE_HEAD, padding=(0, 1))
    table.add_column("Time",   style="dim",  min_width=10)
    table.add_column("Agent",               min_width=18)
    table.add_column("Event",               min_width=9)
    table.add_column("Detail")

    recent = list(reversed(entries[-12:]))
    if not recent:
        table.add_row("—", "No activity yet", "—",
                      "Run /etsy-orchestrator to start")
    else:
        for e in recent:
            ts = e.get("ts", 0)
            time_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "—"
            agent_short = (e.get("agent", "—")
                           .replace("etsy-", "")
                           .replace("-agent", ""))
            event = e.get("event", "—")
            detail = e.get("detail", "—")[:55]
            ev_style = EVENT_STYLES.get(event, "white")
            table.add_row(time_str, agent_short,
                          Text(event, style=ev_style), detail)

    return Panel(table, title="[bold yellow]RECENT ACTIVITY[/bold yellow]",
                 border_style="yellow", padding=(0, 1))


def _panel_quick_commands() -> Panel:
    body = Text()
    commands = [
        ("/etsy-orchestrator",            "Full menu — research, list, CS, analytics"),
        ("/etsy-orchestrator research",   "Find winning product niches"),
        ("/etsy-orchestrator listing",    "Create new listing"),
        ("/etsy-orchestrator cs",         "Handle buyer messages"),
        ("/etsy-orchestrator analytics",  "Revenue + performance report"),
        ("/etsy-dashboard",               "Refresh this dashboard"),
    ]
    for cmd, desc in commands:
        body.append(f"  {cmd:<38}", style="bold cyan")
        body.append(f"{desc}\n", style="dim")
    return Panel(body, title="[bold]QUICK COMMANDS[/bold]",
                 border_style="dim", padding=(0, 1))


# ─────────────────────────────────────────────────────────────────────────────
# Render
# ─────────────────────────────────────────────────────────────────────────────

def render(console: Console) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    metrics = _fetch_shop_metrics()
    statuses = get_agent_statuses()
    entries = read_recent(50)

    console.print()
    console.print(Panel(
        Align(_panel_header(timestamp), align="center"),
        style="bold blue", padding=(0, 2)
    ))
    console.print()
    console.print(Columns(
        [_panel_metrics(metrics), _panel_agent_status(statuses)],
        equal=True, expand=True
    ))
    console.print()
    console.print(_panel_activity(entries))
    console.print()
    console.print(_panel_quick_commands())
    console.print()


def run_watch(refresh_seconds: int = 10) -> None:
    console = Console()
    try:
        while True:
            console.clear()
            render(console)
            console.print(
                f"[dim]  Auto-refreshing every {refresh_seconds}s  —  Ctrl+C to exit[/dim]\n"
            )
            time.sleep(refresh_seconds)
    except KeyboardInterrupt:
        console.print("\n[dim]Dashboard closed.[/dim]")


def run_once() -> None:
    console = Console()
    render(console)


def run_json() -> None:
    from dashboard.agent_logger import get_json_summary
    metrics = _fetch_shop_metrics()
    summary = get_json_summary()
    summary["shop_metrics"] = metrics
    print(json.dumps(summary, indent=2, default=str))


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--watch" in sys.argv:
        refresh = 10
        for arg in sys.argv:
            if arg.startswith("--watch="):
                try:
                    refresh = int(arg.split("=")[1])
                except ValueError:
                    pass
        run_watch(refresh)
    elif "--json" in sys.argv:
        run_json()
    else:
        run_once()
