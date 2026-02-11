# CLAUDE-coverpoint-writer.md

## Coverpoint Writer Reference

**Purpose**: Detailed format rules and patterns for SystemVerilog coverpoint templates
**Primary Guide**: See `CLAUDE-csv-editor.md` for the main workflow
**When to Read**: Only if you need patterns not found in csv-editor.md

---

## Stateless Processing

Each CSV line is processed by a **fresh Claude instance**. No conversation context carries over.
- Knowledge persists ONLY through .md file updates
- If you learn something new, ADD IT to the appropriate .md file before finishing

---

## File Types & Naming

**Directory**: `generators/coverage/templates/`

### Type 1: Custom Coverpoints (Multiple per file)

- **Filename**: `cp_custom_v<instruction_category>.txt` (e.g., `cp_custom_vwvv.txt`)
- **Contains**: ALL custom coverpoints for that instruction category
- **Define helpers once**: `std_vec`, `vtype_lmul_X`, etc. defined once at top, reused in crosses
- **Multiple crosses**: All related crosses at bottom of file

### Type 2: Non-Custom Coverpoints (One per file)

- **Filename**: Matches coverpoint name (e.g., `cp_vstart_gt_vl.txt`)
- **Contains**: Single coverpoint only
- **NO helper definitions**: Combine all conditions with `&` in one coverpoint
- **NO crosses**: Avoids naming conflicts when files are assembled

---

## Template Formats

### Non-Custom (Single Coverpoint, No Crosses)

```systemverilog
//////////////////////////////////////////////////////////////////////////////////
    // cp_example_name
    //////////////////////////////////////////////////////////////////////////////////

    cp_example_name: coverpoint (condition1 &
                                 condition2 &
                                 condition3) {
        bins true = {1};
    }

    //// end cp_example_name////////////////////////////////////////////////
```

### Custom (Multiple Coverpoints, With Crosses)

```systemverilog
//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vexample
    //////////////////////////////////////////////////////////////////////////////////

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

    vd_aligned_lmul_4: coverpoint ins.current.insn[11:7] {
        wildcard bins divisible_by_4 = {5'b???00};
    }

    cp_custom_vexample_lmul4: cross std_vec, vtype_lmul_4, vd_aligned_lmul_4;

    //// end cp_custom_vexample////////////////////////////////////////////////
```

---

## Critical Rules

1. **NO COVERGROUP WRAPPER**: Never write `covergroup ... endgroup`. These files get copy-pasted into an existing covergroup. Write ONLY the coverpoint definitions and crosses.
2. **Comments**: Maximum 1 line to explain something. Readers already read the CSV.
3. **Indentation**: 4 spaces for coverpoints, 8 for bins
4. **Header**: `//` line, `// cp_name`, `//` line (first `//` line starts at column 0)
5. **Footer**: `//// end cp_name` followed by slashes to ~80 chars
6. **Trailing newline**: File ends with exactly one blank line
7. **No unused coverpoints**: Every helper coverpoint MUST be used in at least one cross. After writing, review the file and delete any coverpoints not referenced in a cross. Do a second pass if needed.

---

## Allowed Bin Patterns

**Use ONLY these patterns.**

```systemverilog
bins name = {value};                          // Simple value
bins name = {[start:end]};                    // Range
wildcard bins name = {5'b???00};              // Wildcard
wildcard bins name = (before => after);       // Transition
ignore_bins name = {value};                   // Exclude
wildcard ignore_bins name = {5'b???00};       // Exclude wildcard
```

---

## Keywords for Python Replacement

| Keyword | Replaced With | Example |
|---------|---------------|---------|
| `INSTR` | instruction mnemonic | `add`, `vfredosum.vs` |
| `INSTRNODOT` | mnemonic with `.` → `_` | `vfredosum_vs` |
| `ARCH` | extension lowercase | `i`, `vx64` |
| `EFFEW` | vector element width | `8`, `16`, `32`, `64` |

---

## Communication Format

### Receiving Requirements

```
NAME: cp_custom_example_name
FILE: cp_custom_vcategory.txt (or new standalone file)
TYPE: custom | non-custom

GOAL: What behavior to verify

CONDITIONS:
1. condition (with bits/values)
2. another condition

EXPECTED BINS: count
```

### Output

Write the file directly. No verbose explanations needed.

---

## Common Patterns (Copy-Paste Ready)

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

### LMUL Coverpoints

```systemverilog
// Single LMUL value (vlmul encoding: mf8=5, mf4=6, mf2=7, m1=0, m2=1, m4=2, m8=3)
vtype_lmul_1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
    bins one = {0};
}

vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
    bins two = {1};
}

vtype_lmul_4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
    bins four = {2};
}

// Multiple LMUL values (LMUL >= 1, no guards needed)
vtype_all_lmulge1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
    bins one = {0}; bins two = {1}; bins four = {2}; bins eight = {3};
}
```

**All LMUL values with ifdef guards** (REQUIRED when covering all LMUL values including fractional - fractional LMULs are optional per DUT, integer LMULs are always present):
```systemverilog
vtype_all_lmul: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
    `ifdef LMULf8_SUPPORTED
        bins eighth  = {5};
    `endif
    `ifdef LMULf4_SUPPORTED
        bins fourth = {6};
    `endif
    `ifdef LMULf2_SUPPORTED
        bins half   = {7};
    `endif
    bins one    = {0};
    bins two    = {1};
    bins four   = {2};
    bins eight  = {3};
}
```

### SEW Coverpoints

```systemverilog
// Single SEW value (vsew encoding: e8=0, e16=1, e32=2, e64=3)
vtype_sew_8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
    bins e8 = {0};
}

vtype_sew_16: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
    bins e16 = {1};
}
```

**All SEW values with ifdef guards** (REQUIRED when covering all SEW values - not all SEW widths are supported by every DUT):
```systemverilog
vtype_all_sew: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
    `ifdef SEW8_SUPPORTED
        bins e8  = {0};
    `endif
    `ifdef SEW16_SUPPORTED
        bins e16 = {1};
    `endif
    `ifdef SEW32_SUPPORTED
        bins e32 = {2};
    `endif
    `ifdef SEW64_SUPPORTED
        bins e64 = {3};
    `endif
}
```

### Register Bit Extraction

```systemverilog
// Instruction bits: vd[11:7], vs1[19:15], vs2[24:20], vm[25]

// Register is v0
vd_v0: coverpoint ins.current.insn[11:7] { bins zero = {5'b00000}; }

// Register is NOT v0
vd_not_v0: coverpoint ins.current.insn[11:7] { bins not_v0[] = {[1:31]}; }

// Masking enabled (vm=0)
mask_enabled: coverpoint ins.current.insn[25] { bins masked = {1'b0}; }
```

### Register Alignment (for LMUL)

```systemverilog
// Divisible by 2 (LMUL=2 alignment)
vd_aligned_lmul_2: coverpoint ins.current.insn[11:7] {
    wildcard bins divisible_by_2 = {5'b????0};
}

// Divisible by 4 (LMUL=4 alignment)
vd_aligned_lmul_4: coverpoint ins.current.insn[11:7] {
    wildcard bins divisible_by_4 = {5'b???00};
}

// Divisible by 8 (LMUL=8 alignment)
vd_aligned_lmul_8: coverpoint ins.current.insn[11:7] {
    wildcard bins divisible_by_8 = {5'b??000};
}
```

### Widening Overlap Detection

```systemverilog
// For widening: vd upper bits must match vs2 upper bits
// LMUL=1 widening (2-reg dest): compare bits [4:1]
vs2_vd_overlap_lmul1: coverpoint (ins.current.insn[24:21] == ins.current.insn[11:8]) {
    bins overlapping = {1'b1};
}

// LMUL=2 widening (4-reg dest): compare bits [4:2]
vs2_vd_overlap_lmul2: coverpoint (ins.current.insn[24:22] == ins.current.insn[11:9]) {
    bins overlapping = {1'b1};
}

// LMUL=4 widening (8-reg dest): compare bits [4:3]
vs2_vd_overlap_lmul4: coverpoint (ins.current.insn[24:23] == ins.current.insn[11:10]) {
    bins overlapping = {1'b1};
}
```

### VL at VLMAX

```systemverilog
vl_max: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")
                    == get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) {
    bins target = {1'b1};
}
```

---

## Reference

For `ins` object fields and helper functions, see [CLAUDE-coverpoint-reference.md](./CLAUDE-coverpoint-reference.md).
