# Custom Test Generation Scripts Guide

## Purpose

Each script in this directory is a single Python function that generates assembly test cases for a specific custom coverpoint. When `makeTest()` in `vector-testgen-unpriv.py` encounters a coverpoint not in its if-tree, it calls the matching script from this directory.

## Function Signature

Every custom script must use the `@register` decorator and export a function with this signature:

```python
from coverpoint_registry import register

@register("cp_custom_YOUR_NAME_HERE")
def make(test, sew):
```

The `@register` decorator is **required** — without it the script will not be discovered by the framework. See `custom/example.py` for a minimal working example.

**Parameters:**
- `test` (str): The RISC-V instruction mnemonic (e.g. `"vadd.vv"`, `"vle32.v"`)
- `sew` (int): Selected Element Width in bits (8, 16, 32, or 64)

## Required Imports

```python
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    incrementLengthtestCount,
    getBaseSuiteTestCount,
    getLengthSuiteTestCount,
    vsAddressCount,
    getBaseLmul,
    getLengthLmul,
    randomizeMask,
    randomizeOngroupVectorRegister,
    vreg_count,
    xreg_count,
    freg_count,
)
```

Import only what you need from the above.

---

## Core API

### `randomizeVectorInstructionData(instruction, sew, test_count, suite="base", lmul=1, additional_no_overlap=None, **preset_variables)`

Returns `[vector_register_data, scalar_register_data, floating_point_register_data, imm_val]`.

**Key preset variable kwargs** (pass as keyword args):
- `vd=N` — force destination vector register to vN
- `vs1=N`, `vs2=N`, `vs3=N` — force source vector registers
- `rs1=N`, `rs2=N` — force scalar GPR registers
- `fd=N`, `fs1=N` — force FP registers
- `rs1_val=V`, `rs2_val=V` — force scalar register values
- `fs1_val=V` — force FP register value
- `vs1_val_pointer=S`, `vs2_val_pointer=S` — force vector register to load from named data label
- `vs1_val=V` — force vector register value (integer, applied to all elements)
- `imm=V` — force immediate value

**`suite`**: Either `"base"` or `"length"`. Use `"base"` for register/encoding tests, `"length"` for VL/LMUL/masking tests.

**`additional_no_overlap`**: List of lists specifying register groups that must not overlap. Example: `[['vs1', 'v0'], ['vs2', 'v0'], ['vd', 'v0']]`

### `writeTest(description, instruction, instruction_data, sew=None, lmul=1, vl=1, vstart=0, maskval=None, vxrm=None, frm=None, vxsat=None, vta=0, vma=0)`

Emits a single test case to the output file.

- `description` (str): Test description string (appears as comment in output)
- `instruction` (str): Instruction mnemonic
- `instruction_data`: Return value of `randomizeVectorInstructionData`
- `sew`, `lmul`: SEW and LMUL for vtype configuration
- `vl`: Vector length. Can be int, `"vlmax"`, or `"random"`
- `vstart`: vstart value (default 0)
- `maskval`: Mask pattern string or None (unmasked). Valid values: `"ones"`, `"zeroes"`, `"vlmaxm1_ones"`, `"vlmaxd2p1_ones"`, `"cp_mask_random"`, `"random_mask_0"`, `"random_mask_1"`, `"random_mask_2"`, or None
- `vxrm`: Fixed-point rounding mode string (from `vxrmList`), or None
- `frm`: FP rounding mode string (from `frmList`), or None
- `vta`, `vma`: Tail/mask agnostic bits (0 or 1)

### `incrementBasetestCount()` / `incrementLengthtestCount()`

Call after each `writeTest` to advance the test counter for the appropriate suite.

### `vsAddressCount(suite="base")`

Call after each `writeTest` to advance the signature address counter. Pass `"length"` for length suite tests.

### `getBaseSuiteTestCount()` / `getLengthSuiteTestCount()`

Returns current test count for the suite. Pass to `randomizeVectorInstructionData` as `test_count`.

### `getBaseLmul(instruction, sew)`

Returns the base LMUL for an instruction given its SEW (handles EEW-based LMUL adjustments for indexed/widening instructions).

### `randomizeMask(test, always_masked=False)`

Returns a random mask value string or None (unmasked). Use `always_masked=True` to force masking.

### `randomizeOngroupVectorRegister(instruction, *preset_vreg, lmul=1, maskval=None)`

Returns a random vector register that is properly aligned for the given LMUL and does not overlap with any of the preset registers.

---

## Patterns: How Existing `make_*` Functions Work

### Simple Register Sweep (base suite)

Iterates over all register values for a given operand:

```python
def make(instruction, sew, xlen, lmul=1):
    for v in range(vreg_count):
        description = f"cp_custom_example (Test vd = v{v})"
        instruction_data = randomizeVectorInstructionData(
            instruction, sew, getBaseSuiteTestCount(), lmul=lmul, vd=v
        )
        writeTest(description, instruction, instruction_data, sew=sew, lmul=lmul)
        incrementBasetestCount()
        vsAddressCount()
```

### VL/LMUL Sweep (length suite)

Tests different VL and LMUL combinations:

```python
def make(instruction, sew, xlen, lmul=1):
    for l_exp in range(4):  # lmul 1,2,4,8
        for vl in ["vlmax", 1, "random"]:
            cur_lmul = 2 ** l_exp
            description = f"cp_custom_example (lmul={cur_lmul}, vl={vl})"
            instruction_data = randomizeVectorInstructionData(
                instruction, sew, getLengthSuiteTestCount(),
                suite="length", lmul=cur_lmul
            )
            writeTest(description, instruction, instruction_data,
                      sew=sew, lmul=cur_lmul, vl=vl)
            incrementLengthtestCount()
            vsAddressCount("length")
```

### Masked Test

```python
def make(instruction, sew, xlen, lmul=1):
    maskval = randomizeMask(instruction, always_masked=True)
    no_overlap = [['vs1', 'v0'], ['vs2', 'v0'], ['vd', 'v0']]
    description = "cp_custom_example_masked"
    instruction_data = randomizeVectorInstructionData(
        instruction, sew, getLengthSuiteTestCount(),
        suite="length", lmul=lmul, additional_no_overlap=no_overlap
    )
    writeTest(description, instruction, instruction_data,
              sew=sew, lmul=lmul, vl="vlmax", maskval=maskval)
    incrementLengthtestCount()
    vsAddressCount("length")
```

### Overlap Test (widening — vd overlaps vs2 top)

```python
def make(instruction, sew, xlen, lmul=1):
    import math
    emul = 2 * lmul
    vd = randint(0, math.floor((vreg_count - 1) / emul)) * emul
    vs2 = vd + lmul  # force vs2 to overlap top of vd
    vs1 = randomizeOngroupVectorRegister(instruction, vs2, vd, lmul=lmul)
    description = f"cp_custom_overlap (lmul={lmul})"
    instruction_data = randomizeVectorInstructionData(
        instruction, sew, getBaseSuiteTestCount(),
        vd=vd, vs2=vs2, vs1=vs1, lmul=lmul
    )
    writeTest(description, instruction, instruction_data, sew=sew, lmul=lmul)
    incrementBasetestCount()
    vsAddressCount()
```

### Edge Value Test

```python
def make(instruction, sew, xlen, lmul=1):
    from vector_testgen_common import vedgesemul1
    for v in vedgesemul1:
        description = f"cp_custom_edges (vs2 val = {v})"
        instruction_data = randomizeVectorInstructionData(
            instruction, sew, getBaseSuiteTestCount(),
            lmul=lmul, vs2_val_pointer=v
        )
        writeTest(description, instruction, instruction_data, sew=sew, vl=1, lmul=lmul)
        incrementBasetestCount()
```

---

## Available Edge Value Sets

Import from `vector_testgen_common`:

| Name | Description |
|------|-------------|
| `vedgesemul1` through `vedgesemul8` | Integer vector corner values at various EMUL |
| `vedgesemulf2` through `vedgesemulf8` | Integer vector corners for fractional EMUL |
| `vedgeseew1` | Mask (EEW=1) corner values |
| `v_edges_ls` | Load/store address corner values |
| `vfedgesemul1`, `vfedgesemul2` | FP vector corner values |
| `fedges`, `fedgesD`, `fedgesH` | Scalar FP corner values (32/64/16-bit) as dicts: name→value |
| `vxrmList` | Fixed-point rounding modes dict: name→CSR encoding string |
| `frmList` | FP rounding modes dict: name→CSR encoding string |

---

## Instruction Category Lists

Import from `vector_testgen_common` to check instruction type:

| List | Content |
|------|---------|
| `vvvmtype`, `vvxmtype`, `vvimtype` | VV/VX/VI arithmetic instructions |
| `vs1ins` | Instructions that use vs1 operand |
| `narrowins` | Narrowing instructions |
| `vd_widen_ins` | Instructions where vd is 2*SEW wide |
| `vs2_widen_ins` | Instructions where vs2 is 2*SEW wide |
| `wwvins`, `wvvins`, etc. | Widening sub-categories |
| `vfloattypes` | All FP vector instructions |
| `vector_loads`, `vector_stores` | Load/store instructions |
| `indexed_loads`, `indexed_stores` | Indexed load/store instructions |
| `maskins` | Mask-writing instructions |
| `mmins` | Mask-logical instructions |
| `imm_31` | Instructions with unsigned 5-bit immediate (0-31 instead of -16..15) |
| `vextins` | Extension instructions (vzext/vsext) |

---

## Suite Convention

- **"base" suite**: Tests register encodings, edge values, operand overlaps. Usually `vl=1` (default).
- **"length" suite**: Tests VL/LMUL combinations, masking, agnostic bits. Usually `vl="vlmax"` or `vl="random"`.

Use the matching counter functions:
- Base: `getBaseSuiteTestCount()`, `incrementBasetestCount()`, `vsAddressCount()`
- Length: `getLengthSuiteTestCount()`, `incrementLengthtestCount()`, `vsAddressCount("length")`

---

## CSV Context

Custom scripts are triggered by coverpoint names in the CSV `testplans/` files. The CSV has columns for each coverpoint. When a cell contains `x` for an instruction row, that coverpoint is tested for that instruction. The `coverpointInclusions()` function in `vector-testgen-unpriv.py` may expand shorthand coverpoint names (like `cp_custom_wvv`) into multiple specific coverpoints before `makeTest()` processes them.

A custom CSV (e.g. `Vx_custom_definitions.csv`) describes each custom coverpoint with columns: Goal, Feature Description, Expectation, Bins, Pass/Fail Criteria, etc. The Feature Description should tell you procedurally what to set up and test.

---

## File Naming

Name the script file after the coverpoint it handles. For example, coverpoint `cp_custom_foo_bar` → file `cp_custom_foo_bar.py`. The function inside is always called `make`.
