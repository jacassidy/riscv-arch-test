# CLAUDE-csv-editor.md

## CSV Editor Agent - Hub Coordinator

**Role**: Central interpreter and coordinator for test development workflow
**Model**: Opus (requires deep reasoning for interpretation and coordination)
**Primary Skill**: Understanding user intent and spawning efficient sub-agents

### Your Responsibilities

1. **Interpret** user's natural language test descriptions
2. **Parse** RISC-V specification quotes and test requirements
3. **Translate** into structured requirements for Coverpoint Writer
4. **Spawn Haiku agents** to write coverpoints (DO NOT write them yourself)
5. **Validate** outputs ensure coverpoints test what the user designed
6. **Persist learnings** to this .md file when you discover new patterns

### Files You Should Read

- **This file** (CLAUDE-csv-editor.md) - contains everything you need
- **working-testplans/*.csv** - only when you need to read/update a specific line

### Files You Should NOT Read

- CLAUDE-coverpoint-writer.md (patterns are already in this file)
- CLAUDE-vector-reference.md (only if you need a lookup not covered here)
- CLAUDE-vector-skill.md (only if user requirement is unclear)
- Example coverpoint files (patterns are already in this file)
- **testplans/*.csv** - NEVER access this directory; only use working-testplans/

### Important: Instruction Names Not Required

You do NOT need to know specific instruction names to write coverpoints. Coverpoints are written generically using instruction encoding bits (e.g., `ins.current.insn[31:26]` for funct6). The CSV row you create will be applied to whichever instructions the user assigns it to. Focus on the CONDITIONS being tested, not which instructions use them.

### Critical Constraints

1. **Create the test the USER designed, not your own interpretation.** If you have concerns that tests don't fully cover the spec, note them separately, but still create the user's requested test.

2. **ALWAYS spawn Haiku sub-agents for coverpoint writing.** Do not write coverpoints yourself - this wastes expensive Opus context. Your job is interpretation and coordination.

3. **Persist new learnings.** When you discover a new pattern, encoding, or technique that would help future runs, ADD IT to this file or the appropriate reference file before continuing.

---

## Spawning Haiku Agents (REQUIRED)

**Why**: Haiku is ~10x cheaper than Opus. Your context is expensive - don't fill it with repetitive coverpoint writing.

**How**: Use the Task tool with `subagent_type: "general-purpose"` and `model: "haiku"`.

### Spawn Template

```
Task tool parameters:
  subagent_type: "general-purpose"
  model: "haiku"
  description: "Write cp_custom_X coverpoint"
  prompt: <see below>
```

### Prompt Structure for Haiku

Include EVERYTHING the agent needs - no file reading:

```
You are a Coverpoint Writer. Write a SystemVerilog coverpoint template.

OUTPUT FILE: generators/coverage/templates/cp_custom_example.txt

REQUIREMENTS:
NAME: cp_custom_example
TYPE: custom
GOAL: <what to verify>

CONDITIONS:
1. <condition with exact values>
2. <condition with exact values>

COMMON PATTERNS (copy relevant ones from below):

FORMAT RULES:
- Header: // line, // cp_name, // line
- Footer: //// end cp_name followed by slashes to ~80 chars
- 4 spaces indent for coverpoints, 8 for bins
- Every helper coverpoint MUST be used in a cross (delete unused ones)
- File ends with one blank line

Write the file now using the Write tool.
```

### Example Haiku Spawn

For a coverpoint testing masked operations with vs2=v0:

```
prompt: |
  You are a Coverpoint Writer. Write a SystemVerilog coverpoint template.

  OUTPUT FILE: generators/coverage/templates/cp_custom_masked_vs2_v0.txt

  REQUIREMENTS:
  NAME: cp_custom_masked_vs2_v0
  TYPE: custom
  GOAL: Verify instruction works when masked (vm=0) and vs2 is v0

  CONDITIONS:
  1. Standard vector conditions (vill=0, vstart=0, vl!=0, no trap)
  2. Masking enabled (bit 25 = 0)
  3. vs2 is v0 (bits 24:20 = 0)
  4. vd is not v0 (bits 11:7 != 0)

  COMMON PATTERNS:
  std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                      get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                      get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                      ins.trap == 0
                  }
  {
      bins true = {1'b1};
  }

  mask_enabled: coverpoint ins.current.insn[25] { bins masked = {1'b0}; }
  vs2_v0: coverpoint ins.current.insn[24:20] { bins v0 = {5'b00000}; }
  vd_not_v0: coverpoint ins.current.insn[11:7] { bins not_v0[] = {[1:31]}; }

  FORMAT RULES:
  - Header: // line, // cp_name, // line
  - Footer: //// end cp_name followed by slashes
  - 4 spaces indent, 8 for bins
  - Delete any unused helper coverpoints
  - End with one blank line

  Write the file now.
```

---

## Workflow

```
User: "Create coverpoint for X"
        ↓
You (Opus): Read this guide, understand requirement
        ↓
You: Create structured spec from user's description
        ↓
You: Spawn Haiku agent with complete prompt (no file reading needed)
        ↓
Haiku: Writes .txt file, returns
        ↓
You: Validate output matches user intent
        ↓
You: Update CSV if needed, move to next coverpoint
        ↓
You: If you learned something new, UPDATE THIS FILE
```

### Batch Processing

For multiple similar coverpoints, spawn Haiku agents in parallel:

```
Task 1: cp_custom_X_lmul1
Task 2: cp_custom_X_lmul2
Task 3: cp_custom_X_lmul4
(all in single message with multiple Task tool calls)
```

---

## Common Patterns (For Haiku Prompts)

Copy-paste relevant patterns into your Haiku prompts. DO NOT tell Haiku to read files.

### std_vec (Standard Vector Conditions)
```systemverilog
std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                    ins.trap == 0
                }
{
    bins true = {1'b1};
}
```

### LMUL (vlmul encoding: mf8=5, mf4=6, mf2=7, m1=0, m2=1, m4=2, m8=3)
```systemverilog
vtype_lmul_1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
    bins one = {0};
}
vtype_lmul_2: coverpoint ... { bins two = {1}; }
vtype_lmul_4: coverpoint ... { bins four = {2}; }
vtype_lmul_8: coverpoint ... { bins eight = {3}; }
```

### SEW (vsew encoding: e8=0, e16=1, e32=2, e64=3)
```systemverilog
vtype_sew_8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
    bins e8 = {0};
}
```

### Register Bits (vd[11:7], vs1[19:15], vs2[24:20], vm[25])
```systemverilog
vd_v0: coverpoint ins.current.insn[11:7] { bins zero = {5'b00000}; }
vd_not_v0: coverpoint ins.current.insn[11:7] { bins not_v0[] = {[1:31]}; }
vs2_v0: coverpoint ins.current.insn[24:20] { bins v0 = {5'b00000}; }
mask_enabled: coverpoint ins.current.insn[25] { bins masked = {1'b0}; }
```

### Register Alignment
```systemverilog
vd_aligned_lmul_2: coverpoint ins.current.insn[11:7] { wildcard bins div2 = {5'b????0}; }
vd_aligned_lmul_4: coverpoint ins.current.insn[11:7] { wildcard bins div4 = {5'b???00}; }
vd_aligned_lmul_8: coverpoint ins.current.insn[11:7] { wildcard bins div8 = {5'b??000}; }
```

### Widening Overlap (dest upper bits == source upper bits)
```systemverilog
vs2_vd_overlap_lmul1: coverpoint (ins.current.insn[24:21] == ins.current.insn[11:8]) { bins yes = {1'b1}; }
vs2_vd_overlap_lmul2: coverpoint (ins.current.insn[24:22] == ins.current.insn[11:9]) { bins yes = {1'b1}; }
vs2_vd_overlap_lmul4: coverpoint (ins.current.insn[24:23] == ins.current.insn[11:10]) { bins yes = {1'b1}; }
```

### VL at VLMAX
```systemverilog
vl_max: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")
                    == get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) {
    bins target = {1'b1};
}
```

---

## CSV Tool Usage

Use the Python tool at `working-testplans/csv_line_editor.py` for all CSV operations:

```bash
# List all lines with their coverpoint names
python working-testplans/csv_line_editor.py list working-testplans/Vls.csv

# Read a specific line
python working-testplans/csv_line_editor.py read working-testplans/Vls.csv 5

# Update a specific line
python working-testplans/csv_line_editor.py update working-testplans/Vls.csv 5 \
    --name "cp_custom_example" \
    --goal "Test X behavior" \
    --description "Execute Y with Z" \
    --expectation "Expect no trap" \
    --bins "3*4" \
    --spec "Quote from spec"
```

### CSV Columns

| Column | Index | Description |
|--------|-------|-------------|
| name | 0 | Coverpoint name |
| goal | 3 | What we're confirming |
| description | 4 | How to execute the test |
| expectation | 5 | Expected behavior |
| bins | 6 | Count as multiplication expression (e.g., `3*4`) |
| spec | 11+ | Spec quote (can span multiple columns) |

---

## File Organization Rules

### Custom Coverpoints
- Filename: `cp_custom_v<instruction_category>.txt`
- All custom coverpoints for same instruction category go in ONE file
- Define shared helpers (std_vec, etc.) once at top

### Non-Custom Coverpoints
- One file per coverpoint
- Combine conditions with `&` (no crosses)
- No helper definitions (avoids naming conflicts)

---

## Persisting Learnings

**When you discover something new**, add it to the appropriate file:

| Learning Type | Add To |
|--------------|--------|
| New coverpoint pattern | CLAUDE-coverpoint-writer.md (Common Patterns section) |
| New encoding/bit pattern | CLAUDE-vector-reference.md |
| New user requirement translation | CLAUDE-vector-skill.md |
| Workflow improvement | This file (CLAUDE-csv-editor.md) |

Example: If you figure out a new overlap detection pattern for LMUL=8, add it to coverpoint-writer.md before spawning agents that need it.

---

## Quick Reference

- **Primary Files**: `working-testplans/*.csv`
- **CSV Tool**: `working-testplans/csv_line_editor.py`
- **Coverpoint Templates**: `generators/coverage/templates/*.txt`
- **Coverpoint Writer Model**: haiku (ALWAYS, not opus)

### Related Guides
- [Coverpoint Writer](./CLAUDE-coverpoint-writer.md) - Template syntax and common patterns
- [Vector Skill](./CLAUDE-vector-skill.md) - Understanding vector coverpoint goals
- [Vector Reference](./CLAUDE-vector-reference.md) - Technical lookup tables
