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

**Preset kwargs**: `vd=N`, `vs1=N`, `vs2=N`, `vs3=N`, `rs1=N`, `rs2=N`, `fd=N`, `fs1=N`, `rs1_val=V`, `rs2_val=V`, `fs1_val=V`, `vs1_val_pointer=S`, `vs2_val_pointer=S`, `imm=V`

**`additional_no_overlap`**: e.g. `[['vs1', 'v0'], ['vs2', 'v0'], ['vd', 'v0']]`

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

## Full API Reference

For complete edge value sets, instruction category lists, additional patterns (overlap, VL/LMUL sweep, edge values), and `registerCustomData()` API, see `GUIDE-api-reference.md` in this directory.
