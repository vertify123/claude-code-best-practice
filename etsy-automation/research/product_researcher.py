"""
Etsy Product Research Tool
Finds winning product niches with the best margins.

Usage:
  python research/product_researcher.py "<niche>" [digital|pod|handmade]
  python research/product_researcher.py --top-niches

Output: JSON report with opportunity score, competition, margin breakdown.

The tool works in two modes:
  1. With ETSY_API_KEY set → pulls real listing data from Etsy API
  2. Without API key       → uses web search stubs (Claude agents handle the search)
"""

import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Optional

# Add parent dir so we can import etsy_client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Etsy fee structure (as of 2024)
ETSY_FEES = {
    "listing_fee": 0.20,           # per listing, every 4 months
    "transaction_fee_pct": 0.065,  # 6.5% of item price + shipping
    "payment_pct": 0.03,           # 3% payment processing
    "payment_fixed": 0.25,         # $0.25 per transaction
}

# Popular niches to scan if no specific niche is given
TOP_NICHES = [
    ("printable wall art", "digital"),
    ("svg bundle cut files", "digital"),
    ("printable planner", "digital"),
    ("baby shower printable", "digital"),
    ("wedding invitation template", "digital"),
    ("custom dog portrait", "pod"),
    ("motivational mug", "pod"),
    ("personalized tote bag", "pod"),
    ("watercolor pet portrait", "handmade"),
    ("macrame wall hanging", "handmade"),
]


@dataclass
class FeeBreakdown:
    listing_fee: float
    transaction_fee: float
    payment_processing: float
    total_fees: float
    net_revenue: float
    margin_pct: float


@dataclass
class CompetitionSnapshot:
    listing_count: int
    avg_price_usd: float
    min_price_usd: float
    max_price_usd: float
    avg_favorites: float
    high_demand_count: int  # listings with >100 favorites


@dataclass
class ProductOpportunity:
    niche: str
    product_type: str             # digital | pod | handmade
    competition: CompetitionSnapshot
    suggested_price_usd: float
    cogs_usd: float               # cost of goods sold
    fees: FeeBreakdown
    net_profit_usd: float
    overall_margin_pct: float
    opportunity_score: float      # 0-100
    verdict: str                  # STRONG | MODERATE | WEAK
    reasoning: str


def calculate_fees(price: float, shipping: float = 0.0) -> FeeBreakdown:
    """Return a full Etsy fee breakdown for a given sell price."""
    transaction = (price + shipping) * ETSY_FEES["transaction_fee_pct"]
    payment = price * ETSY_FEES["payment_pct"] + ETSY_FEES["payment_fixed"]
    total = ETSY_FEES["listing_fee"] + transaction + payment
    net = price - total
    margin = (net / price * 100) if price > 0 else 0.0
    return FeeBreakdown(
        listing_fee=round(ETSY_FEES["listing_fee"], 2),
        transaction_fee=round(transaction, 2),
        payment_processing=round(payment, 2),
        total_fees=round(total, 2),
        net_revenue=round(net, 2),
        margin_pct=round(margin, 1),
    )


def cogs_for_type(price: float, product_type: str) -> float:
    """Estimate cost of goods based on product type."""
    if product_type == "digital":
        return 0.0          # Digital files have zero marginal COGS
    elif product_type == "pod":
        return price * 0.40  # Printify/Printful typically ~40% of sell price
    else:  # handmade
        return price * 0.25  # Materials ~25%


def competition_from_listings(listings: list) -> CompetitionSnapshot:
    """Build a CompetitionSnapshot from raw Etsy listing dicts."""
    if not listings:
        return CompetitionSnapshot(0, 0, 0, 0, 0, 0)

    prices = []
    for l in listings:
        p = l.get("price", {})
        amount = p.get("amount", 0)
        divisor = p.get("divisor", 100) or 100
        prices.append(amount / divisor)

    favorites = [l.get("num_favorers", 0) for l in listings]

    return CompetitionSnapshot(
        listing_count=len(listings),
        avg_price_usd=round(sum(prices) / len(prices), 2),
        min_price_usd=round(min(prices), 2),
        max_price_usd=round(max(prices), 2),
        avg_favorites=round(sum(favorites) / len(favorites), 1),
        high_demand_count=sum(1 for f in favorites if f > 100),
    )


def competition_from_summary(count: int, avg_price: float, avg_favorites: float) -> CompetitionSnapshot:
    """Build a CompetitionSnapshot from manually supplied data (no API key)."""
    return CompetitionSnapshot(
        listing_count=count,
        avg_price_usd=avg_price,
        min_price_usd=avg_price * 0.5,
        max_price_usd=avg_price * 2.0,
        avg_favorites=avg_favorites,
        high_demand_count=max(0, int(count * 0.05)),
    )


def score_opportunity(comp: CompetitionSnapshot, net_profit: float, price: float) -> tuple[float, str]:
    """
    Return (score 0-100, reasoning).
    Weights: margin 40%, demand signals 35%, competition density 25%.
    """
    margin_pct = (net_profit / price * 100) if price > 0 else 0

    # Margin score: 80%+ margin → 100 pts (digital); penalise below 40%
    margin_score = min(100, max(0, margin_pct * 1.25))

    # Demand score: avg_favorites proxy
    demand_score = min(100, comp.avg_favorites / 2)

    # Competition score: fewer listings = less competition
    if comp.listing_count == 0:
        comp_score = 50  # unknown
    elif comp.listing_count < 500:
        comp_score = 90
    elif comp.listing_count < 5_000:
        comp_score = 70
    elif comp.listing_count < 20_000:
        comp_score = 45
    else:
        comp_score = 20

    score = margin_score * 0.40 + demand_score * 0.35 + comp_score * 0.25
    score = round(score, 1)

    reasons = [
        f"margin {margin_pct:.0f}%",
        f"avg favorites {comp.avg_favorites:.0f}",
        f"{comp.listing_count:,} competing listings",
    ]
    verdict_reason = " | ".join(reasons)
    return score, verdict_reason


def analyse_niche(
    niche: str,
    product_type: str = "digital",
    listings: Optional[list] = None,
    manual_count: int = 0,
    manual_avg_price: float = 0.0,
    manual_avg_favorites: float = 0.0,
) -> ProductOpportunity:
    """
    Core analysis. Pass either raw `listings` (from API) or manual summary stats
    (from web research). If nothing is supplied, competition snapshot is zeroed.
    """
    if listings:
        comp = competition_from_listings(listings)
        price = comp.avg_price_usd or (7.99 if product_type == "digital" else 24.99)
    elif manual_count:
        comp = competition_from_summary(manual_count, manual_avg_price, manual_avg_favorites)
        price = manual_avg_price or (7.99 if product_type == "digital" else 24.99)
    else:
        comp = CompetitionSnapshot(0, 0, 0, 0, 0, 0)
        price = 7.99 if product_type == "digital" else 24.99

    cogs = cogs_for_type(price, product_type)
    fees = calculate_fees(price)
    net_profit = fees.net_revenue - cogs
    overall_margin = round((net_profit / price * 100) if price > 0 else 0, 1)

    score, reasoning = score_opportunity(comp, net_profit, price)
    verdict = "STRONG" if score >= 70 else "MODERATE" if score >= 40 else "WEAK"

    return ProductOpportunity(
        niche=niche,
        product_type=product_type,
        competition=comp,
        suggested_price_usd=round(price, 2),
        cogs_usd=round(cogs, 2),
        fees=fees,
        net_profit_usd=round(net_profit, 2),
        overall_margin_pct=overall_margin,
        opportunity_score=score,
        verdict=verdict,
        reasoning=reasoning,
    )


def fetch_and_analyse(niche: str, product_type: str = "digital") -> ProductOpportunity:
    """Try to hit the Etsy API; fall back to zero-listing analysis if no key."""
    api_key = os.environ.get("ETSY_API_KEY", "")
    listings = []

    if api_key:
        try:
            from api.etsy_client import EtsyClient
            client = EtsyClient()
            listings = client.search_listings(niche, limit=50)
        except Exception as e:
            print(f"[researcher] API error: {e}", file=sys.stderr)

    return analyse_niche(niche, product_type, listings=listings)


def scan_top_niches() -> list[ProductOpportunity]:
    return [fetch_and_analyse(niche, ptype) for niche, ptype in TOP_NICHES]


def to_dict(opp: ProductOpportunity) -> dict:
    d = asdict(opp)
    return d


if __name__ == "__main__":
    try:
        from dashboard.agent_logger import log_event as _log
    except ImportError:
        def _log(*_): pass  # noqa: E731

    if "--top-niches" in sys.argv:
        _log("etsy-research-agent", "start", "Scanning top niches")
        results = scan_top_niches()
        results.sort(key=lambda o: o.opportunity_score, reverse=True)
        top = results[0].niche if results else "none"
        _log("etsy-research-agent", "complete",
             f"Top: {top} ({results[0].opportunity_score:.0f}pts)" if results else "no results")
        print(json.dumps([to_dict(r) for r in results], indent=2))
    elif len(sys.argv) >= 2:
        niche = sys.argv[1]
        ptype = sys.argv[2] if len(sys.argv) > 2 else "digital"
        _log("etsy-research-agent", "start", f"Analysing niche: {niche} ({ptype})")
        result = fetch_and_analyse(niche, ptype)
        _log("etsy-research-agent", "complete",
             f"{niche}: score={result.opportunity_score}, margin={result.overall_margin_pct}%")
        print(json.dumps(to_dict(result), indent=2))
    else:
        print("Usage:")
        print("  python research/product_researcher.py \"svg bundle\" digital")
        print("  python research/product_researcher.py --top-niches")
