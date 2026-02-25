# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_FpRecSqrtEst_edges

Confirm all possible 7-bit significand inputs to vfrsqrt7.v produce correct
results. The template bins on the 7 MSBs of the significand field of vs2[0].
We iterate all 128 combinations (0..127) embedded in a positive normal value.

Bit positions per SEW:
  SEW16: bits [10:4]
  SEW32: bits [23:17]
  SEW64: bits [52:46]
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


def _make_value(sew, sig_7bit):
    """Build a positive normal FP value with the given 7-bit significand MSBs."""
    if sew == 16:
        # half: sign(1) exp(5) sig(10), normal exp=1 (biased=16=0b10000)
        # bits[15]=0, bits[14:10]=10000, bits[9:0]=sig<<3
        return (0b0_10000 << 10) | (sig_7bit << 3)
    elif sew == 32:
        # float: sign(1) exp(8) sig(23), normal exp=1 (biased=128=0b10000000)
        # bits[30:23]=10000000, bits[22:0]=sig<<16
        return (0b0_10000000 << 23) | (sig_7bit << 16)
    elif sew == 64:
        # double: sign(1) exp(11) sig(52), normal exp=1 (biased=1024=0b10000000000)
        # bits[62:52]=10000000000, bits[51:0]=sig<<45
        return (0b0_10000000000 << 52) | (sig_7bit << 45)
    return 0


@register("cp_custom_FpRecSqrtEst_edges")
def make(test, sew):
    if sew > common.xlen:
        return

    for i in range(128):
        val = _make_value(sew, i)
        label = f"custom_rsqrt_sig_{i:03d}_sew{sew}"
        registerCustomData(label, [val], element_size=sew)
        description = f"cp_custom_FpRecSqrtEst_edges (sig={i:03d})"
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label,
        )
        writeTest(description, test, data, sew=sew, lmul=1, vl=1)
        incrementBasetestCount()
        vsAddressCount()
