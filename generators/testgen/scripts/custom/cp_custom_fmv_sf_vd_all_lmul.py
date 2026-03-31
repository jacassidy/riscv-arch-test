# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_fmv_sf_vd_all_lmul

Confirm vfmv.s.f ignores LMUL for destination register.
Template cross: std_vec × vd_all_regs × vtype_all_lmul

Strategy: 32 vd values at LMUL=1 (covers all vd_all_regs bins) +
1 vd per additional LMUL (covers LMUL bins). Total ~38 tests.
Full cross coverage (32×7=224 bins) requires RTL simulation.
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

# All LMUL values including fractional
ALL_LMULS = [0.125, 0.25, 0.5, 1, 2, 4, 8]


@register("cp_custom_fmv_sf_vd_all_lmul")
def make(test, sew):
    if sew > common.flen:
        return

    # Filter: LMUL must be >= SEW/ELEN for valid vtype (fractional LMUL only supports SEW <= LMUL*ELEN)
    valid_lmuls = [l for l in ALL_LMULS if l >= sew / common.maxELEN]

    for lmul in valid_lmuls:
        # LMUL=1: all 32 regs. Others: just vd=0 to hit the LMUL bin.
        vd_values = range(32) if lmul == 1 else [0]
        for vd in vd_values:
            description = f"cp_custom_fmv_sf_vd_all_lmul (vd=v{vd}, lmul={lmul})"
            try:
                data = randomizeVectorInstructionData(
                    test, sew, getBaseSuiteTestCount(),
                    lmul=lmul, vd=vd,
                )
            except ValueError:
                continue
            writeTest(description, test, data, sew=sew, lmul=lmul, vl=1)
            incrementBasetestCount()
            vsAddressCount()
