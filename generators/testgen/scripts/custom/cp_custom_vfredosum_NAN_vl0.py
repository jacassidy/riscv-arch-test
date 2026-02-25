# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfredosum_NAN_vl0

Confirm that if there are no active elements (vl=0), vs1[0] is simply
copied over and does not canonicalize NaN.

Template cross: fp_flags_clear × vtype_prev_vill_clear × vl_zero ×
                vstart_zero × vs1_0_qNAN (iff no trap)

We need: vl=0, vstart=0, vs1[0]=qNaN, fflags clear, vill clear.
"""

from coverpoint_registry import register
import vector_testgen_common as common
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
    registerCustomData,
)

# qNaN values per SEW
QNAN = {
    16: 0x7E00,
    32: 0x7FC00000,
    64: 0x7FF8000000000000,
}


@register("cp_custom_vfredosum_NAN_vl0")
def make(test, sew):
    if sew > common.xlen:
        return

    qnan = QNAN.get(sew)
    if qnan is None:
        return

    label = f"custom_redosum_qnan_sew{sew}"
    registerCustomData(label, [qnan], element_size=sew)

    description = f"cp_custom_vfredosum_NAN_vl0 ({test}, vl=0, vs1[0]=qNaN)"
    data = randomizeVectorInstructionData(
        test, sew, getBaseSuiteTestCount(),
        lmul=1, vs1_val_pointer=label,
    )
    # vl=0, vstart=0 (default)
    writeTest(description, test, data, sew=sew, lmul=1, vl=0)
    incrementBasetestCount()
    vsAddressCount()
