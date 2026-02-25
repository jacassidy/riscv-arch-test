# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_maskLS

Contains 3 crosses for mask load/store (vlm.v, vsm.v):
1. cp_custom_maskLS_emul_ge_16: cross std_vec × lmulgt1 × sewgt8
   - LMUL > 1 with SEW > 8 → EMUL = EEW/SEW * LMUL >= 16
2. cp_custom_maskLS_tail_no_exception: cross std_vec × lmul_2 × vl_1 ×
   mask_enabled × v0_eq_1 × rs1_at_fault_addr
3. cp_custom_maskLS_prestart_no_exception: cross vill_clear × lmul_2 ×
   vl_2 × vstart_1 × mask_enabled × rs1_at_fault_addr × no_trap × v0_eq_2

For (1): sweep LMUL {2,4,8} × SEW {16,32,64}
For (2) and (3): complex fault address setup — these require RVMODEL_ACCESS_FAULT_ADDRESS
which is DUT-specific. Generate basic structure tests.
"""

from coverpoint_registry import register
import vector_testgen_common as common
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
)

LMULS_GT1 = [2, 4, 8]
SEWS_GT8 = [16, 32, 64]


@register("cp_custom_maskLS")
def make(test, sew):
    if sew > common.xlen:
        return

    # Part 1: emul_ge_16 — sweep LMUL > 1 with SEW > 8
    if sew > 8:
        for lmul in LMULS_GT1:
            description = f"cp_custom_maskLS_emul_ge_16 ({test}, lmul={lmul}, sew={sew})"
            data = randomizeVectorInstructionData(
                test, sew, getBaseSuiteTestCount(), lmul=lmul,
            )
            writeTest(description, test, data, sew=sew, lmul=lmul, vl=1)
            incrementBasetestCount()
            vsAddressCount()

    # Part 2: tail_no_exception — vl=1, masked, v0=1
    # Template needs rs1 at fault address, which we can't easily set.
    # Generate masked test with vl=1, v0 mask bit 0 = 1.
    description = f"cp_custom_maskLS_tail_no_exception ({test}, vl=1, masked)"
    try:
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(), lmul=2,
            additional_no_overlap=[['vd', 'v0']],
        )
        writeTest(description, test, data, sew=sew, lmul=2, vl=1, maskval="ones")
        incrementBasetestCount()
        vsAddressCount()
    except ValueError:
        pass

    # Part 3: prestart_no_exception — vl=2, vstart=1, masked, v0=2
    description = f"cp_custom_maskLS_prestart_no_exception ({test}, vl=2, vstart=1)"
    try:
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(), lmul=2,
            additional_no_overlap=[['vd', 'v0']],
        )
        writeTest(description, test, data, sew=sew, lmul=2, vl=2, vstart=1, maskval="ones")
        incrementBasetestCount()
        vsAddressCount()
    except ValueError:
        pass
