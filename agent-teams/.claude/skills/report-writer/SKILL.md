---
name: report-writer
description: Appends a timestamped bullish stock signals section to agent-teams/output/signals.md. Receives a signals array and writes only HIGH and MEDIUM confidence entries as a markdown table.
allowed-tools: Write, Read, Bash
user-invocable: false
---

# Report Writer Skill

You receive a `signals` array from the calling context. Each element has these fields:

- `ticker` — stock ticker symbol (e.g. AAPL)
- `company` — full company name
- `sector` — market sector
- `signal_type` — one of: EARNINGS_BEAT | CONTRACT_WIN | REGULATORY_APPROVAL | PARTNERSHIP | DEMAND_SURGE | ANALYST_UPGRADE | PRODUCT_LAUNCH
- `confidence` — one of: HIGH | MEDIUM | LOW
- `headline` — the source headline that triggered the signal

## Instructions

### 1. Get the current timestamp

Run this bash command to get the timestamp:

```bash
date '+%Y-%m-%d %H:%M:%S GST'
```

Use the output as the section header timestamp.

### 2. Check whether the output file exists

Read `agent-teams/output/signals.md`. If the file does not exist or is empty, write it with this header first:

```
# Bullish Stock Signals Log
```

### 3. Filter signals

From the received `signals` array, keep only entries where `confidence` is `HIGH` or `MEDIUM`. Discard `LOW` confidence signals — do not include them in the output file.

If no HIGH or MEDIUM signals exist, append the timestamped section header with a note: `_No HIGH or MEDIUM confidence signals in this scan._`

### 4. Build the markdown section

Construct a new section using this format:

```markdown

## <TIMESTAMP>

| Ticker | Company | Sector | Signal | Confidence | Headline |
|--------|---------|--------|--------|------------|----------|
| AAPL   | Apple Inc. | Technology | PRODUCT_LAUNCH | HIGH | Apple unveils... |
```

- Sort rows: HIGH confidence first, then MEDIUM; within each group sort alphabetically by ticker.
- Truncate headlines longer than 80 characters with `…`.
- Use the exact `signal_type` value (e.g. `EARNINGS_BEAT`) in the Signal column.

### 5. Append to the file

Append the new section (starting with the blank line before `##`) to the end of `agent-teams/output/signals.md` using the Write tool. Do not overwrite existing content — read the current file contents first, then write the full updated content.
