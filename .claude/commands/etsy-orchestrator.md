---
description: Run AI-powered Etsy shop management — research winning products, create listings, handle customer messages, or pull analytics
model: sonnet
---

# Etsy Shop Orchestrator

Coordinate the AI agents that run your Etsy shop.

## Step 1: Ask What to Do

Use the AskUserQuestion tool to ask:

**Question**: "What would you like to do with your Etsy shop today?"

**Options**:
1. **Research** — Find winning products with the best margins (great for starting out)
2. **Create Listing** — Generate and post an optimized product listing
3. **Customer Service** — Draft or send replies to buyer messages
4. **Analytics** — Pull shop performance report and get recommendations
5. **Full Run** — Do all of the above in sequence

## Step 2: Execute the Chosen Task

### Research Mode

Use the Task tool to invoke the research agent:
```
Task(
  subagent_type="etsy-research-agent",
  description="Find top 5 winning Etsy product niches",
  prompt="Use your preloaded etsy-market-research skill to research top Etsy product opportunities for 2025. Focus on digital products first, then POD. Return the full ranked JSON report plus a plain-English summary."
)
```

Wait for the report. Present the top 3 opportunities to the user.

### Create Listing Mode

Ask the user for:
- Product name/description
- Product type (digital / POD / handmade)
- Price point
- Whether to post live (default: dry run)

Then invoke:
```
Task(
  subagent_type="etsy-listing-agent",
  description="Create SEO-optimized Etsy listing",
  prompt="Create a listing for: <product>. Type: <type>. Price: $<price>. Context: <context>. [Live: true/false]"
)
```

### Customer Service Mode

Ask the user:
- Draft only, or send replies automatically?
- Brief shop description (for context)

Then invoke:
```
Task(
  subagent_type="etsy-customer-service-agent",
  description="Handle unread Etsy messages",
  prompt="Mode: <draft|send>. Shop context: <description>. Handle all unread conversations."
)
```

Show the user the drafted replies before confirming sends.

### Analytics Mode

Ask the user how many days to include (default: 30).

Then invoke:
```
Task(
  subagent_type="etsy-analytics-agent",
  description="Generate Etsy shop performance report",
  prompt="Generate a performance report for the last <days> days. Include top listings, margin analysis, and 3-5 ranked action items."
)
```

### Full Run Mode

Execute all four agents sequentially:
1. Analytics (understand current state)
2. Research (if new niches needed)
3. Customer Service (clear inbox)
4. Present a combined summary

## Step 3: Summary

After all tasks complete, present a clean summary:
- What was done
- Key findings or actions taken
- Suggested next step

## Critical Rules

1. **Use Task tool** for all agent invocations — never bash commands
2. **Sequential execution** — one agent at a time (they share resources)
3. **Confirm before sending** customer service replies
4. **Confirm before posting** live listings
5. **Setup reminder**: If ETSY_API_KEY is not configured, guide the user to `etsy-automation/.env.example`
