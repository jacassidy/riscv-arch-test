# meta.md — Behavioral Rules for Claude

This file is portable — copy it to any project as the starting point. It defines how Claude should behave and manage guides. Project-specific rules go in CLAUDE.md.

## Guide Management (Highest Priority)

**The guide system is the most important ongoing responsibility.** A Claude instance cannot assume any other instance has access to the same conversation. Everything relevant learned in a session must be written down.

### Structure
- **General behavioral rules and skills** → `guides/` (this folder)
- **Task guides specific to a directory** → a `GUIDE.md` in that directory, next to the code it describes
- **Each file is completely and only what its name says** — no overlap, no duplication. If content already exists somewhere, reference it rather than copying it.

### When to create or update a guide
- After any user correction: update the guide covering that task with a rule preventing recurrence.
- After learning something that would have saved significant time: add it to whichever guide would be read if this situation recurs.
- After building any new pipeline, tool, or workflow component: create or update its guide before finishing.
- **Be frugal**: don't create a guide for something trivial or already covered. Don't pad existing guides with noise.
- **Be confident**: when something IS worth recording, write it thoroughly and precisely — the next Claude will rely on it completely.

### What NOT to write down
- Ephemeral task state (in-progress work, current step) — use task lists for that
- Things derivable from reading the code or git history
- Things already in another guide — update that guide instead

## Planning
- Enter plan mode for any non-trivial task (3+ steps or architectural decisions).
- Stop and re-plan immediately if something goes sideways — don't keep pushing.
- Every plan includes a research summary: what was searched, what was useful, what to skip.
- Clear context between independent plan sections — each starts fresh without prior baggage.
- **Minimal reads rule**: Read only what is needed to answer the question or write the plan. Workflow guides + progress files = enough context for planning. Implementation references (GUIDE.md, knowledge.md, templates) are for when you are writing code — not for planning.

## Verification
- Never mark a task complete without proving it works (run tests, check logs, demonstrate correctness).
- For bug fixes: point at logs/errors, resolve, then verify. No hand-holding needed.

## Multi-Claude Management (Lateral Model)
- Think **rings**, not triangles. Inner Claudes manage broader scope; outer Claudes handle focused tasks.
- Any Claude managing sub-Claudes must fully understand (at high level) what every sub-Claude is doing.
- Minimize prompts to inner/expensive Claudes — be frugal. But when you need them, be confident and provide full context.
- Managers of managers must understand the entirety of all sub-managed Claudes' work.

## User Preferences

Preferences are tracked in `guides/user-preferences/` — one file per topic (e.g., `general.md`, `workflow.md`). They describe the user, not the codebase; keep them separate from task guides.

- **Read** the relevant file before starting any task it covers. You should not need to be told twice.
- **Write** whenever a new preference is learned — correction, confirmed approach, or stated preference. Create a new file if no existing one fits. Be specific; vague entries are useless.
- Each entry: state the preference, add a brief *Why:* if the reason was given.

## General Approach
- Catch issues early: identify blockers and ambiguities before starting. Mistakes cost 10x more to fix later.
- No sunk cost: if a better approach appears mid-task, switch. Don't finish bad paths.
- Read the relevant guide before exploring raw code. Guides exist for all common tasks in this project.
- For suggestions about files outside your task scope: tell the user verbally, don't edit.
