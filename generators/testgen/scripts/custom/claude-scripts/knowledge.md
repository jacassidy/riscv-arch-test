# Custom Coverpoint Test Generation Knowledge Base

## Script Structure (CRITICAL — read this first)

Every custom script MUST follow this pattern. See `custom/example.py` for the minimal reference:

```python
from coverpoint_registry import register
from vector_testgen_common import (
    writeTest, randomizeVectorInstructionData,
    incrementBasetestCount, getBaseSuiteTestCount, vsAddressCount,
)

@register("cp_custom_YOUR_NAME_HERE")
def make(test, sew):
    # test = instruction mnemonic string (e.g. "vfrsqrt7.v")
    # sew = selected element width (16, 32, 64)
    ...
```

**Key rules:**
- The `@register("cp_custom_...")` decorator is REQUIRED — without it, the script won't be discovered
- Function signature is `make(test, sew)` — NOT `make(instruction, sew, xlen, lmul)`
- `test` is the instruction mnemonic (same thing as "instruction" in the guide)
- Do NOT read `vector-testgen-unpriv.py` to understand the dispatch — just use the decorator

## Build Commands

**Always use `make clean` (NOT `make clean-tests`)** before rebuilding. Covergroups also need to be regenerated between runs.

```bash
make clean && make vector-tests && make coverage
```

## API Tips

### Preset Variable Parsing
`randomizeVectorInstructionData()` splits preset kwargs on the FIRST underscore:
- `vs2_val` → sets `vector_register_preset_data['vs2']['val']` (integer value for all elements)
- `vs2_val_pointer` → sets `vector_register_preset_data['vs2']['val_pointer']` (named data label)
- Same pattern works for `vs1`, `vs3`, `vd`, `rs1`, `rs2`, `fd`, `fs1`

### VVM Unary Instructions (vfrsqrt7.v, vfrec7.v, vfsqrt.v, vfclass.v)
These are VVM type. The **source data is in the vs2 field**, not vs1. Use `vs2_val_pointer` to set input values, NOT `vs1_val_pointer`.

**IMPORTANT — verify coverage templates too:** Some templates incorrectly use `ins.current.vs1` when they should use `ins.current.vs2` for VVM unary ops. If you see a template sampling `vs1` for a unary op, **fix it to `vs2`** before running coverage. This was confirmed as a bug in `cp_custom_FpRecSqrtEst_flag_edges.sv` and `cp_custom_FpRecipEst_flag_edges.sv`. Trust your instincts here — if you suspect a register field mismatch, fix it immediately rather than assuming the template is correct and paying the cost of a failed coverage run.

### FP Vector Edge Value Data Labels
Pre-defined data labels in `vector_testgen_common.py` (append `_emul1` for EMUL=1):

| Label base name | Value |
|-----------------|-------|
| `vs_corner_f_pos0` | +0.0 |
| `vs_corner_f_neg0` | -0.0 |
| `vs_corner_f_pos1` | +1.0 |
| `vs_corner_f_neg1` | -1.0 |
| `vs_corner_f_posminnorm` | smallest positive normal |
| `vs_corner_f_negmaxnorm` | largest negative normal |
| `vs_corner_f_posinfinity` | +Inf |
| `vs_corner_f_neginfinity` | -Inf |
| `vs_corner_f_pos0p5` | +0.5 |
| `vs_corner_f_pos1p5` | +1.5 |
| `vs_corner_f_neg2` | -2.0 |
| `vs_corner_f_pi` | pi |
| `vs_corner_f_twoToEmax` | 2^Emax |
| `vs_corner_f_onePulp` | 1 + ULP |
| `vs_corner_f_largestsubnorm` | largest subnormal |
| `vs_corner_f_negSubnormLeadingOne` | negative subnormal |
| `vs_corner_f_min_subnorm` | smallest subnormal |
| `vs_corner_f_canonicalQNaN` | canonical quiet NaN |
| `vs_corner_f_negNoncanonicalQNaN` | negative non-canonical qNaN |
| `vs_corner_f_sNaN_payload1` | signaling NaN |

Available EMUL suffixed sets: `vfedgesemul1`, `vfedgesemul2` (lists of label strings with `_emul1`/`_emul2` appended).

### fflags / FP Flags
The `fp_flags_clear` coverpoint in templates checks that `fflags == 0` BEFORE the instruction executes. This is typically the default state at test start. If your coverpoint crosses with `fp_flags_clear`, just make sure you don't set flags before the instruction under test — using clean edge values with `vl=1` usually satisfies this.

## Registry of Patterns

### FP Flag Edge Tests (e.g. cp_custom_FpRecSqrtEst_flag_edges, cp_custom_FpRecipEst_flag_edges)
Pattern: Loop over FP edge data labels, use `vs2_val_pointer` for VVM unary ops, `vl=1`, base suite.

```python
@register("cp_custom_FpRecSqrtEst_flag_edges")
def make(test, sew):
    edges = [
        ("vs_corner_f_neg1_emul1", "neg_finite"),
        ("vs_corner_f_neginfinity_emul1", "neg_inf"),
        # ... etc
    ]
    for label, desc in edges:
        data = randomizeVectorInstructionData(test, sew, getBaseSuiteTestCount(), lmul=1, vs2_val_pointer=label)
        writeTest(f"cp_name ({desc})", test, data, sew=sew, lmul=1, vl=1)
        incrementBasetestCount()
        vsAddressCount()
```

## Common Pitfalls

### Trust your instincts on suspicious bugs — fix first, verify after
If something looks wrong in a template or config (e.g. wrong register field, wrong hex value), fix it immediately rather than assuming it's correct. A failed coverage run costs minutes; fixing a one-line bug costs seconds. It's cheaper to be wrong and revert than to waste an entire build cycle confirming a suspicion.

### Don't confuse vs1 vs vs2 for unary ops
VVM unary instructions (vfsqrt, vfrsqrt7, vfrec7, vfclass) use the **vs2** field for source data. Coverage templates may incorrectly reference `vs1` — this is a known bug pattern. Always verify the template samples the correct register field, and fix it if wrong.

### Stop spinning on coverage issues
If you can't figure out a coverage issue after 2 attempts, stop. Write a concise note to `claude-scripts/coverage_issues/<coverpoint_name>.md` explaining what coverage is missing and your best guess why. A human will look at it later.

### Read the generated assembly when coverage is unexpected
When coverage shows 0% or unexpected results, read the generated `.S` file (e.g. `tests/rv32i/VfCustom16/VfCustom16-vfrsqrt7.v.S`). For single-instruction coverpoints these files are short and will immediately reveal issues like wrong register fields, missing data, or incorrect instruction encodings.

### `vs2_val` vs `vs2` in coverage templates
Coverage templates that sample vector register DATA must use `ins.current.vs2_val` (or `vs1_val`, `vd_val`), NOT `ins.current.vs2`. The unsuffixed version is the register NAME (a string like "v16") — passing it to `get_vr_element_zero()` causes a "String assignment to packed type" warning and 0% coverage. The `_val` suffix gives the actual register CONTENTS (`VLEN_BITS` packed value). Reference: `coverpoints/general/RISCV_coverage_standard_coverpoints_vector.svh` uses `_val` everywhere.

### sNaN bin values must match test data labels
The `vs_corner_f_sNaN_payload1` data label generates specific values per SEW:
- SEW16: `0x7D01` (NOT `0x7D00`)
- SEW32: `0x7F800001` (NOT `0x7FA00000`)
- SEW64: `0x7FF0000000000001` (matches)

Always verify bin values in `.sv` templates against actual data in generated `.S` files.

## Coverpoint-Specific Notes

- **cp_custom_FpRecSqrtEst_flag_edges**: 90% coverage. Cross with `fp_flags_clear` at 50% — see `coverage_issues/cp_custom_FpRecSqrtEst_flag_edges.md` for details. Script and template are correct.
