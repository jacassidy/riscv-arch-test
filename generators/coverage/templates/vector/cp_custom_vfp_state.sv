    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_state
    //////////////////////////////////////////////////////////////////////////////////

    fd_changed_value : coverpoint (ins.current.fd_val != ins.prev.fd_val) {
        bins target = {1};
    }

    mstatus_vs_active : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins dirty = {3};
    }

    fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags") {
        bins clear = {0};
    }

    cp_custom_vfp_register_state_mstatus_dirty   : cross std_vec, fd_changed_value, mstatus_vs_active;

    //// end cp_custom_vfp_state////////////////////////////////////////////////
