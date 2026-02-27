# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_maskLS

Cross: std_vec × lmulgt1 × sewgt8
Sweep LMUL {2,4,8} × SEW {16,32,64} to cover EMUL >= 16 for mask LS.
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


@register("cp_custom_maskLS")
def make(test, sew):
    # emul_ge_16 — sweep LMUL > 1 with SEW > 8
    if sew > 8:
        for lmul in LMULS_GT1:
            description = f"cp_custom_maskLS_emul_ge_16 ({test}, lmul={lmul}, sew={sew})"
            try:
                data = randomizeVectorInstructionData(
                    test, sew, getBaseSuiteTestCount(), lmul=lmul,
                )
            except ValueError:
                continue
            writeTest(description, test, data, sew=sew, lmul=lmul, vl=1)
            incrementBasetestCount()
            vsAddressCount()
