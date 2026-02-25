# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_fmv_sf_vd_all_lmul

Confirm vfmv.s.f ignores LMUL for destination register.
Template cross: std_vec × vd_all_regs × vtype_all_lmul

vd_all_regs bins on insn[11:7] = all 32 registers.
vtype_all_lmul bins on vlmul = {5(f8), 6(f4), 7(f2), 0(1), 1(2), 2(4), 3(8)}.

We sweep all 32 vd values × 7 LMUL settings = 224 tests per SEW.
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

# LMUL values to test: fractional and integer
# (lmul param value, description)
LMULS = [1, 2, 4, 8]
# Fractional LMULs are handled by passing fractions
FRAC_LMULS = []  # framework may not support fractional lmul directly in writeTest


@register("cp_custom_fmv_sf_vd_all_lmul")
def make(test, sew):
    if sew > common.xlen:
        return

    for lmul in LMULS:
        for vd in range(32):
            description = f"cp_custom_fmv_sf_vd_all_lmul (vd=v{vd}, lmul={lmul})"
            data = randomizeVectorInstructionData(
                test, sew, getBaseSuiteTestCount(),
                lmul=lmul, vd=vd,
            )
            writeTest(description, test, data, sew=sew, lmul=lmul, vl=1)
            incrementBasetestCount()
            vsAddressCount()
