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

| Label base name                    | Value                       |
| ---------------------------------- | --------------------------- |
| `vs_corner_f_pos0`                 | +0.0                        |
| `vs_corner_f_neg0`                 | -0.0                        |
| `vs_corner_f_pos1`                 | +1.0                        |
| `vs_corner_f_neg1`                 | -1.0                        |
| `vs_corner_f_posminnorm`           | smallest positive normal    |
| `vs_corner_f_negmaxnorm`           | largest negative normal     |
| `vs_corner_f_posinfinity`          | +Inf                        |
| `vs_corner_f_neginfinity`          | -Inf                        |
| `vs_corner_f_pos0p5`               | +0.5                        |
| `vs_corner_f_pos1p5`               | +1.5                        |
| `vs_corner_f_neg2`                 | -2.0                        |
| `vs_corner_f_pi`                   | pi                          |
| `vs_corner_f_twoToEmax`            | 2^Emax                      |
| `vs_corner_f_onePulp`              | 1 + ULP                     |
| `vs_corner_f_largestsubnorm`       | largest subnormal           |
| `vs_corner_f_negSubnormLeadingOne` | negative subnormal          |
| `vs_corner_f_min_subnorm`          | smallest subnormal          |
| `vs_corner_f_canonicalQNaN`        | canonical quiet NaN         |
| `vs_corner_f_negNoncanonicalQNaN`  | negative non-canonical qNaN |
| `vs_corner_f_sNaN_payload1`        | signaling NaN               |

Available EMUL suffixed sets: `vfedgesemul1`, `vfedgesemul2` (lists of label strings with `_emul1`/`_emul2` appended).

### fflags / FP Flags

The `fp_flags_clear` coverpoint in templates checks that `fflags == 0` BEFORE the instruction executes. This is typically the default state at test start. If your coverpoint crosses with `fp_flags_clear`, just make sure you don't set flags before the instruction under test — using clean edge values with `vl=1` usually satisfies this.

### NX trigger values for approximation/sqrt instructions

The default NX trigger `1.0 + 1ulp` works for arithmetic instructions (vfadd, vfmul, etc.) but can fail for lookup-table/sqrt instructions because the approximation for that specific input may happen to be exactly representable:

- **vfrsqrt7.v**: Use **3.0** (`{16: 0x4200, 32: 0x40400000, 64: 0x4008000000000000}`) — 1/√3 is not exact in 7-bit approximation
- **vfrec7.v**: Use **3.0** (same values) — 1/3 is not exactly representable
- **vfsqrt.v**: Use **2.0** (`{16: 0x4000, 32: 0x40000000, 64: 0x4000000000000000}`) — √2 is irrational

General rule: when an NX bin is ZERO for an approximation or sqrt instruction, the issue is almost always the trigger value, not the script structure. Try a different input value.

### Transition bins (NV1/DZ1/NX1 etc.) require two consecutive flag-setting tests

The framework inserts `fsflagsi 0b00000` before each test case, so each `SAMPLE_AFTER` value reflects only what that single test produced from a clean fflags state. Transition bins compare `SAMPLE_AFTER[i]` to `SAMPLE_AFTER[i+1]`.

- **`NX = (5'b????0 => 5'b????1)`** — bit 0 was 0, now 1. Covered by a single NX-setting test after any clean state.
- **`NX1 = (5'b????1 => 5'b????1)`** — bit 0 was 1, still 1. Requires **two consecutive NX-setting tests** so that sample[i]=NX and sample[i+1]=NX.

**Pattern**: to cover both `FLAG` and `FLAG1` for any flag bit, generate the flag-triggering test **twice in a row**. Do this for each flag type (NX, NV, DZ, OF, UF) independently. Do NOT mix different flags to try to cover "stays set" — only a matching consecutive pair works.

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

### Register name must match CSV column, not coverpoint definition name

The `@register()` decorator tag must match the **CSV column name** in `testplans/VfCustom.csv` (or whichever CSV), NOT the name in `Vf_custom_definitions.csv`. The testplan_manager maps definition names → CSV column names, but the framework dispatches using the CSV column. E.g., if the CSV column is `cp_custom_vfp_state` but the definition is `cp_custom_f_freg_write_vl0`, register as `cp_custom_vfp_state`.

### SEW > XLEN on RV32 causes compilation failures

When SEW=64 on RV32, `writeTest` generates `sd`/`fld` instructions that need D/zilsd extension. Skip with: `if sew > common.xlen: return` (import `vector_testgen_common as common`).

### Stop spinning on coverage issues

If you can't figure out a coverage issue after 2 attempts, stop. Write a concise note to `claude-scripts/coverage_issues/<coverpoint_name>.md` explaining what coverage is missing and your best guess why. A human will look at it later.

### Read the generated assembly when coverage is unexpected

When coverage shows 0% or unexpected results, read the generated `.S` file (e.g. `tests/rv32i/VfCustom16/VfCustom16-vfrsqrt7.v.S`). For single-instruction coverpoints these files are short and will immediately reveal issues like wrong register fields, missing data, or incorrect instruction encodings.

### Never check instruction identity inside a coverpoint — the framework already does this

Each instruction has its OWN covergroup instance (e.g. `obj_VfCustom16_vfrsqrt7_v`). The framework only calls `sample()` for that covergroup when the matching instruction executes. **You never need to check `ins.current.insn == "someinstruction"` inside a coverpoint** — you already know which instruction is running.

- **Wrong**: `coverpoint (ins.current.insn == "vfrsqrt7.v" & ins.current.vs2_val == 0)`
- **Right**: `coverpoint (ins.current.vs2_val == 0)`

`ins.current.insn` is the **raw 32-bit instruction word** (not a mnemonic string). Comparing it to a string literal like `"vfrsqrt7.v"` is a type mismatch and always evaluates false. If you genuinely needed the instruction name as a string (e.g. to check a _previous_ instruction, as in `cp_custom_sc.sv`), use `ins.prev.inst_name` — but for the _current_ instruction, this is never needed.

### `vs2_val` vs `vs2` in coverage templates

Coverage templates that sample vector register DATA must use `ins.current.vs2_val` (or `vs1_val`, `vd_val`), NOT `ins.current.vs2`. The unsuffixed version is the register NAME (a string like "v16") — passing it to `get_vr_element_zero()` causes a "String assignment to packed type" warning and 0% coverage. The `_val` suffix gives the actual register CONTENTS (`VLEN_BITS` packed value). Reference: `coverpoints/general/RISCV_coverage_standard_coverpoints_vector.svh` uses `_val` everywhere.

### sNaN bin values must match test data labels

The `vs_corner_f_sNaN_payload1` data label generates specific values per SEW:

- SEW16: `0x7D01` (NOT `0x7D00`)
- SEW32: `0x7F800001` (NOT `0x7FA00000`)
- SEW64: `0x7FF0000000000001` (matches)

Always verify bin values in `.sv` templates against actual data in generated `.S` files.

### CSR field names in coverage templates: use "fcsr" not "frm"

The `get_csr_val()` function for sampling `frm` must use `"fcsr"` as the CSR name, not `"frm"`:

- **WRONG**: `get_csr_val(ins.hart, ins.issue, \`SAMPLE_BEFORE, "frm", "frm")`
- **RIGHT**: `get_csr_val(ins.hart, ins.issue, \`SAMPLE_BEFORE, "fcsr", "frm")`The RVVI trace exposes`frm`as a field within`fcsr`, not as a standalone CSR. Using `"frm", "frm"` silently returns 0 and gives 0% coverage on the frm bin.

### Overlap constraints fail for segmented instructions at high LMUL/NF

`randomizeVectorInstructionData()` raises `ValueError` when register overlap constraints are unsolvable. This commonly happens with segmented load/store instructions (e.g., `vlseg6e16.v` has nf=6) at higher LMUL values, because vd occupies `nf*LMUL` consecutive registers, leaving too few registers for other operands. **Always wrap `randomizeVectorInstructionData()` calls in `try/except ValueError: pass`** for scripts applied to segmented or whole-register LS instructions.

### NEVER use `vs2_val=integer` — always use `vs2_val_pointer`

`vs2_val=integer` loads via `li` + `vmv.v.x` which sign-extends from XLEN. On RV32 this truncates 64-bit values, and it can also cause traps for certain values. **Always use `vs2_val_pointer=label`** instead, which loads from memory via `vle`.

For custom values not in the existing edge data labels, use `registerCustomData()`:

```python
from vector_testgen_common import registerCustomData

# Register a data label with 64-bit values (fills full VLEN register by repeating)
registerCustomData("my_custom_label", [0x47F0000000000000], element_size=64)

# Then use it
data = randomizeVectorInstructionData(test, sew, count, lmul=1, vs2_val_pointer="my_custom_label")
```

`registerCustomData(label, values, element_size)` creates a data label in the `.data` section. The `values` list is replicated to fill maxVLEN bits. `element_size` is 8/16/32/64. Labels are cleared between test files automatically.

### Narrowing instructions and get_vr_element_zero()

For narrowing instructions (e.g., `vfncvt.rod.f.f.w`), `get_vr_element_zero()` extracts element 0 at the OUTPUT SEW (from vtype.vsew), but vs2 has 2\*SEW elements. This means it only gets the lower half of the source element. **Fix: use `ins.current.vs2_val[63:0]` directly** instead of `get_vr_element_zero()` for narrowing instruction templates.

### FP lookup table coverpoints need both even and odd exponents

For `vfrsqrt7` and `vfrec7` lookup table coverpoints, the coverage bins span the exponent/mantissa boundary. If the script only uses one exponent value (e.g., biased=16=0b10000), the exponent LSB is always 0 and only half the bins are covered. **Fix: generate values with both even and odd exponents** to cover all 128 lookup table entries.

### VlsCustom coverage is impractical with sail

All VlsCustom test files are ~4300 lines (due to `SIGUPD_COUNT 50000`). Even with only 1-2 test cases, the binary is large. Sail consistently times out even at 600s. All 7 VlsCustom coverpoints are blocked by this issue. These tests are intended for RTL (Wally) simulation, not sail.

### RVVI fsflagsi CSR alias bug — fp_flags_clear cross failures

`fsflagsi 0b00000` writes CSR 001 (fflags) but NOT CSR 003 (fcsr). The RVVI trace mirror maintains separate values for each CSR number. Templates that use `get_csr_val(..., "fcsr", "fflags")` read CSR 003, which retains the stale value from the previous FP instruction. This causes `fp_flags_clear` cross bins to fail for tests that follow flag-setting FP instructions.

**Fix: Add "spacer" tests** after each flag-setting FP instruction. The spacer uses a non-flag-setting input (e.g., vfrec7(-inf)=−0 or vfrsqrt7(+inf)=+0) which writes CSR 003=0, clearing the stale fcsr for the next real test. Flag-setting inputs: ±0 (DZ), tiny subnormals (OF|NX for vfrec7), negative finites (NV for vfrsqrt7), sNaN (NV).

### writeTest(vl=0) prevents vector data loading

When `writeTest(vl=0)` is used, VL=0 is set BEFORE loading any vector register data via `vle*.v`. Since all vector loads respect VL, they load 0 elements. This makes it impossible to pre-load vs1/vs2 data for VL=0 test cases. This is a framework limitation.

## Coverpoint-Specific Notes

- **cp_custom_FpRecSqrtEst_edges**: 100% coverage. Script was fixed to use both even and odd exponents.
- **cp_custom_FpRecipEst_edges**: 100% coverage. Script worked correctly out of the box.
- **cp_custom_vfclass_onehot**: 100% coverage.
- **cp_custom_vfncvt_rod_overflow**: 100% coverage (SEW32). Template fixed: `get_vr_element_zero()` → `ins.current.vs2_val[63:0]`.
- **cp_custom_vfredosum_ordered_sum**: 100% coverage.
- **cp_custom_FpRecSqrtEst_flag_edges**: 100% coverage. Fixed with spacer tests after flag-setting vfrsqrt7 (RVVI fsflagsi alias bug).
- **cp_custom_FpRecipEst_flag_edges**: 100% coverage. Fixed with spacer tests after flag-setting vfrec7 (same RVVI alias bug).
- **cp_custom_vfncvt_rup_overflow**: 100% coverage on RV64 for `vfncvt.f.f.w` and `vfncvt.rod.f.f.w`. The other 6 instructions (int-to-float, float-to-int) can't set fflags.OF with SEW=32: int64 max < float32 max (no overflow possible), and float-to-int overflow sets NV not OF. All RV32 tests fail due to `vs2_val` XLEN truncation. Template had two bugs fixed: (1) wrong CSR name `"frm"` → `"fcsr"` for frm sampling, (2) misleading comment about SEW meaning (corrected to reflect 64→32 narrowing, not 32→16).
- **cp_custom_vfp_state (cp_custom_f_freg_write_vl0)**: 4/8 bins covered = 50% (cp_asm_count, std_vec, fd_changed_value, fp_flags_clear all 100%). Both crosses at 0% due to template issues: (1) `mstatus_prev_clean` checks `mstatus.vs==0` (Off), which traps on all vector instructions, contradicting `std_vec` (requires no trap). Should probably check `vs==2` (Clean), but even then vector setup instructions (vsetvli, vle) dirty VS before the test instruction. (2) `vfp_state_vfsqrt_flag_set` hardcodes `insn=="vfrsqrt7.v"`, impossible for `vfmv.f.s`. The `cp_custom_f_freg_write_vl0` specific bin (fd_changed_value) IS 100% covered. RV32/SEW64 skipped due to sd/fld needing D extension. See `coverage_issues/cp_custom_vfp_state.md`.
- **cp_custom_vfredosum_NAN_vl0**: 55.55%. Cross at 0%. Framework limitation (vl=0 data loading) + wrong SEW32/64 bin values. See `coverage_issues/`.
- **cp_custom_fmv_sf_vd_all_lmul**: 85.46%. Individual coverpoints (vd_all_regs, vtype_all_lmul) at 100%. Cross needs 128 bins (32 regs × 4 LMULs) but sail can only handle ~35 tests per file (under 950 lines). Script optimized to 35 tests: all 32 vd for LMUL=1, vd=0 for LMUL=2/4/8. Full cross needs RTL sim.
- **cp_custom_fmv_fs_vs2_all_lmul**: 85.46%. Same structure and issue as fmv_sf_vd_all_lmul. Same optimization applied.
- **cp_custom_vfp_NaN_input**: Running coverage — 101 instructions × 2 tests each. ~1 min/file, ~10 hours total. Each file is small (~300 lines) but sheer count is large.
- **All VlsCustom coverpoints**: Blocked by sail timeout. SIGUPD_COUNT 50000 creates huge binaries.
