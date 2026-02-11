# CLAUDE-csv-editor.md

## CSV Editor Agent

**Role**: Process individual CSV coverpoint lines and write coverpoint templates
**Invocation**: Fresh instance launched per CSV line via `process_csv.py`
**Context**: NONE from previous lines - only this file and other .md files

---

## CRITICAL: Stateless Processing

**You are launched fresh for EACH CSV line.** There is NO conversation history from previous lines.

- Your ONLY knowledge comes from reading .md files
- If you learn something useful, you MUST add it to the appropriate .md file BEFORE finishing
- The next line will be processed by a completely new Claude instance
- Do NOT assume any context - read this file every time

---

## Your Task (Every Invocation)

1. **Read this file** - contains all patterns you need
2. **Check if template exists** at `generators/coverage/templates/<name>.txt`
3. **If missing, create it** following the format rules below
4. **Validate** the template matches the CSV row's goal/description
5. **Persist learnings** - if you discover a new pattern, ADD IT to this file

---

## Coverpoint Template Format

**Location**: `generators/coverage/templates/<coverpoint_name>.txt`

**NEVER include `covergroup`/`endgroup`** - files are pasted into existing covergroup.

### Template Structure

```systemverilog
// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_name_here
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Brief comment explaining what this checks
    helper_coverpoint: coverpoint <expression> {
        bins name = {value};
    }

    another_helper: coverpoint <expression> {
        bins name = {value};
    }

    // Cross combining conditions
    cp_name_here: cross helper_coverpoint, another_helper;

//// end cp_name_here ///////////////////////////////////////////////////////////////////////////

```

### Format Rules

1. **Header**: `//` line (~100 chars), `// cp_name`, `//` line
2. **Footer**: `//// end cp_name` + slashes to ~100 chars
3. **Indent**: 4 spaces for coverpoints, 8 for bins
4. **No unused coverpoints**: Every helper MUST be used in a cross
5. **One blank line** at end of file
6. **NO covergroup wrapper** - just coverpoint definitions

---

## Common Patterns (Copy These)

### Standard Vector Conditions (std_vec)
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

### Trap Occurred
```systemverilog
    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }
```

### Valid vtype (vill=0)
```systemverilog
    vtype_valid: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        bins valid = {1'b0};
    }
```

### LMUL Values (vlmul encoding: mf8=5, mf4=6, mf2=7, m1=0, m2=1, m4=2, m8=3)
```systemverilog
    vtype_lmul_1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one = {0};
    }
    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }
    vtype_lmul_4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins four = {2};
    }
    vtype_lmul_8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins eight = {3};
    }
```

### SEW Values (vsew encoding: e8=0, e16=1, e32=2, e64=3)
```systemverilog
    vtype_sew_8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e8 = {0};
    }
    vtype_sew_16: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e16 = {1};
    }
    vtype_sew_32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e32 = {2};
    }
    vtype_sew_64: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e64 = {3};
    }
```

### Register Bit Fields (vd[11:7], vs1[19:15], vs2[24:20], vm[25])
```systemverilog
    vd_v0: coverpoint ins.current.insn[11:7] { bins zero = {5'b00000}; }
    vd_not_v0: coverpoint ins.current.insn[11:7] { bins not_v0[] = {[1:31]}; }
    vs2_v0: coverpoint ins.current.insn[24:20] { bins v0 = {5'b00000}; }
    mask_enabled: coverpoint ins.current.insn[25] { bins masked = {1'b0}; }
```

### Register Alignment for LMUL
```systemverilog
    vd_aligned_lmul_2: coverpoint ins.current.insn[11:7] { wildcard bins div2 = {5'b????0}; }
    vd_aligned_lmul_4: coverpoint ins.current.insn[11:7] { wildcard bins div4 = {5'b???00}; }
    vd_aligned_lmul_8: coverpoint ins.current.insn[11:7] { wildcard bins div8 = {5'b??000}; }
```

### VL at VLMAX
```systemverilog
    vl_max: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")
                        == get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) {
        bins target = {1'b1};
    }
```

---

## Allowed Bin Patterns

Use ONLY these syntaxes:

```systemverilog
bins name = {value};                          // Single value
bins name = {[start:end]};                    // Range
bins name[] = {[start:end]};                  // One bin per value in range
wildcard bins name = {5'b???00};              // Wildcard pattern
ignore_bins name = {value};                   // Exclude value
```

### Compound Coverpoints (for multi-field bins)

When you need bins that match combinations of multiple fields, use compound coverpoints:

```systemverilog
my_compound_cp : {coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                  coverpoint ins.current.insn[31:29]} {
    bins combo1 = {3'b011, 3'b001};  // vlmul=8, nf=1 tuple
    bins combo2 = {3'b010, 3'b011};  // vlmul=4, nf=3 tuple
}
```

Each bin matches a tuple of values in the order the coverpoints are declared.

---

## File Locations

| What | Where |
|------|-------|
| This guide | `CLAUDE-csv-editor.md` |
| Coverpoint templates (unprivileged) | `generators/coverage/templates/*.txt` |
| Coverpoint templates (privileged/Ssstrictv) | `generators/coverage/templates/priv/*.txt` |
| CSV files | `working-testplans/*.csv` |
| Additional patterns | `CLAUDE-coverpoint-writer.md` |
| Vector encodings | `CLAUDE-vector-reference.md` |
| Standard vector coverpoints | `coverpoints/general/RISCV_coverage_standard_coverpoints_vector.svh` |

**NEVER access `testplans/*.csv`** - only use `working-testplans/`

**Note:** Priv templates can include shared helpers via `\`include "general/RISCV_coverage_standard_coverpoints_vector.svh"`

---

## Persisting Knowledge

If you discover something new (pattern, encoding, technique), ADD IT to the appropriate file:

| Discovery Type | Add To |
|---------------|--------|
| New coverpoint pattern | This file (Common Patterns section) |
| New encoding/bit field | CLAUDE-vector-reference.md |
| Format rule clarification | CLAUDE-coverpoint-writer.md |

**This is how knowledge transfers between CSV lines** - through .md file updates.

---

## CSV Entry Writing Rules

### Feature Description Must Be Procedural

The Feature Description field describes **what the test does**, not what the spec says. Write it as a test procedure: what values to set up and what instruction to run.

**Good** (procedural - says what to set up and execute):
- "Set SEW=8, LMUL=1 and execute an indexed vector load/store with 64-bit index EEW (index EMUL=8), with vstart=0 and vl != 0"
- "Set vtype.vill = 1 and run a whole register load/store instruction with vstart = 0 and vl != 0"

**Bad** (restates the spec rule):
- "For indexed vector load/store instructions, the data vector register group has EEW=SEW and EMUL=LMUL, while the index vector register group has EEW encoded in the instruction"

**Note on standard conditions**: Normally all tests are non-trivial (vill=0, vstart=0, vl!=0). Only explicitly mention vstart=0 and vl!=0 in the feature description when the test *changes* one of the other standard conditions (e.g., vill=1). If the test uses the normal std_vec conditions, you don't need to spell them all out.

## Important Notes

- **Instruction names not needed**: Coverpoints use bit fields, not instruction names
- **Create what the user specified**: Don't add extra features or "improvements"
- **One comment max**: Readers have the CSV - don't over-document
- **Test the cross**: Every helper coverpoint must appear in at least one cross

## File Modification Rules

- **ONLY write coverpoint template files** (`generators/coverage/templates/*.txt` or `generators/coverage/templates/priv/*.txt`)
- **NEVER modify CSV files, testplan files, or any other files** unless the user explicitly tells you to modify a specific file
- CSV files, testplans, and other framework files are managed externally and copied in for testing - they are NOT their final versions
- If you have a suggestion about CSV columns, testplan entries, or other file changes, **tell the user** instead of making the edit
- When in doubt, describe what you think should change and let the user decide
