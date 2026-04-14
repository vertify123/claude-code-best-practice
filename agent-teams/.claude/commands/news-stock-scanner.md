---
model: sonnet
---

# News & Stock Scanner

> Run this command via `/loop 30m /news-stock-scanner` to scan continuously throughout the day

This command orchestrates a three-step pipeline: fetch bullish headlines across 7 sectors, analyse them for bullish stock signals, then append findings to the signals log.

## Step 1 — Fetch Headlines

Invoke the `news-fetcher-agent` to retrieve bullish headlines across these sectors: Technology, Energy, Healthcare, Financials, Consumer Discretionary, Industrials, Materials.

Use the Agent tool (NOT bash):

```
Agent(
  subagent_type="news-fetcher-agent",
  description="Fetch bullish headlines across 7 market sectors",
  prompt="Fetch the latest headlines across these 7 sectors: AI & Semiconductors, Defense & Aerospace, Nuclear & Clean Energy, Biotech & Healthcare, Cybersecurity, Infrastructure & Industrials, Fintech & Financial. Return a JSON object with this exact structure: { \"headlines\": [ { \"sector\": \"<sector>\", \"headline\": \"<headline text>\", \"source\": \"<publication name>\", \"url\": \"<article url>\" } ] }. Aim for 3-5 headlines per sector (20-35 total). Do NOT filter — return all notable headlines regardless of sentiment."
)
```

Capture the full JSON response from the agent. This is the `headlines_payload`.

## Step 2 — Analyse for Stock Signals

Pass the complete `headlines_payload` JSON from Step 1 to the `stock-analyst-agent` via the Agent tool (NOT bash):

```
Agent(
  subagent_type="stock-analyst-agent",
  description="Identify bullish stock signals from headlines",
  prompt="You are receiving a JSON payload of bullish market headlines. Analyse each headline and identify specific stock tickers that show bullish signals.\n\nHeadlines payload:\n<headlines_payload>\n[INSERT FULL JSON FROM STEP 1 HERE]\n</headlines_payload>\n\nReturn a JSON object with this exact structure: { \"signals\": [ { \"ticker\": \"<TICKER>\", \"company\": \"<Company Name>\", \"sector\": \"<sector>\", \"signal_type\": \"<signal_type>\", \"confidence\": \"<confidence>\", \"headline\": \"<the headline that triggered this signal>\" } ] }\n\nAllowed signal_type values: EARNINGS_BEAT | CONTRACT_WIN | REGULATORY_APPROVAL | PARTNERSHIP | DEMAND_SURGE | ANALYST_UPGRADE | PRODUCT_LAUNCH\nAllowed confidence values: HIGH | MEDIUM | LOW\n\nOnly include signals where you can identify a specific publicly traded ticker. Assign confidence based on how directly and clearly the headline implies a bullish move for that stock."
)
```

Capture the full JSON response. This is the `signals_payload`.

## Step 3 — Write Report

Invoke the `report-writer` skill via the Skill tool, passing the signals from Step 2:

```
Skill("report-writer", signals_payload)
```

The skill will append a timestamped section containing only HIGH and MEDIUM confidence signals to `agent-teams/output/signals.md`.

## Step 4 — Print Summary

After the skill completes, print a summary table of all signals found (HIGH, MEDIUM, and LOW) in this format:

```
Scan complete. X signals identified (Y HIGH, Z MEDIUM, W LOW).

| Ticker | Company | Sector | Signal | Confidence |
|--------|---------|--------|--------|------------|
| ...    | ...     | ...    | ...    | ...        |
```

Sort the table by confidence (HIGH first, then MEDIUM, then LOW), then alphabetically by ticker within each confidence group.
