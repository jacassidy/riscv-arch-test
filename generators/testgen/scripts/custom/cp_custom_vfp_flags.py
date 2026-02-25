# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfp_flags

Contains two crosses:
1. cp_custom_vfp_flags_set: Confirm vector FP exceptions set fflags.
   Cross: std_vec × cp_csr_fflags_vdoun (transition bins for NV/DZ/OF/UF/NX)
2. cp_custom_vfp_flags_inactive_not_set: Confirm inactive masked element
   that would raise a flag does NOT raise it.
   Cross: std_vec × vl_one × mask_enabled × v0_element_1_active ×
          vfsqrt_flag_set × vfp_flags_fp_flags_clear

The transition bins track consecutive samples of fflags AFTER each instruction
execution within the covergroup instance. To hit both the "0→1" and "1→1"
variants, test cases must be ordered so that a non-flag-setting test comes
BEFORE a flag-setting test:
  - NX first (sets only bit 0), then NV (sets bit 4 from 0→1) → covers NV
  - Two NV tests back-to-back → covers NV1

For DZ: the DIVISOR must be zero, not the dividend.
  - vfdiv.vv vd, vs2, vs1: vs1 is the divisor → use vs1_val_pointer
  - vfdiv.vf/vfrdiv.vf: f[rs1] is the scalar → use rs1_val_pointer... but
    that's not supported; instead use vs2_val_pointer for the non-zero operand
    and hope the scalar is non-zero. Better: for vfrsqrt7.v, vs2=0 raises DZ.
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

# Instructions that do NOT set fflags — skip these for flag coverage
NO_FLAG_INSTRUCTIONS = {
    "vfmerge.vfm",      # merge — no arithmetic
    "vfmv.v.f",         # move — no arithmetic
    "vfmv.f.s",         # move — no arithmetic
    "vfmv.s.f",         # move — no arithmetic
    "vfsgnj.vv",        # sign injection — no arithmetic
    "vfsgnj.vf",
    "vfsgnjn.vv",
    "vfsgnjn.vf",
    "vfsgnjx.vv",
    "vfsgnjx.vf",
    "vfslide1up.vf",    # slide — no arithmetic
    "vfslide1down.vf",
    "vfclass.v",        # classify — no arithmetic
}

# Instructions that can raise DZ (divide by zero)
DZ_INSTRUCTIONS = {"vfdiv.vv", "vfdiv.vf", "vfrdiv.vf", "vfrsqrt7.v"}

# Instructions good for triggering OF (overflow via large values added together)
OF_INSTRUCTIONS = {"vfadd.vv", "vfadd.vf", "vfmul.vv", "vfmul.vf"}

# Instructions good for triggering UF (underflow via tiny value * tiny value)
UF_INSTRUCTIONS = {"vfmul.vv", "vfmul.vf"}

# FP values that trigger each flag type per SEW
FLAG_TRIGGERS = {
    16: {
        "NV": 0x7D01,      # sNaN → Invalid for most ops
        "DZ": 0x0000,      # +0.0 → Divide by zero for divisor
        "OF": 0x7BFF,      # max normal → overflow for vfadd with same
        "UF": 0x0080,      # very small normal → underflow for vfmul
        "NX": 0x3C01,      # 1.0 + ulp → inexact
        "ONE": 0x3C00,     # 1.0 (non-zero, non-sNaN for DZ dividend)
    },
    32: {
        "NV": 0x7F800001,  # sNaN
        "DZ": 0x00000000,  # +0.0
        "OF": 0x7F7FFFFF,  # max normal
        "UF": 0x00800001,  # small normal → underflow for mul
        "NX": 0x3F800001,  # 1.0 + ulp
        "ONE": 0x3F800000, # 1.0
    },
    64: {
        "NV": 0x7FF0000000000001,  # sNaN
        "DZ": 0x0000000000000000,  # +0.0
        "OF": 0x7FEFFFFFFFFFFFFF,  # max normal
        "UF": 0x0010000000000001,  # small normal
        "NX": 0x3FF0000000000001,  # 1.0 + ulp
        "ONE": 0x3FF0000000000000, # 1.0
    },
}


def _gen_test(test, sew, label_name, value, description, **extra_kwargs):
    """Generate a single flag-triggering test case."""
    registerCustomData(label_name, [value], element_size=sew)
    kwargs = {"lmul": 1, "vs2_val_pointer": label_name}
    kwargs.update(extra_kwargs)
    data = randomizeVectorInstructionData(
        test, sew, getBaseSuiteTestCount(), **kwargs,
    )
    writeTest(description, test, data, sew=sew, lmul=1, vl=1)
    incrementBasetestCount()
    vsAddressCount()


def _gen_test_two_operands(test, sew, label1, val1, label2, val2, description):
    """Generate test with both vs2 and vs1 (or vs2 and rs1 for .vf) set."""
    registerCustomData(label1, [val1], element_size=sew)
    registerCustomData(label2, [val2], element_size=sew)
    # For .vv: vs2_val_pointer + vs1_val_pointer
    # For .vf: vs2_val_pointer is the vector operand
    if test.endswith(".vv") or test.endswith(".vs"):
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label1, vs1_val_pointer=label2,
        )
    else:
        # For .vf: vs2 is vector, scalar rs1/fs1 is from randomized data
        # We can only control vs2; just use the first operand label
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label1,
        )
    writeTest(description, test, data, sew=sew, lmul=1, vl=1)
    incrementBasetestCount()
    vsAddressCount()


@register("cp_custom_vfp_flags")
def make(test, sew):
    if sew > common.xlen:
        return

    if test not in vfloattypes:
        return

    # Skip instructions that can't set fflags
    if test in NO_FLAG_INSTRUCTIONS:
        return

    triggers = FLAG_TRIGGERS.get(sew, {})
    if not triggers:
        return

    # --- Part 1: cp_custom_vfp_flags_set ---
    # IMPORTANT: Order matters for transition bins!
    # The covergroup samples fflags AFTER each execution of this instruction.
    # Transition bins track consecutive samples:
    #   NV  = (5'b0???? => 5'b1????) means "bit4 was 0, now 1"
    #   NV1 = (5'b1???? => 5'b1????) means "bit4 was 1, still 1"
    # To cover NV: need a non-NV test BEFORE an NV test
    # To cover NV1: need two consecutive NV-setting tests
    # So order: [NX, NV, NV] → covers NX, NV (0→1), NV1 (1→1)

    # Test 1: NX (inexact) — comes first so later NV test has bit4=0 before
    if "NX" in triggers:
        _gen_test(test, sew,
                  f"custom_flag_nx_sew{sew}", triggers["NX"],
                  f"cp_custom_vfp_flags_set (NX via inexact, {test})")

    # Test 2: NV (sNaN input) — bit4 transitions 0→1, covering NV bin
    if "NV" in triggers:
        _gen_test(test, sew,
                  f"custom_flag_nv_sew{sew}", triggers["NV"],
                  f"cp_custom_vfp_flags_set (NV via sNaN, {test})")

    # Test 3: NV again — bit4 stays 1→1 (fflags cleared between, but
    # this instruction re-sets NV, and previous sample was NV), covers NV1
    if "NV" in triggers:
        _gen_test(test, sew,
                  f"custom_flag_nv_sew{sew}", triggers["NV"],
                  f"cp_custom_vfp_flags_set (NV1 via sNaN again, {test})")

    # Test 4: DZ — only for div/rsqrt instructions
    if test in DZ_INSTRUCTIONS and "DZ" in triggers:
        if test == "vfrsqrt7.v":
            # vfrsqrt7 uses vs2 as input: rsqrt(0) = Inf, raises DZ
            _gen_test(test, sew,
                      f"custom_flag_dz_sew{sew}", triggers["DZ"],
                      f"cp_custom_vfp_flags_set (DZ via zero, {test})")
        elif test == "vfdiv.vv":
            # vfdiv.vv vd, vs2, vs1: divisor is vs1, dividend is vs2
            # Need vs1=0 (zero divisor) and vs2=non-zero (non-zero dividend)
            _gen_test_two_operands(test, sew,
                                  f"custom_flag_one_sew{sew}", triggers["ONE"],
                                  f"custom_flag_dz_sew{sew}", triggers["DZ"],
                                  f"cp_custom_vfp_flags_set (DZ via zero divisor, {test})")
        elif test in {"vfdiv.vf", "vfrdiv.vf"}:
            # .vf: scalar rs1 is from register, we can't directly control it
            # For vfdiv.vf: vd = vs2 / f[rs1] — need f[rs1]=0
            # For vfrdiv.vf: vd = f[rs1] / vs2 — need vs2=0
            if test == "vfrdiv.vf":
                _gen_test(test, sew,
                          f"custom_flag_dz_sew{sew}", triggers["DZ"],
                          f"cp_custom_vfp_flags_set (DZ via zero vs2, {test})")

    # Test 5: OF — overflow via large values
    if test in OF_INSTRUCTIONS and "OF" in triggers:
        if test.endswith(".vv"):
            _gen_test_two_operands(test, sew,
                                  f"custom_flag_of_sew{sew}", triggers["OF"],
                                  f"custom_flag_of2_sew{sew}", triggers["OF"],
                                  f"cp_custom_vfp_flags_set (OF via max+max, {test})")
        else:
            _gen_test(test, sew,
                      f"custom_flag_of_sew{sew}", triggers["OF"],
                      f"cp_custom_vfp_flags_set (OF via max normal, {test})")

    # Test 6: UF — underflow via tiny values multiplied
    if test in UF_INSTRUCTIONS and "UF" in triggers:
        if test.endswith(".vv"):
            _gen_test_two_operands(test, sew,
                                  f"custom_flag_uf_sew{sew}", triggers["UF"],
                                  f"custom_flag_uf2_sew{sew}", triggers["UF"],
                                  f"cp_custom_vfp_flags_set (UF via tiny*tiny, {test})")
        else:
            _gen_test(test, sew,
                      f"custom_flag_uf_sew{sew}", triggers["UF"],
                      f"cp_custom_vfp_flags_set (UF via tiny, {test})")

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
        writeTest(description, test, data,
                  sew=sew, lmul=1, vl=1, maskval="zeroes")
        incrementBasetestCount()
        vsAddressCount()
