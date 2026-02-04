# CLAUDE-vector-skill.md

## Vector Coverpoint Understanding Guide

**Purpose**: Help the CSV Editor Agent translate user requirements into precise specifications for the Coverpoint Writer.

**When to Use**: Working with Vx.csv, Vf.csv, or Vls.csv testplans.

---

## Key Concepts (Brief)

**SEW/LMUL/VL**: Set via `vsetvli`, stored in `vtype` and `vl` CSRs.

**EMUL**: Effective LMUL = (EEW/SEW) * LMUL. Constraint: 1/8 ≤ EMUL ≤ 8.

**Widening**: dest EMUL = 2*LMUL, so LMUL ≤ 4. Overlap rule: highest-numbered register must match.

**Narrowing**: source EMUL = 2*LMUL. Overlap rule: lowest-numbered register must match.

**Masking**: vm=0 (bit 25=0) means v0 is the mask. vd cannot be v0 when masked (except mask-producing instructions).

---

## Translating User Requirements

### "Test widening operations with register overlap"
- Widening: dest EMUL = 2 * source EMUL
- Source fits in upper half of widened destination
- **Use**: `cp_custom_wvv` or `cp_custom_wvx`

### "Test shift instructions handle large shift amounts"
- Only low lg2(SEW) bits matter, upper bits ignored
- **Use**: `cp_custom_shift_vx_sewN` or `cp_custom_shift_vv_sewN`

### "Test reductions properly"
- vd/vs1 can be any register (not LMUL-constrained)
- vs2 is the vector source (LMUL-constrained)
- **Use**: `cp_custom_red` or `cp_custom_wred`

### "Test with vstart > 0"
- vstart skips initial elements
- Edge cases: vstart=vl-1, vstart=vl/2, vstart≥vl
- **Use**: `cp_vstart` or `cp_vstart_gt_vl`

---

## Quick Decision Matrix

| User Describes | Likely Coverpoints |
|---------------|-------------------|
| Register overlap | `cp_custom_wvv`, `cmp_vd_vs*` |
| Shift amounts | `cp_custom_shift_*_sew*` |
| Edge values | `cp_vs*_edges`, `cr_vs2_vs1_edges` |
| Masking behavior | `cr_vtype_agnostic`, `cp_masking_edges` |
| LMUL/SEW combinations | `cr_vl_lmul` |
| Reductions | `cp_custom_red`, `cp_custom_wred` |
| FP exceptions | `cp_csr_fflags`, `cp_csr_frm` |

---

## CSV Column Quick Reference

| Column | Meaning |
|--------|---------|
| `cp_vd`, `cp_vs1`, `cp_vs2` | Register coverpoints (variants: `emul2`, `nv0`, `lte24`) |
| `cp_vs*_edges` | Element edge values (zero, one, min, max) |
| `cr_vl_lmul` | Cross vl edges with legal LMULs |
| `cr_vtype_agnostic` | Cross vta/vma with masking |

---

## Related Files
- [Vector Reference](./CLAUDE-vector-reference.md) - Encodings, bit patterns, formulas
- [Coverpoint Writer](./CLAUDE-coverpoint-writer.md) - Template syntax and common patterns
