#!/usr/bin/env python3
"""Simple stock portfolio manager — tracks holdings, cost basis, and P&L."""

import json
import os
from datetime import date

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "portfolio.json")


def load() -> dict:
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE) as f:
            return json.load(f)
    return {"holdings": {}, "cash": 0.0}


def save(portfolio: dict) -> None:
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2)


def buy(symbol: str, shares: float, price: float) -> None:
    portfolio = load()
    symbol = symbol.upper()
    cost = shares * price

    if portfolio["cash"] < cost:
        print(f"Insufficient cash (${portfolio['cash']:.2f} available, ${cost:.2f} needed).")
        return

    h = portfolio["holdings"]
    if symbol in h:
        total_shares = h[symbol]["shares"] + shares
        total_cost = h[symbol]["avg_cost"] * h[symbol]["shares"] + cost
        h[symbol]["shares"] = total_shares
        h[symbol]["avg_cost"] = total_cost / total_shares
    else:
        h[symbol] = {"shares": shares, "avg_cost": price}

    portfolio["cash"] -= cost
    save(portfolio)
    print(f"Bought {shares} shares of {symbol} @ ${price:.2f}. Cash remaining: ${portfolio['cash']:.2f}")


def sell(symbol: str, shares: float, price: float) -> None:
    portfolio = load()
    symbol = symbol.upper()
    h = portfolio["holdings"]

    if symbol not in h or h[symbol]["shares"] < shares:
        held = h.get(symbol, {}).get("shares", 0)
        print(f"Cannot sell {shares} shares — only {held} held.")
        return

    proceeds = shares * price
    gain = (price - h[symbol]["avg_cost"]) * shares
    h[symbol]["shares"] -= shares

    if h[symbol]["shares"] == 0:
        del h[symbol]

    portfolio["cash"] += proceeds
    save(portfolio)
    print(f"Sold {shares} shares of {symbol} @ ${price:.2f}. P&L: ${gain:+.2f}. Cash: ${portfolio['cash']:.2f}")


def deposit(amount: float) -> None:
    portfolio = load()
    portfolio["cash"] += amount
    save(portfolio)
    print(f"Deposited ${amount:.2f}. Total cash: ${portfolio['cash']:.2f}")


def view(current_prices: dict[str, float] | None = None) -> None:
    portfolio = load()
    h = portfolio["holdings"]

    print(f"\n{'=' * 52}")
    print(f"  Stock Portfolio  —  {date.today()}")
    print(f"{'=' * 52}")
    print(f"  Cash:  ${portfolio['cash']:>10.2f}")
    print(f"{'─' * 52}")

    total_market = 0.0
    total_cost = 0.0

    if not h:
        print("  No holdings.")
    else:
        print(f"  {'Symbol':<8} {'Shares':>8} {'Avg Cost':>10} {'Mkt Price':>10} {'P&L':>10}")
        print(f"  {'─' * 48}")
        for sym, data in sorted(h.items()):
            shares = data["shares"]
            avg = data["avg_cost"]
            mkt = (current_prices or {}).get(sym, avg)
            pnl = (mkt - avg) * shares
            total_market += mkt * shares
            total_cost += avg * shares
            print(f"  {sym:<8} {shares:>8.2f} {avg:>10.2f} {mkt:>10.2f} {pnl:>+10.2f}")

    print(f"{'─' * 52}")
    total_pnl = total_market - total_cost
    total_value = total_market + portfolio["cash"]
    print(f"  Holdings value:  ${total_market:>10.2f}  (P&L: ${total_pnl:>+.2f})")
    print(f"  Total portfolio: ${total_value:>10.2f}")
    print(f"{'=' * 52}\n")


def reset() -> None:
    if os.path.exists(PORTFOLIO_FILE):
        os.remove(PORTFOLIO_FILE)
    print("Portfolio reset.")


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "view"

    if cmd == "deposit" and len(sys.argv) == 3:
        deposit(float(sys.argv[2]))
    elif cmd == "buy" and len(sys.argv) == 5:
        buy(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]))
    elif cmd == "sell" and len(sys.argv) == 5:
        sell(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]))
    elif cmd == "view":
        view()
    elif cmd == "reset":
        reset()
    else:
        print("Usage:")
        print("  python portfolio.py deposit <amount>")
        print("  python portfolio.py buy <SYMBOL> <shares> <price>")
        print("  python portfolio.py sell <SYMBOL> <shares> <price>")
        print("  python portfolio.py view")
        print("  python portfolio.py reset")
