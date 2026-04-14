# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a best practices repository for Claude Code configuration, demonstrating patterns for skills, subagents, hooks, and commands. It serves as a reference implementation rather than an application codebase.

## Key Components

### Weather System (Example Workflow)
A demonstration of two distinct skill patterns via the **Command → Agent → Skill** architecture:
- `/weather-orchestrator` command (`.claude/commands/weather-orchestrator.md`): Entry point — asks user for C/F, invokes agent, then invokes SVG skill
- `weather-agent` agent (`.claude/agents/weather-agent.md`): Fetches temperature using its preloaded `weather-fetcher` skill (agent skill pattern)
- `weather-fetcher` skill (`.claude/skills/weather-fetcher/SKILL.md`): Preloaded into agent — instructions for fetching temperature from Open-Meteo
- `weather-svg-creator` skill (`.claude/skills/weather-svg-creator/SKILL.md`): Skill — creates SVG weather card, writes `orchestration-workflow/weather.svg` and `orchestration-workflow/output.md`

Two skill patterns: agent skills (preloaded via `skills:` field) vs skills (invoked via `Skill` tool). See `orchestration-workflow/orchestration-workflow.md` for the complete flow diagram.

### Agent Teams Demo (`agent-teams/`)
A self-contained sub-project demonstrating the same Command → Agent → Skill architecture for Dubai time. It has its own `.claude/` directory and runs independently via `cd agent-teams && claude`. Do NOT modify `agent-teams/.claude/` from the repo root — treat it as a separate project. Created by an agent team of three parallel subagents (Command Architect, Agent Engineer, Skill Designer).

### Agents (`.claude/agents/`)
- `weather-agent.md`: Fetches Dubai temperature (preloaded: `weather-fetcher`; model: sonnet; memory: project)
- `time-agent.md`: Displays Pakistan Standard Time in PKT/UTC+5 (model: haiku; maxTurns: 3)
- `presentation-curator.md`: Manages all presentation edits — **always delegate presentation work here** (preloaded: 3 presentation skills; model: sonnet). See `.claude/rules/presentation.md`.
- `development-workflows-research-agent.md`: Researches Claude Code workflow repos on GitHub — fetches star counts, agent/skill/command counts, and uniqueness tags (model: sonnet; permissionMode: bypassPermissions)

### Skills (`.claude/skills/`)
- `weather-fetcher/`: Agent-preloaded — Open-Meteo temperature fetch instructions
- `weather-svg-creator/`: SVG weather card creator (writes `orchestration-workflow/weather.svg`)
- `time-skill/`: Displays current PKT time (user-invocable)
- `agent-browser/`: Browser automation CLI — navigate, snapshot, click, fill, screenshot (allowed-tools: `Bash(agent-browser:*)`)
- `presentation/vibe-to-agentic-framework/`: Framework narrative for presentation slides
- `presentation/presentation-structure/`: Slide format, level system, section structure
- `presentation/presentation-styling/`: CSS classes, syntax highlighting patterns

### Commands (`.claude/commands/`)
- `weather-orchestrator.md`: Orchestrates the weather workflow (C/F → agent → SVG)
- `time-command.md`: Displays current PKT time
- `workflows/development-workflows.md`: Updates DEVELOPMENT WORKFLOWS table in README via 2 parallel research agents
- `workflows/best-practice/workflow-claude-subagents.md`: Tracks subagents doc drift
- `workflows/best-practice/workflow-claude-commands.md`: Tracks commands doc drift
- `workflows/best-practice/workflow-claude-settings.md`: Tracks settings doc drift
- `workflows/best-practice/workflow-claude-skills.md`: Tracks skills doc drift
- `workflows/best-practice/workflow-concepts.md`: Updates README CONCEPTS section

### MCP Servers (`.mcp.json`)
Three project-level MCP servers: `playwright` (browser automation), `context7` (library docs lookup), `deepwiki` (deep wiki search).

### Hooks System
Cross-platform sound notification system in `.claude/hooks/`:
- `scripts/hooks.py`: Main handler for all Claude Code hook events
- `config/hooks-config.json`: Shared team configuration
- `config/hooks-config.local.json`: Personal overrides (git-ignored)
- `sounds/`: Audio files organized by hook event (generated via ElevenLabs TTS)

All **27 hook events** are wired in `.claude/settings.json`: PreToolUse, PermissionRequest, PostToolUse, PostToolUseFailure, UserPromptSubmit, Notification, Stop, SubagentStart, SubagentStop, PreCompact, PostCompact, SessionStart, SessionEnd, Setup, TeammateIdle, TaskCreated, TaskCompleted, ConfigChange, WorktreeCreate, WorktreeRemove, InstructionsLoaded, Elicitation, ElicitationResult, StopFailure, CwdChanged, FileChanged, PermissionDenied.

Special: git commits trigger `pretooluse-git-committing` sound. Hooks 15-17 (TeammateIdle, TaskCreated, TaskCompleted) require `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

### Skill Definition Structure
Skills in `.claude/skills/<name>/SKILL.md` use YAML frontmatter:
- `name`: Display name and `/slash-command` (defaults to directory name)
- `description`: When to invoke (recommended for auto-discovery)
- `argument-hint`: Autocomplete hint (e.g., `[issue-number]`)
- `disable-model-invocation`: Set `true` to prevent automatic invocation
- `user-invocable`: Set `false` to hide from `/` menu (background knowledge only)
- `allowed-tools`: Tools allowed without permission prompts when skill is active
- `model`: Model to use when skill is active
- `context`: Set to `fork` to run in isolated subagent context
- `agent`: Subagent type for `context: fork` (default: `general-purpose`)
- `hooks`: Lifecycle hooks scoped to this skill

## Critical Patterns

### Subagent Orchestration
Subagents **cannot** invoke other subagents via bash commands. Use the Agent tool (renamed from Task in v2.1.63; `Task(...)` still works as an alias):
```
Agent(subagent_type="agent-name", description="...", prompt="...", model="haiku")
```

Be explicit about tool usage in subagent definitions. Avoid vague terms like "launch" that could be misinterpreted as bash commands.

### Subagent Definition Structure
Subagents in `.claude/agents/*.md` use YAML frontmatter:
- `name`: Subagent identifier
- `description`: When to invoke (use "PROACTIVELY" for auto-invocation)
- `tools`: Comma-separated allowlist of tools (inherits all if omitted). Supports `Agent(agent_type)` syntax
- `disallowedTools`: Tools to deny, removed from inherited or specified list
- `model`: Model alias: `haiku`, `sonnet`, `opus`, or `inherit` (default: `inherit`)
- `permissionMode`: Permission mode (e.g., `"acceptEdits"`, `"plan"`, `"bypassPermissions"`)
- `maxTurns`: Maximum agentic turns before the subagent stops
- `skills`: List of skill names to preload into agent context
- `mcpServers`: MCP servers for this subagent (server names or inline configs)
- `hooks`: Lifecycle hooks scoped to this subagent (all hook events are supported; `PreToolUse`, `PostToolUse`, and `Stop` are the most common)
- `memory`: Persistent memory scope — `user`, `project`, or `local` (see `reports/claude-agent-memory.md`)
- `background`: Set to `true` to always run as a background task
- `effort`: Effort level override: `low`, `medium`, `high`, `max` (default: inherits from session)
- `isolation`: Set to `"worktree"` to run in a temporary git worktree
- `color`: CLI output color for visual distinction

### Configuration Hierarchy
1. **Managed** (`managed-settings.json` / MDM plist / Registry): Organization-enforced, cannot be overridden
2. Command line arguments: Single-session overrides
3. `.claude/settings.local.json`: Personal project settings (git-ignored)
4. `.claude/settings.json`: Team-shared settings
5. `~/.claude/settings.json`: Global personal defaults
6. `hooks-config.local.json` overrides `hooks-config.json`

Notable settings in this repo's `.claude/settings.json`: `outputStyle: "Explanatory"`, `plansDirectory: "./reports"`, `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: "80"` (auto-compact at 80% context).

### Disable Hooks
Set `"disableAllHooks": true` in `.claude/settings.local.json`, or disable individual hooks in `hooks-config.json`.

## Answering Best Practice Questions

When the user asks a Claude Code best practice question, **always search this repo first** (`best-practice/`, `reports/`, `tips/`, `implementation/`, and `README.md`) before relying on training knowledge or external sources. This repo is the authoritative source — only fall back to external docs or web search if the answer is not found here.

## Workflow Best Practices

From experience with this repository:

- Keep CLAUDE.md under 200 lines per file for reliable adherence
- Use commands for workflows instead of standalone agents
- Create feature-specific subagents with skills (progressive disclosure) rather than general-purpose agents
- Perform manual `/compact` at ~50% context usage
- Start with plan mode for complex tasks
- Use human-gated task list workflow for multi-step tasks
- Break subtasks small enough to complete in under 50% context

### Debugging Tips

- Use `/doctor` for diagnostics
- Run long-running terminal commands as background tasks for better log visibility
- Use browser automation MCPs (Claude in Chrome, Playwright, Chrome DevTools) for Claude to inspect console logs
- Provide screenshots when reporting visual issues

## Git Commit Rules

When committing changes, **create separate commits per file**. Do NOT bundle multiple file changes into a single commit. Each file gets its own commit with a descriptive message specific to that file's changes.

For example, if `README.md`, `best-practice/claude-subagents.md`, and a skill file all changed:
- Commit 1: `git add README.md` → commit with README-specific message
- Commit 2: `git add best-practice/claude-subagents.md` → commit with subagents-doc-specific message
- Commit 3: `git add .claude/skills/weather-fetcher/SKILL.md` → commit with skill-specific message

This makes the git history cleaner and easier to review, revert, or cherry-pick individual changes.

## Documentation

See `.claude/rules/markdown-docs.md` for documentation standards. Key docs:
- `best-practice/claude-subagents.md`: Subagent frontmatter, hooks, and repository agents
- `best-practice/claude-commands.md`: Slash command patterns and built-in command reference
- `orchestration-workflow/orchestration-workflow.md`: Weather system flow diagram
- `reports/claude-agent-memory.md`: Agent memory scope patterns
- `reports/claude-skills-for-larger-mono-repos.md`: Skills in monorepo subdirectories
