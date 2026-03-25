# Knowledge Archive — Completed Coverpoint Outcomes

Per-coverpoint notes for completed/blocked work. Reference only — don't read upfront.

| Coverpoint                        | Status       | Key Notes                                                                                                           |
| --------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------- |
| cp_custom_FpRecSqrtEst_edges      | 100%         | Fixed: even+odd exponents                                                                                           |
| cp_custom_FpRecipEst_edges        | 100%         | Worked out of the box                                                                                               |
| cp_custom_vfclass_onehot          | 100%         | —                                                                                                                   |
| cp_custom_vfncvt_rod_overflow     | 100% (SEW32) | Fixed: `get_vr_element_zero()` → `vs2_val[63:0]`                                                                    |
| cp_custom_vfredosum_ordered_sum   | 100%         | —                                                                                                                   |
| cp_custom_FpRecSqrtEst_flag_edges | 100%         | Fixed with spacer tests (RVVI alias bug)                                                                            |
| cp_custom_FpRecipEst_flag_edges   | 100%         | Fixed with spacer tests (RVVI alias bug)                                                                            |
| cp_custom_vfncvt_rup_overflow     | 100% RV64    | Only vfncvt.f.f.w and .rod can set OF at SEW32. Int-to-float/float-to-int can't overflow. Fixed CSR name + comment. |
| cp_custom_vfp_state               | 50%          | 2 crosses at 0%: template checks mstatus.vs==0 (traps), hardcodes wrong insn. See coverage_issues/.                 |
| cp_custom_vfredosum_NAN_vl0       | 55.55%       | Cross 0%. Framework vl=0 limitation + wrong bin values. See coverage_issues/.                                       |
| cp_custom_vfp_flags               | 100%         | Root cause for rv32+SEW64 was sew>xlen skip                                                                         |
| cp_custom_vfp_flags_nv_nx         | 100%         | Fixed: back-to-back NX tests + .wf scalar width correction                                                          |
| cp_custom_fmv_sf_vd_all_lmul      | 85.46%       | Cross needs 128 bins, sail limited to ~35 tests. Full coverage needs RTL.                                           |
| cp_custom_fmv_fs_vs2_all_lmul     | 85.46%       | Same as above                                                                                                       |
| cp_custom_vfp_NaN_input           | In progress  | 101 instructions, ~10 hours total                                                                                   |
| All VlsCustom                     | Blocked      | Sail timeout — intended for RTL sim                                                                                 |
