# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfp_flags

Contains two crosses:
1. cp_custom_vfp_flags_set: Confirm vector FP exceptions set fflags.
   Cross: std_vec × cp_csr_fflags_vdoun (transition bins for NV/DZ/OF/UF/NX)
2. cp_custom_vfp_flags_inactive_not_set: Confirm inactive masked element
   that would raise a flag does NOT raise it.
   Cross: std_vec × vl_one × mask_enabled × v0_element_1_active ×
          vfsqrt_flag_set × vfp_flags_fp_flags_clear

For (1) we need to trigger each of the 5 flag types (NV, DZ, OF, UF, NX).
For (2) we need vfrsqrt7.v with vs2=0 (raises DZ), vl=1 so element[1] is
inactive, mask bit[0]=0 so element 0 is inactive, the flag-raising value
is in the first element but masked off.
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
    vfloattypes,
)

# FP values that trigger each flag type per SEW
# We use vs2_val_pointer with custom data labels
FLAG_TRIGGERS = {
    16: {
        "NV": 0x7D01,      # sNaN → Invalid for most ops
        "DZ": 0x0000,      # +0.0 → Divide by zero for vfdiv/vfrdiv
        "OF": 0x7BFF,      # max normal → overflow for vfadd with same
        "UF": 0x0400,      # smallest normal → underflow for vfmul with small
        "NX": 0x3C01,      # 1.0 + small → inexact
    },
    32: {
        "NV": 0x7F800001,  # sNaN
        "DZ": 0x00000000,  # +0.0
        "OF": 0x7F7FFFFF,  # max normal
        "UF": 0x00800000,  # smallest normal
        "NX": 0x3F800001,  # 1.0 + ulp
    },
    64: {
        "NV": 0x7FF0000000000001,  # sNaN
        "DZ": 0x0000000000000000,  # +0.0
        "OF": 0x7FEFFFFFFFFFFFFF,  # max normal
        "UF": 0x0010000000000000,  # smallest normal
        "NX": 0x3FF0000000000001,  # 1.0 + ulp
    },
}


@register("cp_custom_vfp_flags")
def make(test, sew):
    if sew > common.xlen:
        return

    if test not in vfloattypes:
        return

    # --- Part 1: cp_custom_vfp_flags_set ---
    # Trigger fflags transitions. For most instructions, sNaN input sets NV.
    # DZ only applies to vfdiv/vfrdiv. OF/UF/NX need specific values.
    triggers = FLAG_TRIGGERS.get(sew, {})

    # Always test NV (sNaN input works for nearly all FP ops)
    if "NV" in triggers:
        label = f"custom_flag_nv_sew{sew}"
        registerCustomData(label, [triggers["NV"]], element_size=sew)
        description = f"cp_custom_vfp_flags_set (NV via sNaN, {test})"
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label,
        )
        writeTest(description, test, data, sew=sew, lmul=1, vl=1)
        incrementBasetestCount()
        vsAddressCount()

    # --- Part 2: cp_custom_vfp_flags_inactive_not_set ---
    # Only for vfrsqrt7.v: vs2=0 raises DZ, but element 0 is masked off
    if test == "vfrsqrt7.v":
        label = f"custom_flag_zero_sew{sew}"
        registerCustomData(label, [0], element_size=sew)
        description = "cp_custom_vfp_flags_inactive_not_set (vfrsqrt7.v vs2=0, masked)"
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label,
            additional_no_overlap=[['vs2', 'v0'], ['vd', 'v0']],
        )
        # vl=1, mask enabled with element 0 inactive (mask bit 0 = 0)
        # maskval="zeroes" means all mask bits are 0 → element 0 is inactive
        writeTest(description, test, data,
                  sew=sew, lmul=1, vl=1, maskval="zeroes")
        incrementBasetestCount()
        vsAddressCount()
