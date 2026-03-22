    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_flags_nv
    // For instructions that can only raise NV (comparison, min, max).
    // These instructions compare or select operands exactly — no rounding occurs,
    // so NX/DZ/OF/UF are never raised. NV fires when either operand is a sNaN.
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_fflags_vdoun : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags") iff (ins.trap == 0 )  {
        wildcard bins NV   = (5'b0???? => 5'b1????);
        wildcard bins NV1  = (5'b1???? => 5'b1????);
    }

    cp_custom_vfp_flags_set : cross std_vec, cp_csr_fflags_vdoun;

    //// end cp_custom_vfp_flags_nv////////////////////////////////////////////////
