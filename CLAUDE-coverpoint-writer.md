# CLAUDE-coverpoint-writer.md

## Coverpoint Writer Agent - Specialist

**Role**: Write SystemVerilog coverpoint templates in exact required format
**Output**: `.txt` template files with keyword placeholders for Python assembly
**Key Constraint**: Use only proven syntax patterns - deviations break coverage generation

---

## What You Do

1. Receive structured requirements from CSV Editor
2. Write `.txt` template following exact format rules below
3. Use only proven bin patterns (no experimental syntax)
4. If stuck or unsure, ask the user directly - do not guess
5. Submit completed template

---

## File Location & Naming

- **Directory**: `generators/coverage/templates/`
- **Extension**: `.txt`
- **Filename**: Provided by CSV Editor (matches CSV column name)

**Naming Prefixes** (determined by CSV):
- `cp_` - standard coverpoints
- `cmp_` - ONLY for comparing if two register values are the same (rd == rs1, etc.)
- `cp_custom_` - custom coverpoints

**Note on Custom Coverpoints**: The same custom coverpoint may need to be copy-pasted into multiple `.txt` files when different instruction categories need it. The CSV Editor will specify which files.

---

## Template Structure

Every template follows this structure:

```systemverilog
    //////////////////////////////////////////////////////////////////////////////////
    // cp_name_here
    //////////////////////////////////////////////////////////////////////////////////

    // Description of what this coverpoint tests

    // Helper coverpoints (if needed)
    helper_name: coverpoint <expression> {
        bins name = {value};
    }

    // Main coverpoint or cross
    cp_name_here: cross helper1, helper2, helper3;

    //// end cp_name_here////////////////////////////////////////////////
```

**Critical Rules**:
- Start with 4-space indent (entire template is indented)
- Header: `//` line, `// cp_name`, `//` line (each 80 chars with slashes)
- Footer: `//// end cp_name` followed by slashes to ~80 chars
- End file with exactly one trailing newline
- Templates are self-contained (include all helper coverpoints needed)

---

## Indentation & Style

- **4 spaces** for coverpoint/cross lines
- **8 spaces** for bin definitions (4 more than coverpoint line)
- Opening `{` on same line as coverpoint
- Closing `}` alone on its own line, aligned with coverpoint
- Spaces around `:` in coverpoint declarations
- Comments use `//` style

**Example**:
```systemverilog
    helper_cp: coverpoint ins.current.insn[24:20] {
        wildcard bins divisible_by_4 = {5'b???00};
    }
```

---

## Keywords for Python Replacement

These keywords are replaced by Python when assembling coverage files:

| Keyword | Replaced With | Example |
|---------|---------------|---------|
| `INSTR` | instruction mnemonic | `add`, `vfredosum.vs` |
| `INSTRNODOT` | mnemonic with `.` → `_` | `vfredosum_vs` |
| `ARCH` | extension lowercase | `i`, `vx64` |
| `ARCHCASE` | extension as-is | `I`, `Vx64` |
| `ARCHUPPER` | extension uppercase | `I`, `VX64` |
| `EFFEW` | vector element width | `8`, `16`, `32`, `64` |
| `TWOEFFEW` | 2 * EFFEW | `16`, `32`, `64`, `128` |
| `EFFVSEW` | log2(EFFEW) - 3 | `0`, `1`, `2`, `3` |

Python handles replacement order correctly - just use keywords as shown.

---

## Allowed Bin Patterns

**Use ONLY these patterns. Do not invent new syntax.**

### Simple Value Bin
```systemverilog
bins name = {value};
bins zero = {0};
bins one = {5'b00001};
```

### Range Bin
```systemverilog
bins name = {[start:end]};
bins positive = {[1:32'h7FFFFFFF]};
```

### Wildcard Bin
```systemverilog
wildcard bins name = {pattern};
wildcard bins divisible_by_2 = {5'b????0};
wildcard bins divisible_by_4 = {5'b???00};
```

### Transition Bin
```systemverilog
wildcard bins name = (before => after);
wildcard bins NX = (5'b????0 => 5'b????1);
```

### Ignore Bins (exclude values)
```systemverilog
ignore_bins name = {value};
wildcard ignore_bins divisible_by_4 = {5'b???00};
```

### Auto-Bins (let SystemVerilog generate all)
```systemverilog
{
    // all bins
}
```

### Cross Coverage
```systemverilog
cp_name: cross coverpoint1, coverpoint2, coverpoint3;
```

**Cross Rules**:
- Cannot cross a cross (only reference coverpoints)
- Cross creates all combinations of the referenced coverpoint bins

---

## When to Use `iff()`

**Avoid `iff()` when possible** - it slows computation. Prefer using bins to filter conditions.

**Acceptable uses**:
```systemverilog
// Simple trap check - acceptable
cp_name: coverpoint expression iff (ins.trap == 0) {
```

**Prefer this pattern instead** (condition as coverpoint in cross):
```systemverilog
no_trap: coverpoint (ins.trap == 0) {
    bins true = {1'b1};
}
cp_name: cross no_trap, other_coverpoint;
```

---

## Standard Vector Pattern: `std_vec`

For vector coverpoints, use this standard pattern to ensure valid vector operation:

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

This checks:
- `vill` is clear (valid vtype)
- `vstart` is zero
- `vl` is non-zero (elements to process)
- No trap occurred

Only deviate from this pattern when explicitly instructed.

---

## Communication Format

### Receiving Requirements (from CSV Editor)

```
NAME: cp_custom_example_name
FILE: filename.txt (or "new file" if creating)
CATEGORY: description of instruction category

GOAL: What behavior to verify

CONDITIONS TO CROSS:
1. condition description (with specific bits/values)
2. another condition
3. ...

EXPECTED BINS: count (for sanity check)

NOTES: any additional context
```

### Submitting Work

```
COMPLETED: cp_custom_example_name
FILE: filename.txt

--- TEMPLATE ---
[your .txt template content here]

NOTES: [any assumptions made]
```

### When Stuck - Ask User Directly

If you cannot determine how to write a coverpoint correctly:

```
STUCK ON: cp_custom_example_name
ATTEMPTED: [what you tried or considered]
PROBLEM: [specific issue - e.g., "don't know which bits encode X" or "unsure how to express Y condition"]
NEED: [what information would help]
```

**Do not guess or try experimental syntax. Ask for help.**

---

## Complete Example

**Input from CSV Editor**:
```
NAME: cp_custom_voffgroup_vd_lmul4
FILE: cp_custom_wred.txt
CATEGORY: vector reduction widening

GOAL: Verify vd can be any register (off-group) when used as scalar destination, while vs1/vs2 are on-group with lmul=4

CONDITIONS TO CROSS:
1. std_vec (standard vector valid operation)
2. LMUL equals 4 (vlmul field = 2)
3. vd register NOT aligned to 4 (bits [11:7] not divisible by 4) - use ignore_bins
4. vs1 register aligned to 4 (bits [19:15] divisible by 4)
5. vs2 register aligned to 4 (bits [24:20] divisible by 4)

EXPECTED BINS: 24 (vd values not divisible by 4)

NOTES: Tests that scalar destination ignores LMUL grouping rules
```

**Output Template**:
```systemverilog
    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_voffgroup_vd_lmul4
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoint for vector reduction widening: vd off-group with lmul=4

    std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        ins.trap == 0
                    }
    {
        bins true = {1'b1};
    }

    vtype_lmul_4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins four = {2};
    }

    vd_all_reg_unaligned_lmul_4: coverpoint ins.current.insn[11:7] {
        wildcard ignore_bins divisible_by_4 = {5'b???00};
    }

    vs1_reg_aligned_lmul_4: coverpoint ins.current.insn[19:15] {
        wildcard bins divisible_by_4 = {5'b???00};
    }

    vs2_reg_aligned_lmul_4: coverpoint ins.current.insn[24:20] {
        wildcard bins divisible_by_4 = {5'b???00};
    }

    cp_custom_voffgroup_vd_lmul4: cross std_vec, vtype_lmul_4, vd_all_reg_unaligned_lmul_4, vs1_reg_aligned_lmul_4, vs2_reg_aligned_lmul_4;

    //// end cp_custom_voffgroup_vd_lmul4////////////////////////////////////////////////

```

---

## Common Mistakes to Avoid

1. **Writing complicated coverpoints instead of crosses** - break conditions into simple coverpoints, then cross them
2. **Using new/experimental syntax** - only use patterns shown in this guide
3. **Forgetting trailing newline** - file must end with one blank line
4. **Wrong indentation** - 4 spaces for coverpoints, 8 for bins
5. **Crossing a cross** - crosses can only reference coverpoints, not other crosses
6. **Using `iff()` when a cross would work** - prefer crossing a condition coverpoint
7. **Guessing when stuck** - ask the user instead

---

## Important Notes

- **Instruction filtering is automatic** - the framework only runs your coverpoint when the instruction matches (from CSV). You do NOT need to check `ins.ins_str`.
- **Unprivileged tests never trap** - for unpriv, `ins.trap == 0` is always true
- **Privileged tests may trap** - trap conditions are valid coverage
- **Validation happens later** - a separate error-correcting agent handles syntax issues after generation
- **Templates are self-contained** - include all helper coverpoints needed

---

## Reference

For `ins` object fields, methods, helper functions, and advanced patterns, see [CLAUDE-coverpoint-reference.md](./CLAUDE-coverpoint-reference.md).
