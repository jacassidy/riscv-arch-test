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

from coverpoint_registry import register, REGISTRY
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
# vfrec7.v: vfrec7(0) = +Inf, raises DZ
DZ_INSTRUCTIONS = {"vfdiv.vv", "vfdiv.vf", "vfrdiv.vf", "vfrsqrt7.v", "vfrec7.v"}

# Instructions good for triggering OF (overflow via large values added together)
OF_INSTRUCTIONS = {"vfadd.vv", "vfadd.vf", "vfmul.vv", "vfmul.vf"}

# Instructions good for triggering UF (underflow via tiny value * tiny value)
UF_INSTRUCTIONS = {"vfmul.vv", "vfmul.vf"}

# Narrowing int→float: source register has 2*sew-wide INTEGER elements.
# Data must be loaded at element_size=2*sew, and NX triggers must be integers
# that exceed the destination float mantissa precision.
NARROWING_INT_TO_FLOAT = {"vfncvt.f.x.w", "vfncvt.f.xu.w"}

# ALL instructions whose vs2 source has 2*sew-wide elements.
# Includes all narrowing (.w suffix) and widening-wide (.wv/.wf) instructions.
# Data must be loaded at element_size=2*sew for these.
WIDE_SOURCE_INSTRUCTIONS = {
    # Narrowing float→float
    "vfncvt.f.f.w", "vfncvt.rod.f.f.w",
    # Narrowing float→int
    "vfncvt.x.f.w", "vfncvt.xu.f.w", "vfncvt.rtz.x.f.w", "vfncvt.rtz.xu.f.w",
    # Narrowing int→float
    "vfncvt.f.x.w", "vfncvt.f.xu.w",
    # Widening with wide first operand (.wv/.wf)
    "vfwadd.wv", "vfwadd.wf", "vfwsub.wv", "vfwsub.wf",
}

# Widening .vv/.vf where NX is structurally uncoverable: both operands are sew-width,
# result at 2*sew always has enough precision for exact arithmetic.
# These should use cp_custom_vfp_flags_nv (NV-only) template.
WIDENING_NX_IMPOSSIBLE = {
    "vfwadd.vv", "vfwadd.vf", "vfwsub.vv", "vfwsub.vf",
    "vfwmul.vv", "vfwmul.vf",
}

# Per-instruction NX trigger overrides.
# The default NX trigger (1+ulp) works for arithmetic instructions but may
# hit lookup-table entries that happen to be exact for approximation/sqrt
# instructions. These alternatives are known to produce inexact results:
#   vfrsqrt7.v/vfrec7.v:  3.0 — lookup table result for 1/√3 or 1/3 is inexact
#   vfsqrt.v:             2.0 — √2 is irrational, always inexact
NX_TRIGGERS_OVERRIDE = {
    "vfrsqrt7.v": {16: 0x4200, 32: 0x40400000, 64: 0x4008000000000000},  # 3.0
    "vfrec7.v":   {16: 0x4200, 32: 0x40400000, 64: 0x4008000000000000},  # 3.0
    "vfsqrt.v":   {16: 0x4000, 32: 0x40000000, 64: 0x4000000000000000},  # 2.0
    # Narrowing int→float: value is an INTEGER at 2*sew width, keyed by dest sew.
    # Must exceed destination mantissa precision to trigger NX.
    # float16 mantissa=10 bits → int > 2^11;  float32 mantissa=23 bits → int > 2^24
    "vfncvt.f.x.w":  {16: 0x00000801, 32: 0x0000000001000001},  # 2049, 2^24+1
    "vfncvt.f.xu.w": {16: 0x00000801, 32: 0x0000000001000001},  # 2049, 2^24+1
}

# FP values that trigger each flag type per SEW
FLAG_TRIGGERS = {
    16: {
        "NV": 0x7D01,      # sNaN → Invalid for most ops
        "DZ": 0x0000,      # +0.0 → Divide by zero for divisor
        "OF": 0x7BFF,      # max normal → overflow for vfadd with same
        "UF": 0x0080,      # very small normal → underflow for vfmul
        "NX": 0x3C01,      # 1.0 + ulp → inexact
        "NX2": 0x3C02,     # 1.0 + 2*ulp — alternate trigger for NX1 (still inexact for cvt)
        "ONE": 0x3C00,     # 1.0 (non-zero, non-sNaN for DZ dividend)
    },
    32: {
        "NV": 0x7F800001,  # sNaN
        "DZ": 0x00000000,  # +0.0
        "OF": 0x7F7FFFFF,  # max normal
        "UF": 0x00800001,  # small normal → underflow for mul
        "NX": 0x3F800001,  # 1.0 + ulp
        "NX2": 0x3F800002, # 1.0 + 2*ulp — alternate trigger for NX1 (still inexact for cvt)
        "ONE": 0x3F800000, # 1.0
    },
    64: {
        "NV": 0x7FF0000000000001,  # sNaN
        "DZ": 0x0000000000000000,  # +0.0
        "OF": 0x7FEFFFFFFFFFFFFF,  # max normal
        "UF": 0x0010000000000001,  # small normal
        "NX": 0x3FF0000000000001,  # 1.0 + ulp
        "NX2": 0x3FF0000000000002, # 1.0 + 2*ulp — alternate trigger for NX1
        "ONE": 0x3FF0000000000000, # 1.0
    },
}


def _gen_test(test, sew, label_name, value, description, **extra_kwargs):
    """Generate a single flag-triggering test case."""
    # Wide-source instructions read vs2 at 2*sew; data must match source width
    esize = sew * 2 if test in WIDE_SOURCE_INSTRUCTIONS else sew
    registerCustomData(label_name, [value], element_size=esize)
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
    # fsflagsi clears fflags before each test, so SAMPLE_AFTER[i] reflects only
    # what test i produced. Transition bins compare consecutive SAMPLE_AFTER values.
    # The FIRST sample has no predecessor so creates no transition.
    #
    # To get FLAG (0→1): need a test that does NOT set FLAG right before one that does.
    # To get FLAG1 (1→1): need two consecutive tests that both set FLAG.
    #
    # Order: [CLEAN, NV, NV, NX, NX, DZ, DZ, OF, OF, UF, UF]
    # - CLEAN produces fflags=0 (no flags). Wastes the "no predecessor" slot.
    # - CLEAN→NV: NV (0→1) ✓
    # - NV→NV: NV1 (1→1) ✓
    # - NV→NX: NX (0→1) ✓ (NV test doesn't set NX bit)
    # - NX→NX: NX1 (1→1) ✓
    # - NX→DZ: DZ (0→1) ✓ etc.

    # Test 0: clean spacer — produces fflags=0 so first real flag gets (0→1)
    # Wide-source instructions need triggers at 2*sew width.
    # - Narrowing int→float: integer 1 at 2*sew (exact conversion, no flags)
    # - Narrowing/widening float: FP 1.0 at 2*sew (normal value, no flags)
    if test in WIDE_SOURCE_INSTRUCTIONS:
        wide_sew = sew * 2
        wide_triggers = FLAG_TRIGGERS.get(wide_sew, {})
        if test in NARROWING_INT_TO_FLOAT:
            spacer_one = 1  # integer 1 → exact float conversion
        else:
            spacer_one = wide_triggers.get("ONE", triggers["ONE"])
        spacer_label = f"custom_flag_wide_one_sew{sew}"
    else:
        spacer_one = triggers["ONE"]
        spacer_label = f"custom_flag_one_sew{sew}"
    _gen_test(test, sew,
              spacer_label, spacer_one,
              f"cp_custom_vfp_flags_set (clean spacer, {test})")

    # Tests 1-2: NV (sNaN input) — CLEAN→NV gives NV (0→1), NV→NV gives NV1
    if "NV" in triggers:
        # Wide-source: sNaN must be at 2*sew width (except int→float: NV impossible)
        if test in WIDE_SOURCE_INSTRUCTIONS and test not in NARROWING_INT_TO_FLOAT:
            nv_val = FLAG_TRIGGERS.get(sew * 2, {}).get("NV", triggers["NV"])
            nv_label = f"custom_flag_wide_nv_sew{sew}"
        else:
            nv_val = triggers["NV"]
            nv_label = f"custom_flag_nv_sew{sew}"
        _gen_test(test, sew,
                  nv_label, nv_val,
                  f"cp_custom_vfp_flags_set (NV via sNaN, {test})")
        _gen_test(test, sew,
                  nv_label, nv_val,
                  f"cp_custom_vfp_flags_set (NV1 via sNaN again, {test})")

    # Tests 3-4: NX (inexact) — after NV so transition NV→NX gives NX (0→1)
    if "NX" in triggers:
        # Wide-source: NX trigger must be at 2*sew width.
        # NX_TRIGGERS_OVERRIDE has correct values for narrowing int→float.
        # For other wide-source: use 1+ulp at 2*sew (inexact when narrowed/rounded).
        if test in NX_TRIGGERS_OVERRIDE:
            nx_val = NX_TRIGGERS_OVERRIDE[test].get(sew, triggers["NX"])
        elif test in WIDE_SOURCE_INSTRUCTIONS:
            wide_triggers = FLAG_TRIGGERS.get(sew * 2, {})
            nx_val = wide_triggers.get("NX", triggers["NX"])
        else:
            nx_val = triggers["NX"]
        # Some .vv instructions need both operands controlled for reliable NX.
        three = {16: 0x4200, 32: 0x40400000, 64: 0x4008000000000000}
        if test == "vfsub.vv":
            # max_normal - 1.0 is always inexact (result doesn't fit mantissa)
            _gen_test_two_operands(test, sew,
                                  f"custom_flag_of_sew{sew}", triggers["OF"],  # max_normal
                                  f"custom_flag_one_sew{sew}", triggers["ONE"],
                                  f"cp_custom_vfp_flags_set (NX via max-1, {test})")
            _gen_test_two_operands(test, sew,
                                  f"custom_flag_of_sew{sew}", triggers["OF"],
                                  f"custom_flag_three_sew{sew}", three[sew],
                                  f"cp_custom_vfp_flags_set (NX1 via max-3, {test})")
        elif test == "vfdiv.vv":
            _gen_test_two_operands(test, sew,
                                  f"custom_flag_one_sew{sew}", triggers["ONE"],
                                  f"custom_flag_three_sew{sew}", three[sew],
                                  f"cp_custom_vfp_flags_set (NX via 1/3, {test})")
            _gen_test_two_operands(test, sew,
                                  f"custom_flag_one_sew{sew}", triggers["ONE"],
                                  f"custom_flag_three_sew{sew}", three[sew],
                                  f"cp_custom_vfp_flags_set (NX1 via 1/3 again, {test})")
        elif test == "vfrdiv.vf":
            _gen_test(test, sew,
                      f"custom_flag_three_sew{sew}", three[sew],
                      f"cp_custom_vfp_flags_set (NX via x/3, {test})")
            _gen_test(test, sew,
                      f"custom_flag_three_sew{sew}", three[sew],
                      f"cp_custom_vfp_flags_set (NX1 via x/3 again, {test})")
        else:
            # Wide-source uses values at 2*sew — needs unique label to avoid clashes
            if test in NARROWING_INT_TO_FLOAT:
                nx_label = f"custom_flag_int_nx_sew{sew}"
            elif test in WIDE_SOURCE_INSTRUCTIONS:
                nx_label = f"custom_flag_wide_nx_sew{sew}"
            else:
                nx_label = f"custom_flag_nx_sew{sew}"
            _gen_test(test, sew,
                      nx_label, nx_val,
                      f"cp_custom_vfp_flags_set (NX via inexact, {test})")
            # Second NX test uses a different trigger to avoid deterministic
            # random operands that may make the first trigger exact.
            if test in NARROWING_INT_TO_FLOAT:
                nx2_val = nx_val + 2  # slightly different integer
                nx2_label = f"custom_flag_int_nx2_sew{sew}"
            elif test in WIDE_SOURCE_INSTRUCTIONS:
                nx2_val = FLAG_TRIGGERS.get(sew * 2, {}).get("NX2", nx_val)
                nx2_label = f"custom_flag_wide_nx2_sew{sew}"
            else:
                nx2_val = triggers.get("NX2", nx_val)
                nx2_label = f"custom_flag_nx2_sew{sew}"
            _gen_test(test, sew,
                      nx2_label, nx2_val,
                      f"cp_custom_vfp_flags_set (NX1 via inexact again, {test})")

    # Tests 5-6: DZ — two consecutive to cover DZ and DZ1 (div/rsqrt only)
    if test in DZ_INSTRUCTIONS and "DZ" in triggers:
        if test in {"vfrsqrt7.v", "vfrec7.v"}:
            # vfrsqrt7(0) = +Inf (DZ), vfrec7(0) = +Inf (DZ) — both use vs2 as input
            _gen_test(test, sew,
                      f"custom_flag_dz_sew{sew}", triggers["DZ"],
                      f"cp_custom_vfp_flags_set (DZ via zero, {test})")
            _gen_test(test, sew,
                      f"custom_flag_dz_sew{sew}", triggers["DZ"],
                      f"cp_custom_vfp_flags_set (DZ1 via zero again, {test})")
        elif test == "vfdiv.vv":
            # vfdiv.vv vd, vs2, vs1: divisor is vs1, dividend is vs2
            # Need vs1=0 (zero divisor) and vs2=non-zero (non-zero dividend)
            _gen_test_two_operands(test, sew,
                                  f"custom_flag_one_sew{sew}", triggers["ONE"],
                                  f"custom_flag_dz_sew{sew}", triggers["DZ"],
                                  f"cp_custom_vfp_flags_set (DZ via zero divisor, {test})")
            _gen_test_two_operands(test, sew,
                                  f"custom_flag_one_sew{sew}", triggers["ONE"],
                                  f"custom_flag_dz_sew{sew}", triggers["DZ"],
                                  f"cp_custom_vfp_flags_set (DZ1 via zero divisor again, {test})")
        elif test in {"vfdiv.vf", "vfrdiv.vf"}:
            # For vfrdiv.vf: vd = f[rs1] / vs2 — need vs2=0
            if test == "vfrdiv.vf":
                _gen_test(test, sew,
                          f"custom_flag_dz_sew{sew}", triggers["DZ"],
                          f"cp_custom_vfp_flags_set (DZ via zero vs2, {test})")
                _gen_test(test, sew,
                          f"custom_flag_dz_sew{sew}", triggers["DZ"],
                          f"cp_custom_vfp_flags_set (DZ1 via zero vs2 again, {test})")

    # Tests 7-8: OF — two consecutive to cover OF and OF1
    if test in OF_INSTRUCTIONS and "OF" in triggers:
        if test.endswith(".vv"):
            _gen_test_two_operands(test, sew,
                                  f"custom_flag_of_sew{sew}", triggers["OF"],
                                  f"custom_flag_of2_sew{sew}", triggers["OF"],
                                  f"cp_custom_vfp_flags_set (OF via max+max, {test})")
            _gen_test_two_operands(test, sew,
                                  f"custom_flag_of_sew{sew}", triggers["OF"],
                                  f"custom_flag_of2_sew{sew}", triggers["OF"],
                                  f"cp_custom_vfp_flags_set (OF1 via max+max again, {test})")
        else:
            _gen_test(test, sew,
                      f"custom_flag_of_sew{sew}", triggers["OF"],
                      f"cp_custom_vfp_flags_set (OF via max normal, {test})")
            _gen_test(test, sew,
                      f"custom_flag_of_sew{sew}", triggers["OF"],
                      f"cp_custom_vfp_flags_set (OF1 via max normal again, {test})")

    # Tests 9-10: UF — two consecutive to cover UF and UF1
    if test in UF_INSTRUCTIONS and "UF" in triggers:
        if test.endswith(".vv"):
            _gen_test_two_operands(test, sew,
                                  f"custom_flag_uf_sew{sew}", triggers["UF"],
                                  f"custom_flag_uf2_sew{sew}", triggers["UF"],
                                  f"cp_custom_vfp_flags_set (UF via tiny*tiny, {test})")
            _gen_test_two_operands(test, sew,
                                  f"custom_flag_uf_sew{sew}", triggers["UF"],
                                  f"custom_flag_uf2_sew{sew}", triggers["UF"],
                                  f"cp_custom_vfp_flags_set (UF1 via tiny*tiny again, {test})")
        else:
            _gen_test(test, sew,
                      f"custom_flag_uf_sew{sew}", triggers["UF"],
                      f"cp_custom_vfp_flags_set (UF via tiny, {test})")
            _gen_test(test, sew,
                      f"custom_flag_uf_sew{sew}", triggers["UF"],
                      f"cp_custom_vfp_flags_set (UF1 via tiny again, {test})")

    # --- Part 2: cp_custom_vfp_flags_inactive_not_set ---
    # Only for vfrsqrt7.v: vs2=0 raises DZ, but element 0 is masked off
    if test == "vfrsqrt7.v":
        # RVVI fsflagsi CSR alias bug: fsflagsi writes CSR 001 but not CSR 003.
        # The inactive_not_set cross checks SAMPLE_BEFORE fcsr.fflags (CSR 003).
        # After flag-setting tests, CSR 003 is stale. Insert a spacer test with
        # a non-flag-setting input (1.0) to make the hardware write CSR 003 = 0.
        spacer_label = f"custom_flag_one_sew{sew}"
        registerCustomData(spacer_label, [triggers["ONE"]], element_size=sew)
        _gen_test(test, sew,
                  spacer_label, triggers["ONE"],
                  f"cp_custom_vfp_flags spacer (clears stale fcsr, {test})")

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


# Register the same function for all split-template variants.
# Each variant uses the same test generation logic; only the coverage
# template (.sv) differs in which flag bins it measures.
for _variant in [
    "cp_custom_vfp_flags_nv",
    "cp_custom_vfp_flags_nv_nx",
    "cp_custom_vfp_flags_nv_dz",
    "cp_custom_vfp_flags_nv_nx_dz",
    "cp_custom_vfp_flags_nv_nx_of",
    "cp_custom_vfp_flags_nv_nx_of_uf",
    "cp_custom_vfp_flags_nx",
]:
    REGISTRY[_variant] = make
