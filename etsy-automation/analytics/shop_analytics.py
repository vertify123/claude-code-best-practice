"""
Etsy Shop Analytics
Pulls transaction data and generates a performance report.

Usage:
  python analytics/shop_analytics.py              # last 30 days summary
  python analytics/shop_analytics.py --days 90    # last 90 days
  python analytics/shop_analytics.py --json       # output raw JSON
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Etsy fee constants (mirrors research/product_researcher.py)
TRANSACTION_FEE_PCT = 0.065
PAYMENT_PCT = 0.03
PAYMENT_FIXED = 0.25
LISTING_FEE = 0.20


def _net_revenue(price: float) -> float:
    fees = (
        price * TRANSACTION_FEE_PCT
        + price * PAYMENT_PCT
        + PAYMENT_FIXED
        + LISTING_FEE
    )
    return round(price - fees, 2)


def build_report(transactions: list, days: int = 30) -> dict:
    now = datetime.now(tz=timezone.utc)
    cutoff_ts = now.timestamp() - days * 86400

    recent = [
        t for t in transactions
        if t.get("create_timestamp", 0) >= cutoff_ts
    ]

    total_gross = 0.0
    total_net = 0.0
    by_listing: dict[str, dict] = defaultdict(lambda: {"sales": 0, "gross": 0.0, "net": 0.0})

    for t in recent:
        price_cents = t.get("price", {}).get("amount", 0)
        divisor = t.get("price", {}).get("divisor", 100) or 100
        price = price_cents / divisor
        quantity = t.get("quantity", 1)
        gross = price * quantity
        net = _net_revenue(price) * quantity

        total_gross += gross
        total_net += net

        title = t.get("title", "Unknown listing")
        by_listing[title]["sales"] += quantity
        by_listing[title]["gross"] += gross
        by_listing[title]["net"] += net

    # Top listings by net revenue
    top_listings = sorted(
        [{"title": k, **v} for k, v in by_listing.items()],
        key=lambda x: x["net"],
        reverse=True,
    )[:10]

    # Round floats
    for l in top_listings:
        l["gross"] = round(l["gross"], 2)
        l["net"] = round(l["net"], 2)

    return {
        "period_days": days,
        "total_transactions": len(recent),
        "gross_revenue_usd": round(total_gross, 2),
        "net_revenue_usd": round(total_net, 2),
        "etsy_fees_usd": round(total_gross - total_net, 2),
        "avg_order_value_usd": round(total_gross / len(recent), 2) if recent else 0,
        "effective_margin_pct": (
            round(total_net / total_gross * 100, 1) if total_gross > 0 else 0
        ),
        "top_listings": top_listings,
        "pricing_recommendations": _pricing_recs(top_listings, total_gross, len(recent)),
    }


def _pricing_recs(top_listings: list, gross: float, count: int) -> list:
    recs = []
    if not top_listings:
        recs.append("No sales yet. Run research agent to find winning niches.")
        return recs

    top = top_listings[0]
    if top["sales"] > 5:
        recs.append(f"Top listing '{top['title'][:50]}' is selling well — "
                    f"consider a 10-15% price increase to test elasticity.")

    if count > 0 and gross / count < 8:
        recs.append("Average order value is low. Bundle listings or add upsells.")

    if len(top_listings) == 1:
        recs.append("Only one listing driving revenue — diversify your catalog.")

    return recs


def run(days: int = 30, as_json: bool = False) -> None:
    from api.etsy_client import EtsyClient
    client = EtsyClient()
    print(f"[analytics] Fetching up to 100 transactions…", file=sys.stderr)
    transactions = client.get_transactions(limit=100)
    report = build_report(transactions, days)

    if as_json:
        print(json.dumps(report, indent=2))
        return

    # Pretty print
    print(f"\n{'='*50}")
    print(f"  Etsy Shop Analytics — Last {days} days")
    print(f"{'='*50}")
    print(f"  Transactions : {report['total_transactions']}")
    print(f"  Gross Revenue: ${report['gross_revenue_usd']:.2f}")
    print(f"  Etsy Fees    : ${report['etsy_fees_usd']:.2f}")
    print(f"  Net Revenue  : ${report['net_revenue_usd']:.2f}")
    print(f"  Margin       : {report['effective_margin_pct']}%")
    print(f"  Avg Order    : ${report['avg_order_value_usd']:.2f}")
    print(f"\n  Top Listings:")
    for i, l in enumerate(report["top_listings"][:5], 1):
        print(f"    {i}. {l['title'][:55]:<55} {l['sales']} sales  ${l['net']:.2f} net")
    if report["pricing_recommendations"]:
        print(f"\n  Recommendations:")
        for r in report["pricing_recommendations"]:
            print(f"    • {r}")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    run(days=args.days, as_json=args.json)
