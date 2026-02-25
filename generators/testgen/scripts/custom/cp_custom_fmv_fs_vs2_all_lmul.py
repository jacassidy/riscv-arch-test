# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_fmv_fs_vs2_all_lmul

Confirm vfmv.f.s ignores LMUL for source register.
Template cross: std_vec × vs2_all_regs × vtype_all_lmul

vs2_all_regs bins on insn[24:20] = all 32 registers.
vtype_all_lmul bins on vlmul = {5(f8), 6(f4), 7(f2), 0(1), 1(2), 2(4), 3(8)}.

We sweep all 32 vs2 values × 7 LMUL settings = 224 tests per SEW.
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

LMULS = [1, 2, 4, 8]


@register("cp_custom_fmv_fs_vs2_all_lmul")
def make(test, sew):
    if sew > common.xlen:
        return

    for lmul in LMULS:
        for vs2 in range(32):
            description = f"cp_custom_fmv_fs_vs2_all_lmul (vs2=v{vs2}, lmul={lmul})"
            data = randomizeVectorInstructionData(
                test, sew, getBaseSuiteTestCount(),
                lmul=lmul, vs2=vs2,
            )
            writeTest(description, test, data, sew=sew, lmul=lmul, vl=1)
            incrementBasetestCount()
            vsAddressCount()
