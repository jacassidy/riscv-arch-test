# Custom Test Generation Scripts Guide

## Function Signature

```python
from coverpoint_registry import register
from vector_testgen_common import (
    writeTest, randomizeVectorInstructionData,
    incrementBasetestCount, getBaseSuiteTestCount, vsAddressCount,
    incrementLengthtestCount, getLengthSuiteTestCount,
    randomizeMask, randomizeOngroupVectorRegister, vreg_count,
)

@register("cp_custom_YOUR_NAME_HERE")
def make(test, sew):
    # test = instruction mnemonic (e.g. "vfrsqrt7.v")
    # sew = selected element width (8, 16, 32, 64)
```

The `@register` decorator is **required**. It must match the **CSV column name** in `testplans/`.

## Core API

### `randomizeVectorInstructionData(instruction, sew, test_count, suite="base", lmul=1, additional_no_overlap=None, **preset_variables)`

Returns `[vector_register_data, scalar_register_data, floating_point_register_data, imm_val]`.

**Preset kwargs**: `vd=N`, `vs1=N`, `vs2=N`, `vs3=N`, `rs1=N`, `rs2=N`, `fd=N`, `fs1=N`, `rs1_val=V`, `rs2_val=V`, `fs1_val=V`, `vs1_val_pointer=S`, `vs2_val_pointer=S`, `vd_val_pointer=S`, `vs3_val_pointer=S`, `imm=V`

**`additional_no_overlap`**: e.g. `[['vs1', 'v0'], ['vs2', 'v0'], ['vd', 'v0']]`

#### What the function handles automatically — DO NOT duplicate in scripts

The function inspects the `instruction` string and automatically configures:

1. **EMUL for LS instructions**: Looks up EEW from instruction category lists (`eew8_ins`, `eew16_ins`, `eew32_ins`, `eew64_ins`). Sets `size_multiplier = EEW/SEW` on the correct operand (vd for loads, vs3 for stores, vs2 for indexed). The register assigner then uses `EMUL = size_multiplier × lmul` for alignment and spacing.

2. **Segments for segmented instructions**: Parses nf from `seg2`–`seg8` category lists. Sets `segments` on all vector operands. Register assignment ensures `nf × EMUL` registers fit without exceeding v31.

3. **Widening/narrowing multipliers**: Automatically sets `size_multiplier=2` on widened operands (vd and/or vs1/vs2 depending on instruction type via `getVectorEmulMultipliers`).

4. **Architecture-mandated overlap constraints**: `getInstructionRegisterOverlapConstraints` adds the correct `_top`/`_bottom` overlap rules for widening, narrowing, mask-producing, compress, vext, and indexed segment instructions. You only need `additional_no_overlap` for constraints beyond the spec requirements (e.g., `['vd', 'v0']` to prevent vd=v0 when masking).

5. **rs1 address for LS**: For load/store instructions, auto-sets `rs1_val_pointer = "vector_ls_random_base"` (valid memory).

6. **rs2 stride for strided LS**: Auto-sets `rs2_val` to a valid stride value (`±N × EEW/8`).

7. **Whole register LS**: Uses `nfields` as the effective LMUL (overrides the `lmul` argument).

8. **Mask/scalar register types**: Sets `reg_type="mask"` or `"scalar"` for mask-producing, reduction, and move instructions so those operands use EMUL=1.

#### RISC-V V spec constraint: nf × EMUL ≤ 8

Per the RISC-V V spec, `nf × EMUL` must not exceed 8. Operations violating this are **illegal** and must never be generated. When `lmul > 1` and the instruction has `EEW ≠ SEW` or `nf > 1`, the effective EMUL can grow beyond what the script author intended. Example: `vlseg3e64ff.v` with SEW=16, LMUL=2 → EMUL = 64/16 × 2 = 8, nf=3 → nf × EMUL = 24 (illegal).

**Any script that uses `lmul > 1` with LS instructions must guard against this.** The function handles register assignment correctly for legal cases, but it cannot reject illegal SEW/LMUL/EEW/nf combinations — that is the script's responsibility.

Guard pattern:

```python
import re

def _get_eew(instruction):
    """Get EEW from instruction name (e.g., vlseg3e64ff.v → 64). Returns None if SEW-based."""
    m = re.search(r'e(\d+)', instruction.split('seg')[-1] if 'seg' in instruction else instruction)
    return int(m.group(1)) if m else None

def _get_nf(instruction):
    """Get nfields from segmented instruction name. Returns 1 if not segmented."""
    m = re.search(r'seg(\d+)', instruction)
    return int(m.group(1)) if m else 1

# In make():
eew = _get_eew(test)
if eew is not None:
    emul = eew * lmul // sew
else:
    emul = lmul
nf = _get_nf(test)
if emul * nf > 8:
    return  # Illegal: nf × EMUL exceeds 8
```

### `writeTest(description, instruction, instruction_data, sew=None, lmul=1, vl=1, vstart=0, maskval=None, vxrm=None, frm=None, vxsat=None, vta=0, vma=0)`

Mask values: `"ones"`, `"zeroes"`, `"vlmaxm1_ones"`, `"vlmaxd2p1_ones"`, `"cp_mask_random"`, `"random_mask_0"`/`1`/`2`, or `None`

### Counters

Call after each `writeTest`: `incrementBasetestCount()` + `vsAddressCount()` (base suite) or `incrementLengthtestCount()` + `vsAddressCount("length")` (length suite).

## Two Core Patterns

### Base suite — register/value sweep

```python
for v in range(vreg_count):
    data = randomizeVectorInstructionData(test, sew, getBaseSuiteTestCount(), lmul=1, vd=v)
    writeTest(f"test vd=v{v}", test, data, sew=sew, lmul=1)
    incrementBasetestCount()
    vsAddressCount()
```

### Length suite — masked test

```python
maskval = randomizeMask(test, always_masked=True)
no_overlap = [['vs1', 'v0'], ['vs2', 'v0'], ['vd', 'v0']]
data = randomizeVectorInstructionData(test, sew, getLengthSuiteTestCount(), suite="length", lmul=1, additional_no_overlap=no_overlap)
writeTest("masked test", test, data, sew=sew, lmul=1, vl="vlmax", maskval=maskval)
incrementLengthtestCount()
vsAddressCount("length")
```

## Important: Register Assignment for LS Instructions

For load/store instructions, EMUL = EEW/SEW × LMUL, which can differ from LMUL. **Never manually pick vd with `randint()`** — the register assigner inside `randomizeVectorInstructionData` handles EMUL alignment automatically. Use `additional_no_overlap` to add constraints:

```python
# WRONG — vd may not be EMUL-aligned for LS instructions
vd = randint(1, 31)
data = randomizeVectorInstructionData(test, sew, count, lmul=1, vs2=0, vd=vd)

# RIGHT — let assigner pick vd, constrain with no_overlap
data = randomizeVectorInstructionData(test, sew, count, lmul=1, vs2=0,
    additional_no_overlap=[['vd', 'v0']])
```

## Full API Reference

For complete edge value sets, instruction category lists, additional patterns (overlap, VL/LMUL sweep, edge values), and `registerCustomData()` API, see `GUIDE-api-reference.md` in this directory.
