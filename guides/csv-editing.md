# csv-editing.md — CSV Testplan Editing Guide

## Stateless Processing

CSV editor agents are launched fresh per row with NO conversation history. All knowledge must come from .md files.
- If you learn something new, ADD IT to the appropriate guide before finishing.
- The next line will be processed by a completely new Claude instance.

## File Locations

| What | Where |
|------|-------|
| Canonical CSV source | `working-testplans/*.csv` |
| Live CSVs consumed by framework | `testplans/*.csv` |
| CSV editor script | `csv_edit.py` (repo root) |

**NEVER access `testplans/*.csv`** directly — only use `working-testplans/`. The `testplans/` files are managed by isolation/restore scripts.

## csv_edit.py API

```python
python3 csv_edit.py <function> <csv_name> [args...]
```

CSV name can be just the extension name (e.g., `'Vf'`, `'Vx'`, `'VfCustom'`) — auto-resolves to `working-testplans/`.

| Function | Usage | Description |
|----------|-------|-------------|
| `read_structure` | `read_structure(csv_name)` | Print headers + first column only (lightweight context) |
| `set_cells` | `set_cells(csv_name, [(row, col), ...], value="x")` | Set specific cells |
| `fill_column` | `fill_column(csv_name, col_name, row_names=None, value="x")` | Fill a whole column |
| `fill_row` | `fill_row(csv_name, row_name, col_names=None, value="x")` | Fill a whole row |
| `clear_cells` | `clear_cells(csv_name, [(row, col), ...])` | Clear specific cells |

Always call `read_structure()` first to get context before making changes.

## Vector-Specific Translation Guide

### Key Concepts

- **SEW/LMUL/VL**: Set via `vsetvli`, stored in `vtype` and `vl` CSRs.
- **EMUL**: Effective LMUL = (EEW/SEW) * LMUL. Constraint: 1/8 ≤ EMUL ≤ 8.
- **Widening**: dest EMUL = 2*LMUL, so LMUL ≤ 4. Overlap rule: highest-numbered register must match.
- **Narrowing**: source EMUL = 2*LMUL. Overlap rule: lowest-numbered register must match.
- **Masking**: vm=0 (bit 25=0) means v0 is the mask. vd cannot be v0 when masked (except mask-producing instructions).

### Translating User Requirements

| User Describes | Likely Coverpoints |
|---------------|-------------------|
| Register overlap | `cp_custom_wvv`, `cmp_vd_vs*` |
| Shift amounts | `cp_custom_shift_*_sew*` |
| Edge values | `cp_vs*_edges`, `cr_vs2_vs1_edges` |
| Masking behavior | `cr_vtype_agnostic`, `cp_masking_edges` |
| LMUL/SEW combinations | `cr_vl_lmul` |
| Reductions | `cp_custom_red`, `cp_custom_wred` |
| FP exceptions | `cp_csr_fflags`, `cp_csr_frm` |

### CSV Column Quick Reference

| Column | Meaning |
|--------|---------|
| `cp_vd`, `cp_vs1`, `cp_vs2` | Register coverpoints (variants: `emul2`, `nv0`, `lte24`) |
| `cp_vs*_edges` | Element edge values (zero, one, min, max) |
| `cr_vl_lmul` | Cross vl edges with legal LMULs |
| `cr_vtype_agnostic` | Cross vta/vma with masking |

### Feature Description Rules

Write feature descriptions as **test procedures** (what to set up and execute), not spec restatements.

**Good**: "Set SEW=8, LMUL=1 and execute an indexed vector load/store with 64-bit index EEW (index EMUL=8), with vstart=0 and vl != 0"

**Bad**: "For indexed vector load/store instructions, the data vector register group has EEW=SEW and EMUL=LMUL..."

Note: Only explicitly mention vstart=0 and vl!=0 when the test *changes* a standard condition. Normal std_vec conditions (vill=0, vstart=0, vl!=0) don't need to be spelled out each time.

## Knowledge Persistence

When you discover something new, add it to the appropriate file:

| Discovery Type | Add To |
|---------------|--------|
| New coverpoint pattern or SV syntax | `generators/coverage/templates/GUIDE.md` |
| New encoding / bit field value | `guides/vector-reference.md` |
| New script pitfall or API detail | `generators/testgen/scripts/custom/GUIDE.md` |
| New workflow step or tool | `generators/testgen/scripts/custom/COVERAGE-WORKFLOW.md` |
| Custom coverpoint outcome/bug | `generators/testgen/scripts/custom/claude-scripts/knowledge.md` |
