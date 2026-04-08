# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_ffLS_update_vl

Template cross: std_vec × vtype_lmul_2 × vl_max × mask_enabled × v0_eq_1

Requires: LMUL=2, vl=VLMAX, masking enabled (vm=0), v0 register = 1
(only element 0 active).

The maskval="zeroes" path zeros v0 via vmv.v.i, then pre_test_lines
override element 0 to set bit 0 = 1.  This gives unsigned(v0) == 1.
"""

import re
from coverpoint_registry import register
import vector_testgen_common as common
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
    getLmulFlag,
)


def _get_eew(instruction: str) -> int | None:
    """Get EEW from instruction name (e.g., vlseg3e64ff.v → 64)."""
    m = re.search(r'e(\d+)', instruction.split('seg')[-1] if 'seg' in instruction else instruction)
    return int(m.group(1)) if m else None


def _get_nf(instruction: str) -> int:
    """Get nfields from segmented instruction name. Returns 1 if not segmented."""
    m = re.search(r'seg(\d+)', instruction)
    return int(m.group(1)) if m else 1


@register("cp_custom_ffLS_update_vl")
def make(test: str, sew: int) -> None:
    lmul = 2

    # nf × EMUL must not exceed 8 (RISC-V V spec constraint)
    eew = _get_eew(test)
    emul = (eew * lmul // sew) if eew is not None else lmul
    nf = _get_nf(test)
    if emul * nf > 8:
        return

    description = f"cp_custom_ffLS_update_vl ({test}, lmul=2, vl=vlmax, masked, v0=1)"
    try:
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(), lmul=lmul,
            additional_no_overlap=[['vd', 'v0']],
        )
        rs1 = int(data[1]['rs1']['reg'])
        # Pick a temp register for vsetvli that won't clobber rs1
        temp = 31 if rs1 != 31 else 30

        lmulflag = getLmulFlag(lmul)
        # maskval="zeroes" zeros all of v0 (vmv.v.i v0, 0 at LMUL=2, vl=VLMAX).
        # pre_test_lines then set only bit 0 and restore vtype/vl.
        pre_lines = [
            "vsetivli x0, 1, e8, m1, tu, mu",
            "vmv.v.i v0, 1",
            f"vsetvli x{temp}, x0, e{sew}, m{lmulflag}, tu, mu",
        ]
        writeTest(description, test, data, sew=sew, lmul=lmul, vl="vlmax",
                  maskval="zeroes", pre_test_lines=pre_lines)
        incrementBasetestCount()
        vsAddressCount()
    except ValueError:
        pass
