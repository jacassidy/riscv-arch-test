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
- Always add `if sew > common.xlen: return` guard for FP scripts (SEW=64 on RV32 generates sd/ld which need zilsd)
- `.wf` scalar presets: use SEW-sized values for `fs1_val`, not widened-width (scalar load follows SEW)
- **NEVER manually pick vd/vs2/vs1 with `randint()` for LS instructions** — EMUL = EEW/SEW × LMUL can differ from LMUL, requiring alignment the manual pick won't respect. Let `randomizeVectorInstructionData()` assign registers (it knows EMUL), and use `additional_no_overlap` to enforce constraints like `vd != v0`. E.g. `additional_no_overlap=[['vd', 'v0']]` instead of `vd=randint(1,31)`.
- **Guard against illegal nf × EMUL > 8 for LS instructions** — Per the RISC-V V spec, `nf × EMUL` must not exceed 8 (the operation is illegal otherwise). When `lmul > 1` and the instruction has `EEW ≠ SEW` or `nf > 1`, compute `emul = EEW/SEW × lmul` and do not generate if `emul × nf > 8` (e.g., `vlseg3e64ff.v` with SEW=16, LMUL=2 → EMUL=8, nf=3 → nf×EMUL=24, illegal). See GUIDE.md for the guard pattern.

## Template Rules

- **NEVER check `ins.current.insn == "some_string"`** — `insn` is the raw 32-bit encoding. The framework already routes per-instruction.
- Use `ins.current.vs2_val` (register contents), NOT `ins.current.vs2` (register name string)
- CSR sampling: `get_csr_val(..., "fcsr", "frm")` not `"frm", "frm"` (returns 0)
- CSR sampling: `get_csr_val(..., "fcsr", "fflags")` not `"fflags", "fflags"`
- Narrowing ops: `get_vr_element_zero()` extracts at OUTPUT SEW. Use `ins.current.vs2_val[63:0]` for source.
- `v0_element_1_active` inactive element bins: use `{0}` (inactive = mask bit 0), not `{1}`

## RV32 SEW64 — ifdef Guard for Custom Bins

RV32 cannot execute SEW=64 FP instructions, so VfCustom64 covergroups on RV32 will always show `cp_asm_count` and `std_vec` at 0%. This is expected and counts as 100% coverage. However, custom bins defined in templates **must** be guarded so they don't appear on RV32 SEW64. Use the `` `ifndef COVER_VFCUSTOM64 `` / `` `else `` / `` `ifdef XLEN64 `` pattern:

```systemverilog
`ifndef COVER_VFCUSTOM64
    // bins for SEW16/SEW32 (always included)
    my_coverpoint : coverpoint ... { bins ... }
    cp_custom_foo : cross std_vec, my_coverpoint;
`else
    `ifdef XLEN64
    // same bins, only included for RV64 SEW64
    my_coverpoint : coverpoint ... { bins ... }
    cp_custom_foo : cross std_vec, my_coverpoint;
    `endif
`endif
```

When you see custom bins at 0% in an RV32 VfCustom64 report, wrap them with this pattern. The residual `cp_asm_count`/`std_vec` at 0% on RV32 is acceptable — those are framework-generated and cannot be ifdefed from the template.

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

## vmv.v.i v0 Before vsetvli (Fixed)

`writeTest()` previously emitted `vmv.v.i v0, 0` (mask init for masked instructions like `vfmerge.vfm`) **before** `prepBaseV()` which calls `vsetvli`. After reset, `vtype.vill=1`, so the bare `vmv.v.i` had undefined behavior — sail hung indefinitely. **Fixed** in `vector_testgen_common.py`: bare `vmv.v.i v0, 0` cases (maskval `"zeroes"` and default masked-instruction init) now emit after `prepBaseV`. Mask types with their own `vsetvli` (`"ones"`, `"vlmaxm1_ones"`, etc.) still run before `prepBaseV` so it restores the correct vtype.

## prepMaskV vid.v Alignment (Fixed)

`prepMaskV()` uses `vid.v` + `vmsltu` to build mask patterns in v0. Previously it always used `vid.v v1`, which is illegal when LMUL>=2 (v1 is not aligned to the register group size). **Fixed**: temp vreg is now `int(lmul)` when lmul>=2 (v2 for LMUL=2, v4 for LMUL=4, v8 for LMUL=8), v1 otherwise. Overlap with test operand regs is fine since mask setup runs before operand loads.

## Framework Limitations

- `writeTest(vl=0)` sets VL=0 before vector loads — impossible to pre-load data for VL=0 tests
- VlsCustom: all files ~4300 lines, sail times out even at 600s. Intended for RTL sim only.
- Cross bin saturation: sail handles ~35 tests/file. Scripts optimized for ~85% on large crosses, full coverage deferred to RTL.

## Completed Coverpoint Outcomes

See `knowledge-archive.md` for per-coverpoint notes on completed work.
