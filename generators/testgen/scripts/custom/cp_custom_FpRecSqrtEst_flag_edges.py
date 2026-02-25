# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_FpRecSqrtEst_flag_edges

Confirm all FP flags are correctly set for reciprocal sqrt estimate (vfrsqrt7.v).
Exercises 8 FP edge-case inputs with fflags clear before execution.
Cross: std_vec x vs1_0_reciprocal_sqrt_edges x fp_flags_clear
"""

from coverpoint_registry import register
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
)

# Map: (data label, description) for each bin in the coverage template
EDGE_CASES = [
    ("vs_corner_f_neg1_emul1", "neg_finite (-1.0)"),
    ("vs_corner_f_neginfinity_emul1", "neg_inf (-Inf)"),
    ("vs_corner_f_neg0_emul1", "neg_zero (-0.0)"),
    ("vs_corner_f_pos0_emul1", "pos_zero (+0.0)"),
    ("vs_corner_f_posinfinity_emul1", "pos_inf (+Inf)"),
    ("vs_corner_f_pos1_emul1", "pos_finite (+1.0)"),
    ("vs_corner_f_canonicalQNaN_emul1", "qNaN (canonical)"),
    ("vs_corner_f_sNaN_payload1_emul1", "sNaN"),
]


@register("cp_custom_FpRecSqrtEst_flag_edges")
def make(test, sew):
    for label, desc in EDGE_CASES:
        description = f"cp_custom_FpRecSqrtEst_flag_edges ({desc})"
        instruction_data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label,
        )
        writeTest(description, test, instruction_data,
                  sew=sew, lmul=1, vl=1)
        incrementBasetestCount()
        vsAddressCount()
