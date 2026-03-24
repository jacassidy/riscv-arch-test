# Coverage Work Status

## Current State (2026-03-24)

### Active Work: VfCustom — cp_custom_vfp_flags_nv
- **Isolated column:** `cp_custom_vfp_flags_nv` in `testplans/VfCustom.csv`
- **Makefile EXTENSIONS:** `VfCustom16,VfCustom32,VfCustom64,VlsCustom8,VlsCustom16,VlsCustom32,VlsCustom64`
- **Coverage result:** 100% (62 covergroups, both rv32 and rv64)
- **Status:** PASS — ready to mark complete and move to next coverpoint

### Recent Fix
- **Bug:** `vector_testgen_common.py` line ~1488 set `storeop = "sd"` for SEW=64 even on RV32, where `sd` isn't available.
- **Fix:** Added `storeop = "sw"` override inside the `precision > xlen` branch (line 1492). The code already splits 64-bit values into two 32-bit stores at offsets 0 and 4, it just used the wrong store instruction.
- **File:** `generators/testgen/scripts/vector_testgen_common.py`

## Queue (from progress.json)

### VfCustom (next items)
| Coverpoint | Status |
|---|---|
| cp_custom_vfp_flags | completed (100%) |
| cp_custom_vfp_flags_nv | **just passed** — update progress.json |
| cp_custom_vfp_flags_nv_nx | untested |
| cp_custom_vfp_flags_nv_nx_dz | untested |
| cp_custom_vfp_flags_nv_nx_of | untested |
| cp_custom_vfp_flags_nv_nx_of_uf | untested |
| cp_custom_vfp_flags_nx | untested |
| cp_custom_vfp_flags_nv_dz | untested |

### VlsCustom (blocked/parked items)
| Coverpoint | Status |
|---|---|
| cp_custom_vwholeRegLS_vill | partial (framework bug for EFFEW>8) |
| cp_custom_vwholeRegLS_lmul | completed (100%) |
| cp_custom_maskLS | completed (100%) |
| cp_custom_ls_indexed | untested |
| cp_custom_ffLS_update_vl | untested |
| cp_custom_indexed_emul_data_only | untested |
| cp_custom_masked_v0_operand | untested |

## Workflow Reminder
1. Isolate: `python3 isolate_coverpoint.py VfCustom <coverpoint_name>`
2. Set Makefile EXTENSIONS if needed
3. `make coverage` — verify 100%
4. Update `progress.json`
5. Restore: `python3 isolate_coverpoint.py --restore VfCustom`
6. Isolate next coverpoint
