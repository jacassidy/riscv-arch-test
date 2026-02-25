# cp_custom_fmv_fs_vs2_all_lmul — Sail Timeout (same as fmv_sf_vd_all_lmul)

## Status
Same issue as cp_custom_fmv_sf_vd_all_lmul. 224 test cases per file, sail times out.
Also missing fractional LMULs (script only has {1,2,4,8}, template needs {mf8,mf4,mf2,1,2,4,8}).
