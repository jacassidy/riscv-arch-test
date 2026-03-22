# CLAUDE.md

## Meta-Rules (Most Important — Read First)
- **Catch issues early**: Identify blockers and ambiguities before starting. Mistakes cost 10x more to fix later.
- **Never repeat mistakes**: When corrected, immediately update the relevant .md guide with a rule preventing recurrence. Don't rely on memory alone — write it where the next Claude will read it.
- **Document new structure**: Any new pipeline, tool, or workflow component → create a guide .md before finishing the task.
- **No sunk cost**: If a better approach appears mid-task, switch. Don't finish bad paths to avoid "wasting" prior work.
- **Read guides before exploring**: Task-specific guides exist for everything common in this project. Read them. Never explore raw code when a guide exists.

## Task Routing
| Task | Read First |
|------|------------|
| Coverpoint/CSV work | `CLAUDE-csv-editor.md` → `CLAUDE-coverpoint-writer.md` |
| Custom test scripts (cp_custom_*.py) | `generators/testgen/scripts/custom/CLAUDE-custom-testgen.md` |
| Coverage workflow (isolate → build → analyze) | `generators/testgen/scripts/custom/CLAUDE-coverage-workflow.md` |
| Vector encoding, CSR fields | `CLAUDE-vector-reference.md` |
| Understanding test goals | `CLAUDE-vector-skill.md` |
| Coverpoint syntax reference | `CLAUDE-coverpoint-reference.md` |
| Test writer patterns | `CLAUDE-test-writer.md` |
| Project architecture, commands, directory structure | `CLAUDE-architecture.md` |

## Planning
- Enter plan mode for any non-trivial task (3+ steps or architectural decisions).
- Stop and re-plan immediately if something goes sideways — don't keep pushing.
- Every plan includes a research summary: what was searched, what was useful, what to skip.
- Clear context between independent plan sections — each starts fresh without prior baggage.

## Self-Improvement
- After any user correction: update the relevant .md guide with a rule preventing recurrence.
- After learning something that would have saved significant time: log it in the guide that would be read if this task recurred.

## Verification
- Never mark a task complete without proving it works (run tests, check logs, demonstrate correctness).
- For bug fixes: point at logs/errors, resolve, then verify. No hand-holding needed.

## Multi-Claude Management (Lateral Model)
- Think **rings**, not triangles. Inner Claudes manage broader scope; outer Claudes handle focused tasks.
- Any Claude managing sub-Claudes must fully understand (at high level) what every sub-Claude is doing.
- Minimize prompts to inner/expensive Claudes — be frugal. But when you need them, be confident and provide full context.
- Managers of managers must understand the entirety of all sub-managed Claudes' work.

## File Modification Rules
- Only modify coverpoint template files unless explicitly instructed otherwise.
- CSVs: use `csv_edit.py` only when explicitly asked.
- For suggestions about other files: tell the user verbally, don't edit.
