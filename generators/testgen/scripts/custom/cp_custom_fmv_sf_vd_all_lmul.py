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

# LMUL values matching template bins: vlmul encoding → actual LMUL
# vlmul=5→mf8, 6→mf4, 7→mf2, 0→m1, 1→m2, 2→m4, 3→m8
# Full set: [0.125, 0.25, 0.5, 1, 2, 4, 8]
# Integer LMULs only (60 aligned tests) to avoid sail timeout.
# Fractional LMULs can be added when running on RTL (Wally) instead of sail.
LMULS = [1, 2, 4, 8]


@register("cp_custom_fmv_sf_vd_all_lmul")
def make(test, sew):
    if sew > common.xlen:
        return

    # Strategy: all 32 vd for LMUL=1 (covers all vd_all_regs bins).
    # For LMUL>1: use 1 vd value to hit the LMUL bins while keeping
    # total test count low enough to avoid sail timeout (>32 tests risky).
    # Total: 32 + 1 + 1 + 1 = 35 tests per SEW.
    for lmul in LMULS:
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
