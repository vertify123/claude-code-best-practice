---
description: Open the Etsy AI Command Center — see shop metrics, agent status, recent activity, and AI-powered action items
model: haiku
---

# Etsy AI Command Center

Show a live overview of the Etsy shop and all running agents.

## Workflow

### Step 1: Launch the Dashboard Agent

Use the Task tool to invoke the dashboard agent:

```
Task(
  subagent_type="etsy-dashboard-agent",
  description="Generate Etsy command center snapshot",
  prompt="Run the command center dashboard. Show the rich TUI output first, then add your AI insights section. If no activity log exists yet, explain how to get started."
)
```

Wait for the agent to return the full dashboard output.

### Step 2: Show the Output

Present the agent's output verbatim (it includes the rich dashboard + AI insights).

### Step 3: Offer Next Actions

After the dashboard, ask the user:

Use the AskUserQuestion tool:
**Question**: "What would you like to do next?"
**Options**:
1. **Run research** — Find new winning product niches
2. **Handle messages** — Reply to buyer conversations
3. **Create a listing** — Post a new product
4. **View analytics** — Deep-dive into revenue data
5. **Watch mode** — Run the live-refresh dashboard in terminal

If the user picks **Watch mode**, tell them to run:
```
cd etsy-automation && python dashboard/command_center.py --watch
```
(Claude can't run persistent processes — this must be done in a terminal.)

## Critical Rules

1. **Use Task tool** — never bash the dashboard script directly from the command
2. **Let the agent handle the display** — don't re-summarize what it already shows
3. **Watch mode is terminal-only** — explain this clearly if user picks it
