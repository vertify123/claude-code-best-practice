---
name: stock-analyzer
description: Preloaded analysis framework for identifying bullish stock signals from financial news headlines
user-invocable: false
---

This skill provides the analysis framework used by the `stock-analyst-agent` to evaluate financial news headlines and produce structured bullish signal output.

## Bullish Signal Detection Rules

For each headline, check for these patterns to assign a `signal_type`:

- **EARNINGS_BEAT**: "beat estimates", "topped expectations", "raised guidance", "record revenue", "record profit", "blew past forecasts", "exceeded analyst expectations"
- **CONTRACT_WIN**: "awarded contract", "wins deal", "selected by", "chosen for", "government contract", "multi-year agreement", "sole-source contract"
- **REGULATORY_APPROVAL**: "FDA approved", "FDA approval", "FCC approved", "cleared by", "authorized", "green light", "receives approval", "granted approval"
- **PARTNERSHIP**: "partnership with", "collaboration with", "joint venture", "strategic deal", "strategic alliance", "acquisition target", "merger talks", "buyout rumors"
- **DEMAND_SURGE**: "demand surge", "capacity expansion", "supply shortage", "record orders", "backlog grows", "order book swells", "production ramp", "sold out"
- **ANALYST_UPGRADE**: "upgrade to buy", "upgraded to buy", "raised price target", "outperform rating", "strong buy", "initiates coverage", "bullish on", "overweight rating"
- **PRODUCT_LAUNCH**: "launches", "unveils", "announces new product", "breakthrough product", "next-generation", "introduces", "debuts", "shipping now"

If a headline matches multiple patterns, choose the most specific and highest-impact `signal_type`.

## Key Tickers by Sector

Use this reference to quickly identify likely ticker symbols when a company name appears in a headline:

| Sector | Tickers |
|--------|---------|
| AI & Semiconductors | NVDA, AMD, TSMC, ARM, SMCI, INTC, AVGO, ANET |
| Defense & Aerospace | LMT, RTX, NOC, GD, PLTR, LDOS, BAH, HII |
| Nuclear & Clean Energy | CEG, VST, NRG, CCJ, OKLO, NNE, SMR, ETN |
| Biotech & Healthcare | LLY, NVO, MRNA, AMGN, VRTX, REGN, GILD, ABBV |
| Cybersecurity | CRWD, PANW, ZS, FTNT, S, OKTA, CYBR |
| Infrastructure & Industrials | CAT, DE, PWR, VMC, MLM, EMR, ETN, HUBB |
| Fintech & Financial | JPM, GS, MS, COIN, SQ, PYPL, V, MA |

This list is a reference guide, not exhaustive. If a company is clearly identifiable but not listed here, use the correct ticker.

## Confidence Calibration

| Level | When to use |
|-------|-------------|
| **HIGH** | Named company + clear direct catalyst. Example: "NVIDIA wins $2B AWS contract" → NVDA, CONTRACT_WIN, HIGH |
| **MEDIUM** | Sector-level news without a named company, or the company benefits indirectly. Example: "AI chip demand expected to double in 2025" → NVDA/AMD, DEMAND_SURGE, MEDIUM |
| **LOW** | Vague macro news with no direct company link, or the signal requires multiple inferential leaps. Example: "Tech sector may benefit from rate cuts" → LOW |

## Omission Rules

- **Omit bearish headlines entirely** — do not include them in output even with LOW confidence
- **Omit duplicates** — if the same ticker appears with the same signal_type from multiple headlines, keep only the highest-confidence entry
- **Omit unidentifiable companies** — if you cannot determine the ticker even after a WebSearch, omit the signal rather than guessing

## Output Reminder

Return structured JSON matching the format specified in the `stock-analyst-agent` instructions. Do not include explanatory text outside the JSON object.
