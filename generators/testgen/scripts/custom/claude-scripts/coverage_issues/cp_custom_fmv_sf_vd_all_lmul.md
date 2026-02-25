# cp_custom_fmv_sf_vd_all_lmul — Sail Timeout

## Status
Cannot run coverage — sail simulation times out even at 600s.

## Issue
The cross `std_vec × vd_all_regs × vtype_all_lmul` requires 32 vd × 7 LMUL = 224 test cases.
Each test case generates ~25 lines of assembly plus signature updates.
The resulting 5784-line test file is too large for sail to simulate within 600 seconds.

## Possible Solutions
1. **Increase timeout further** (1200s+) — diminishing returns, makes overall coverage runs very slow
2. **Reduce SIGUPD_COUNT** — currently 50000, reducing to 10000 might speed up sail
3. **Split into multiple test files** — not supported by current framework (one file per instruction per SEW)
4. **Use spike instead of sail** — spike is much faster but may not generate the same trace format
5. **Run the test file through Wally RTL simulation** — the intended use case, not sail reference model
