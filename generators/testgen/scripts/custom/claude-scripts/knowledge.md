# Knowledge Base — Active Pitfalls

**Read after you have coverage results, not before.**

## Verification Rule

**Always rerun coverage to verify a fix.** After editing a script or template, rebuild (`make clean && make vector-tests`) and rerun coverage (`make coverage` + `coverage_summary.py`). Do not read generated files, assembly, or framework code to guess whether a fix worked or whether a problem affects other instructions — the coverage report answers both questions faster and with certainty.

## Script Rules

- `@register("cp_custom_...")` must match the **CSV column name**, not the definition name
- Function signature is `make(test, sew)` — `test` is the instruction mnemonic
- VVM unary ops (vfsqrt, vfrsqrt7, vfrec7, vfclass): source data is **vs2**, use `vs2_val_pointer`
- **NEVER use `vs2_val=integer`** — sign-extends from XLEN, truncates on RV32. Always use `vs2_val_pointer=label`
- Wrap `randomizeVectorInstructionData()` in `try/except ValueError: pass` for segmented/whole-register LS instructions (overlap constraints unsolvable at high LMUL/NF)
- Always add `if sew > common.flen: return` guard for FP scripts (V spec Section 3.4 requires SEW ≤ FLEN for FP instructions)
- `.wf` scalar presets: use SEW-sized values for `fs1_val`, not widened-width (scalar load follows SEW)
- **LS register assignment and nf×EMUL guard** — see GUIDE.md "Important: Register Assignment for LS Instructions" and the nf×EMUL guard pattern

## Template Rules

- **Residual 0% bins are fine.** Framework-generated bins not defined in the template will be filled by the full suite. Only custom bins must reach 100% during isolated testing.
- **NEVER check `ins.current.insn == "some_string"`** — `insn` is the raw 32-bit encoding. The framework already routes per-instruction.
- Use `ins.current.vs2_val` (register contents), NOT `ins.current.vs2` (register name string)
- CSR sampling: `get_csr_val(..., "fcsr", "frm")` not `"frm", "frm"` (returns 0)
- CSR sampling: For fflags **after** an FP instruction, `"fcsr", "fflags"` works (FP instructions write both CSR 001 and 003). For fflags **before** an instruction (SAMPLE_BEFORE), use `"fflags", "fflags"` because `fsflagsi` only writes CSR 001, leaving CSR 003 (fcsr) stale.
- Narrowing ops: `get_vr_element_zero()` extracts at OUTPUT SEW. Use `ins.current.vs2_val[63:0]` for source.
- `v0_element_1_active` inactive element bins: use `{0}` (inactive = mask bit 0), not `{1}`

## SEW64 FP — ifdef Guard for Custom Bins

SEW=64 FP instructions require FLEN ≥ 64 (D extension). On systems without D extension, Vf64 covergroups will always show `cp_asm_count` and `std_vec` at 0%. This is expected and counts as 100% coverage. However, custom bins defined in templates **must** be guarded so they don't appear when FLEN < 64. Use the `` `ifndef COVER_VFCUSTOM64 `` / `` `else `` / `` `ifdef FLEN64 `` pattern (note: `COVER_VFCUSTOM*` macros are still defined as aliases in `header_vector.sv`):

```systemverilog
`ifndef COVER_VFCUSTOM64
    // bins for SEW16/SEW32 (always included)
    my_coverpoint : coverpoint ... { bins ... }
    cp_custom_foo : cross std_vec, my_coverpoint;
`else
    `ifdef FLEN64
    // same bins, only included when FLEN >= 64
    my_coverpoint : coverpoint ... { bins ... }
    cp_custom_foo : cross std_vec, my_coverpoint;
    `endif
`endif
```

When you see custom bins at 0% in a Vf64 report on a system without D extension, wrap them with this pattern. The residual `cp_asm_count`/`std_vec` at 0% is acceptable — those are framework-generated and cannot be ifdefed from the template.

## RVVI fsflagsi CSR Alias Bug

`fsflagsi` writes CSR 001 (fflags) but NOT CSR 003 (fcsr). Templates using `get_csr_val("fcsr", "fflags")` see stale values. **Fix**: add spacer tests with non-flag-setting inputs after flag-setting FP instructions to force CSR 003=0.

## Transition Bins (NV1/DZ1/NX1)

Framework clears fflags before each test. To cover "stays set" (`FLAG1`), generate the flag-triggering test **twice in a row** so sample[i] and sample[i+1] both have the flag set.

## NX Triggers for Approximation/Sqrt

Default `1.0+1ulp` may not trigger NX for lookup-table instructions:

- **vfrsqrt7.v / vfrec7.v**: use **3.0** (`{16: 0x4200, 32: 0x40400000, 64: 0x4008000000000000}`)
- **vfsqrt.v**: use **2.0** (`{16: 0x4000, 32: 0x40000000, 64: 0x4000000000000000}`)

## FP Lookup Table Coverage

vfrsqrt7/vfrec7 bin coverage requires both **even and odd exponents** to cover all 128 lookup entries.

## sNaN Actual Values

`vs_corner_f_sNaN_payload1` generates: SEW16=`0x7D01`, SEW32=`0x7F800001`, SEW64=`0x7FF0000000000001`. Verify template bin values match.

## Fixed Issues

See `knowledge-archive.md` for details on these resolved bugs:

- **vmv.v.i v0 Before vsetvli** — mask init now emits after `prepBaseV`
- **prepMaskV vid.v Alignment** — temp vreg now LMUL-aligned

## Framework Limitations

- `writeTest(vl=0)` sets VL=0 before vector loads — impossible to pre-load data for VL=0 tests

## Hang Detection

Sail can run an **indefinite** number of tests. If a build is hanging, it's a test bug (illegal instruction → trap loop), NOT a sail limitation. A single isolated coverpoint should build in <30s. If it takes longer:

1. Kill the build
2. Note the hanging file from `make coverage` output (e.g. `oldest: .../Vf64-vfmv.s.f.sig`)
3. Follow the debugging guide in `guides/debugging-hangs.md` to trace the hang and fix the script

## Completed Coverpoint Outcomes

See `knowledge-archive.md` for per-coverpoint notes on completed work.

## Vls Coverage Status

**VlsCustom has been merged into Vls.** The combined `Vls.csv` testplan covers all LS instructions (310 total) with both custom (`cp_custom_*`) and non-custom coverpoints. Extensions are `Vls8,Vls16,Vls32,Vls64`. When updating `testplans/Vls.csv`, also update `working-testplans/duplicates/Vls-save.csv`.

**Full Vls coverage achieved:** All 94 covergroups at 100% on both RV32 and RV64. No hangs.

### Key Bugs Fixed for Vls

- **SIGUPD_V SEW mismatch (EEW≠SEW)**: `RVTEST_SIGUPD_V` uses `vle##_SEW.v` to load reference, but `vmsne.vv` compares at current vtype's SEW. For LS with EEW≠SEW (e.g., `vlseg5e8ff.v` at SEW=16), only 1 byte loaded but 2 bytes compared → stale-byte mismatch. Fix: always emit `vsetivli x0, 1, e{sig_sew}, m1` before SIGUPD in base tests (not just when lmul≠1).
- **Mask LS reload register**: vsm.v/vlm.v store/load ceil(VL/8) bytes. Stale tail bytes in reload register differ between builds. Fix: zero reload register before reload.
- **Indexed LS vs2 EMUL**: `loadVecReg` always used `m1` for vs2, but indexed LS with EEW≠SEW can have EMUL>1. Fix: use `e{register_sew}, m{max(register_emul,1)}`.
- **Whole register LS vd preload EMUL**: Used `lmul*eew/sew` which gives wrong EMUL for whole register LS. Fix: extract NF from instruction name.
- **Whole register stores vs3 loading**: Cascading `if` chain overwrote `load_unique_vtype=True` with False. Fix: restructured to `elif` chain. Also: used avlReg for VLMAX vsetvli, clobbering saved VL. Fix: use separate vlmaxTempReg.
