# CLAUDE.md

**MANDATORY: Read `guides/meta.md` before doing ANYTHING else — no exceptions, no skipping even for simple tasks.**

## Guide Structure

All Claude guides follow two rules:
1. **Meta-rules and general skills** → `guides/` (one file per topic, read first)
2. **Task guides specific to a code directory** → a `GUIDE.md` in that directory

**When creating a new .md**: put it in `guides/` if it's general, next to the relevant code if directory-specific. Each file is completely and only what its name says — no overlap, no duplication between files.

## Task Routing

| Task | Read First |
|------|------------|
| Coverpoint/CSV work | `guides/csv-editing.md` → `generators/coverage/templates/GUIDE.md` |
| Custom test scripts (cp_custom_*.py) | `generators/testgen/scripts/custom/GUIDE.md` |
| Coverage workflow (isolate → build → analyze) | `generators/testgen/scripts/custom/COVERAGE-WORKFLOW.md` |
| Vector encodings, CSR fields, FP edge values | `guides/vector-reference.md` |
| Project architecture, commands, directory structure | `guides/architecture.md` |

## Project File Rules
- Only modify coverpoint template files unless explicitly instructed otherwise.
- CSVs: use `csv_edit.py` only when explicitly asked.
- For suggestions about other files: tell the user verbally, don't edit.

## Self-Improvement

**MANDATORY: When corrected or when you learn something new, update the relevant guide immediately — do not wait to be asked.** The routing table above tells you which file to update.
