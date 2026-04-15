---
name: etsy-market-research
description: Instructions for researching winning Etsy products with the best margins
user-invocable: false
---

# Etsy Market Research Skill

This skill provides a structured process for finding high-opportunity Etsy products.

## Goal

Identify 5 product niches with strong demand, low competition, and margins above 50%.

## Research Process

### Step 1: Trend Discovery (Web Search)

Use WebSearch to find current high-demand Etsy product trends:
- Search: `"best selling Etsy products 2025 digital downloads"`
- Search: `"etsy trending products low competition 2025"`
- Search: `"etsy winning niches printable high margin"`

Extract niche names, product types (digital/POD/handmade), and any reported sales figures.

### Step 2: Competition Check (Etsy Search)

For each candidate niche, use WebFetch to check Etsy search result counts:
- URL pattern: `https://www.etsy.com/search?q=<niche keyword>&ref=pagination`
- Look for the result count shown at the top: e.g., "23,489 results"
- Also note the price range of top 10 listings

Competition thresholds:
- < 5,000 results   → LOW competition (score +30)
- 5,000 – 20,000    → MEDIUM competition (score +15)
- > 20,000 results  → HIGH competition (score +0)

### Step 3: Demand Signals

For each niche, collect demand signals from Etsy search results:
- Number of favorites on top listings (visible in search cards)
- Presence of "Bestseller" badges
- Number of reviews on top 5 shops

Demand thresholds:
- Top listing > 500 favorites → HIGH demand (score +30)
- Top listing 100-500 favorites → MEDIUM demand (score +20)
- Top listing < 100 favorites → LOW demand (score +5)

### Step 4: Margin Calculation

Run the Python margin calculator for each shortlisted niche:
```bash
cd etsy-automation && python research/product_researcher.py "<niche>" <digital|pod|handmade>
```

Key margin rules:
- **Digital products**: ~75-80% margin after Etsy fees (no COGS)
- **Print-on-demand**: ~35-50% margin (Printify cost ~40% of sell price)
- **Handmade**: ~45-65% margin (materials ~25% of sell price)

### Step 5: Scoring & Ranking

Score each niche out of 100:
- Competition score (25 pts): LOW=25, MED=15, HIGH=5
- Demand score (35 pts): HIGH=35, MED=20, LOW=8
- Margin score (40 pts): >75%=40, 50-75%=25, <50%=10

### Step 6: Output

Return a ranked JSON report:
```json
{
  "top_opportunities": [
    {
      "rank": 1,
      "niche": "...",
      "product_type": "digital|pod|handmade",
      "competition": "LOW|MEDIUM|HIGH",
      "listing_count": 0,
      "avg_price_usd": 0.00,
      "demand_signal": "...",
      "estimated_margin_pct": 0,
      "net_profit_per_sale_usd": 0.00,
      "score": 0,
      "why": "One-sentence rationale"
    }
  ],
  "recommended_start": "Niche name",
  "recommended_product_type": "digital|pod|handmade",
  "recommended_price_usd": 0.00,
  "next_steps": ["..."]
}
```

## Notes

- Prioritize **digital products** first — zero COGS, instant delivery, infinitely scalable
- A niche with 500-5,000 listings and >200 avg favorites is the sweet spot
- Seasonal niches (e.g., holiday, wedding) have high demand windows — note the season
- If Etsy blocks the WebFetch request, fall back to web search for competition data
