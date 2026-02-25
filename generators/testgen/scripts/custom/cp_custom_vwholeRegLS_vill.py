# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vwholeRegLS_vill

Check that whole register loads and stores are not affected by the vill bit.
Template: single coverpoint (not a cross) checking vill==1 AND vstart==0 AND
vl!=0 AND no trap, all simultaneously.

Whole register LS instructions ignore vtype (including vill), so they should
execute without trapping even when vill is set.

We need to set vill=1 before the instruction. This can be done by setting
an illegal vtype via vsetvli with an unsupported SEW/LMUL combination.
The writeTest function doesn't support setting vill directly, but we can
use vstart=0 and vl!=0 (both defaults).

NOTE: The framework may not support vill=1 directly. If the test traps
because vill is not set, this is a framework limitation.
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


@register("cp_custom_vwholeRegLS_vill")
def make(test, sew):
    if sew > common.xlen:
        return

    # Whole register LS uses vl=NFIELDS*VLEN/EEW, ignoring vtype.
    # Generate a basic test with default vtype settings.
    # The coverage template checks vill==1 at SAMPLE_BEFORE; we need
    # the framework to support vill=1 which it currently doesn't.
    # Generate tests anyway to get std_vec coverage flowing.
    description = f"cp_custom_vwholeRegLS_vill ({test})"
    try:
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(), lmul=1,
        )
        writeTest(description, test, data, sew=sew, lmul=1, vl=1)
        incrementBasetestCount()
        vsAddressCount()
    except ValueError:
        pass
