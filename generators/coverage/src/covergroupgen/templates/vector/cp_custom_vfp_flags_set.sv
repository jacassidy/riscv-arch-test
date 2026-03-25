    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_flags_set
    // For instructions that can raise NV and DZ (vfrsqrt7.v, vfrec7.v).
    // vfrsqrt7.v: NV (negative/NaN input) and DZ (zero input).
    // vfrec7.v: NV (sNaN input) and DZ (zero input).
    // NX is NOT raised: these are defined 7-bit lookup-table approximations,
    // not IEEE operations, so results are exact by definition.
    // OF and UF are not achievable: result is always in normal range.
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_fflags_vdoun : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags") iff (ins.trap == 0 )  {
        wildcard bins NV   = (5'b0???? => 5'b1????);
        wildcard bins NV1  = (5'b1???? => 5'b1????);
        wildcard bins DZ   = (5'b?0??? => 5'b?1???);
        wildcard bins DZ1  = (5'b?1??? => 5'b?1???);
    }

    cp_custom_vfp_flags_set : cross std_vec, cp_csr_fflags_vdoun;

    //// end cp_custom_vfp_flags_set////////////////////////////////////////////////
