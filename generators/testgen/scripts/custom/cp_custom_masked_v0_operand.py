# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_masked_v0_operand

Verify correct execution when an instruction is masked (vm=0) and uses
v0 as a source operand (v0 serves as both mask and source).

Template has 2 crosses:
- cp_custom_masked_vs2_v0: std_vec × mask_enabled × vs2=v0 × vd!=v0
- cp_custom_masked_vs1_v0: std_vec × mask_enabled × vs1=v0 × vd!=v0

We force vs2=v0 or vs1=v0 with masking enabled, ensuring vd != v0.
"""

from coverpoint_registry import register
import vector_testgen_common as common
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
    vs1ins,
)

from random import randint


@register("cp_custom_masked_v0_operand")
def make(test, sew):
    if sew > common.xlen:
        return

    # Part 1: masked with vs2=v0, vd != v0
    vd = randint(1, 31)  # any register except v0
    description = f"cp_custom_masked_vs2_v0 ({test}, vs2=v0, vd=v{vd}, masked)"
    try:
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(), lmul=1,
            vs2=0, vd=vd,
        )
        writeTest(description, test, data, sew=sew, lmul=1, vl=1, maskval="ones")
        incrementBasetestCount()
        vsAddressCount()
    except ValueError:
        pass  # overlap constraints unsolvable for this instruction/sew combo

    # Part 2: masked with vs1=v0, vd != v0 (only if instruction uses vs1)
    if test in vs1ins:
        vd = randint(1, 31)
        description = f"cp_custom_masked_vs1_v0 ({test}, vs1=v0, vd=v{vd}, masked)"
        try:
            data = randomizeVectorInstructionData(
                test, sew, getBaseSuiteTestCount(), lmul=1,
                vs1=0, vd=vd,
            )
            writeTest(description, test, data, sew=sew, lmul=1, vl=1, maskval="ones")
            incrementBasetestCount()
            vsAddressCount()
        except ValueError:
            pass  # overlap constraints unsolvable for this instruction/sew combo
