---
name: news-fetcher
description: Preloaded skill for news-fetcher-agent — provides sector search queries and return format
user-invocable: false
---

This skill is preloaded into the `news-fetcher-agent`. It defines the 7 market sectors, their WebSearch queries, and the required return format.

## Sectors and Search Queries

Run **2-3 WebSearch queries** per sector using the queries listed below. Collect all results before moving to the next sector.

| Sector | Search Queries |
|--------|----------------|
| AI & Semiconductors | "AI chip demand news today", "semiconductor earnings beat", "data center expansion announcement" |
| Defense & Aerospace | "defense contract award today", "aerospace earnings results", "Pentagon procurement news" |
| Nuclear & Clean Energy | "nuclear power plant deal", "energy demand AI data center", "electricity grid investment" |
| Biotech & Healthcare | "FDA drug approval today", "GLP-1 obesity drug news", "biotech clinical trial results" |
| Cybersecurity | "cybersecurity contract government", "cyber company earnings beat", "security breach drives demand" |
| Infrastructure & Industrials | "infrastructure contract awarded", "industrial earnings beat", "grid modernization spending" |
| Fintech & Financial | "fintech earnings results", "crypto regulation clarity", "payment company partnership" |

## Search Instructions

1. Work through all 7 sectors sequentially.
2. For each sector, run 2-3 of the listed WebSearch queries.
3. From each query result, extract notable headlines — aim for 3-5 headlines per sector.
4. Record the headline text, source name, and URL for each result.

## Return Format

After searching all 7 sectors, return ONLY the following JSON object with no surrounding prose:

```json
{
  "headlines": [
    { "sector": "AI & Semiconductors", "headline": "...", "source": "...", "url": "..." },
    { "sector": "Defense & Aerospace", "headline": "...", "source": "...", "url": "..." },
    { "sector": "Nuclear & Clean Energy", "headline": "...", "source": "...", "url": "..." },
    { "sector": "Biotech & Healthcare", "headline": "...", "source": "...", "url": "..." },
    { "sector": "Cybersecurity", "headline": "...", "source": "...", "url": "..." },
    { "sector": "Infrastructure & Industrials", "headline": "...", "source": "...", "url": "..." },
    { "sector": "Fintech & Financial", "headline": "...", "source": "...", "url": "..." }
  ]
}
```

Target: **20-35 total headlines** (3-5 per sector minimum).

## Critical Rule

Include ALL notable headlines found. Do NOT filter for bullishness, positive sentiment, or relevance to any specific stock. Return everything — the stock-analyst-agent is responsible for filtering and scoring.
