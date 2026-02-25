# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_FpRecipEst_flag_edges

Confirm all FP flags are correctly set for reciprocal estimate (vfrec7.v).
14 edge bins per SEW covering negative/positive subnormals, normals, zeros,
infinities, qNaN, and sNaN.

NOTE: Template uses ins.current.vs1 but vfrec7.v is VVM unary (source=vs2).
The template may need fixing to use vs2_val. We load data into vs2 regardless.
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

# Per-SEW edge values matching the template bins exactly
EDGES = {
    16: [
        (0xFC00, "neg_inf"),
        (0x8000, "neg_zero"),
        (0x8001, "neg_sub_tiny"),
        (0x83FF, "neg_sub_big"),
        (0xBC00, "neg_norm_small"),
        (0xFBFF, "neg_norm_big"),
        (0x0000, "pos_zero"),
        (0x0001, "pos_sub_tiny"),
        (0x03FF, "pos_sub_big"),
        (0x3C00, "pos_norm_small"),
        (0x7BFF, "pos_norm_big"),
        (0x7C00, "pos_inf"),
        (0x7E00, "qNaN"),
        (0x7D00, "sNaN"),
    ],
    32: [
        (0xFF800000, "neg_inf"),
        (0x80000000, "neg_zero"),
        (0x80000001, "neg_sub_tiny"),
        (0x807FFFFF, "neg_sub_big"),
        (0xBF800000, "neg_norm_small"),
        (0xFF7FFFFF, "neg_norm_big"),
        (0x00000000, "pos_zero"),
        (0x00000001, "pos_sub_tiny"),
        (0x007FFFFF, "pos_sub_big"),
        (0x3F800000, "pos_norm_small"),
        (0x7F7FFFFF, "pos_norm_big"),
        (0x7F800000, "pos_inf"),
        (0x7FC00000, "qNaN"),
        (0x7FA00000, "sNaN"),
    ],
    64: [
        (0xFFF0000000000000, "neg_inf"),
        (0x8000000000000000, "neg_zero"),
        (0x8000000000000001, "neg_sub_tiny"),
        (0x800FFFFFFFFFFFFF, "neg_sub_big"),
        (0xBFF0000000000000, "neg_norm_small"),
        (0xFFEFFFFFFFFFFFFF, "neg_norm_big"),
        (0x0000000000000000, "pos_zero"),
        (0x0000000000000001, "pos_sub_tiny"),
        (0x000FFFFFFFFFFFFF, "pos_sub_big"),
        (0x3FF0000000000000, "pos_norm_small"),
        (0x7FEFFFFFFFFFFFFF, "pos_norm_big"),
        (0x7FF0000000000000, "pos_inf"),
        (0x7FF8000000000000, "qNaN"),
        (0x7FF0000000000001, "sNaN"),
    ],
}


@register("cp_custom_FpRecipEst_flag_edges")
def make(test, sew):
    if sew > common.xlen:
        return

    edges = EDGES.get(sew, [])
    for val, desc in edges:
        label = f"custom_recip_edge_{desc}_sew{sew}"
        registerCustomData(label, [val], element_size=sew)
        description = f"cp_custom_FpRecipEst_flag_edges ({desc})"
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label,
        )
        writeTest(description, test, data, sew=sew, lmul=1, vl=1)
        incrementBasetestCount()
        vsAddressCount()
