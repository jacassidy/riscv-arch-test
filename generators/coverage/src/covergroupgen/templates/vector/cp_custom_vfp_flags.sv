    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_flags
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_fflags_vdoun : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags") iff (ins.trap == 0 )  {
        // vfrsqrt7.v can raise NV (negative/NaN input) and DZ (zero input).
        // NX is NOT raised: vfrsqrt7 is a defined 7-bit lookup-table approximation,
        // not an IEEE operation, so the result is exact by definition.
        // OF and UF are not achievable: result is always in normal range.
        wildcard bins NV   = (5'b0???? => 5'b1????);
        wildcard bins NV1  = (5'b1???? => 5'b1????);
        wildcard bins DZ   = (5'b?0??? => 5'b?1???);
        wildcard bins DZ1  = (5'b?1??? => 5'b?1???);
    }

    mask_enabled: coverpoint ins.current.insn[25] {
        bins unmasked = {1'b0};
    }

    vfp_flags_fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags") {
        bins clear = {0};
    }

    // Check element 0 of vs2 is zero. We check [15:0] which is the smallest
    // FP SEW (16). For SEW32/64, zero means all bits are 0 including [15:0].
    // For non-zero FP values, [15:0] is always nonzero (exponent/mantissa bits).
    vfsqrt_flag_set : coverpoint (ins.current.vs2_val[15:0] == 0) {
        bins target = {1};
    }

    vl_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        //Any value between max and 1
        bins target = {1};
    }

    v0_element_1_active : coverpoint (ins.current.v0_val[0]) {
        bins target = {0};
    }

    cp_custom_vfp_flags_set : cross std_vec, cp_csr_fflags_vdoun;

    cp_custom_vfp_flags_inactive_not_set : cross std_vec, vl_one, mask_enabled, v0_element_1_active, vfsqrt_flag_set, vfp_flags_fp_flags_clear;

    //// end cp_custom_vfp_flags////////////////////////////////////////////////
