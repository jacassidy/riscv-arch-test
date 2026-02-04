# CLAUDE-vector-skill.md

## Vector Coverpoint Understanding Guide

**Purpose**: Help the CSV Editor Agent understand vector coverpoint goals and translate user requirements into precise specifications for Coverpoint Writer and Test Writer.

**When to Use**: Any time the user mentions vector instructions (V extension), or when working with Vx.csv, Vf.csv, or Vls.csv testplans.

---

## The Core Vector Model

Vector instructions operate on **elements** within **vector registers**. The key insight is that everything depends on three state variables:

```
SEW  = Selected Element Width (8, 16, 32, or 64 bits)
LMUL = Length Multiplier (determines register grouping)
VL   = Vector Length (how many elements to process)
```

These are set via `vsetvli`/`vsetivli` before vector operations and stored in CSRs `vtype` and `vl`.

---

## LMUL: Register Grouping

LMUL determines how many physical registers form one logical "vector register group":

| LMUL | Registers per Group | Alignment Rule | Max Groups |
|------|---------------------|----------------|------------|
| mf8  | 1 (1/8 used)        | Any register   | 32 groups  |
| mf4  | 1 (1/4 used)        | Any register   | 32 groups  |
| mf2  | 1 (1/2 used)        | Any register   | 32 groups  |
| m1   | 1                   | Any register   | 32 groups  |
| m2   | 2                   | Even (v0, v2...) | 16 groups |
| m4   | 4                   | Multiple of 4 (v0, v4...) | 8 groups |
| m8   | 8                   | Multiple of 8 (v0, v8...) | 4 groups |

**Coverpoint Goal**: Verify register alignment rules are enforced. A register is "aligned" when its number is divisible by LMUL.

**vlmul CSR encoding**:
- mf8 = 5, mf4 = 6, mf2 = 7, m1 = 0, m2 = 1, m4 = 2, m8 = 3

---

## VLMAX and VL

```
VLMAX = (VLEN * LMUL) / SEW
```

Where VLEN is the implementation's vector register width in bits.

- **vl** can be 0 to VLMAX
- **vl = 0**: No elements processed (but instruction still executes)
- **vl = VLMAX**: All possible elements processed

**Coverpoint Goal**: Test with vl at edge values (0, 1, VLMAX-1, VLMAX) and random legal values.

---

## Element Processing: The Three Regions

For each element index `i`:

```
if (i < vstart)      -> PRESTART: Skip, no exceptions, no writes
if (vstart <= i < vl):
  if (mask[i] == 1)  -> BODY ACTIVE: Execute, may raise exceptions
  if (mask[i] == 0)  -> BODY INACTIVE: Skip (may write 1s if vma=1)
if (vl <= i < VLMAX) -> TAIL: Skip (may write 1s if vta=1)
```

**Critical Case**: When `vstart >= vl`, there are NO body elements. Nothing is written, not even agnostic values.

---

## Agnostic Behavior (vta, vma)

"Agnostic" means the implementation can either:
1. Leave the element unchanged (undisturbed)
2. Write all-1s to the element

It can choose differently per element, per instruction. This supports register renaming.

| vta | vma | Tail Elements | Inactive Elements |
|-----|-----|---------------|-------------------|
| 0   | 0   | undisturbed   | undisturbed       |
| 0   | 1   | undisturbed   | agnostic          |
| 1   | 0   | agnostic      | undisturbed       |
| 1   | 1   | agnostic      | agnostic          |

**Coverpoint Goal**: Cross all combinations of vta/vma with masking enabled/disabled.

---

## Widening and Narrowing

**Widening**: Destination EEW = 2 * SEW, destination EMUL = 2 * LMUL
**Narrowing**: Source EEW = 2 * SEW, source EMUL = 2 * LMUL

Key constraint: EMUL cannot exceed 8, so:
- Widening at LMUL=8 is reserved (would need EMUL=16)
- Narrowing from LMUL=8 is OK (source EMUL=8, dest EMUL=4)

**Coverpoint Goal**: Test with LMUL values that push EMUL to limits (lmul4max = LMUL up to 4).

---

## Register Overlap Rules

Three cases where source and destination can overlap:

1. **Same EEW**: Arbitrary overlap allowed
2. **Narrowing (dest smaller)**: Lowest-numbered register must match
3. **Widening (dest larger)**: Highest-numbered register must match

**Critical**: When source and destination overlap with **different EEW**, the instruction becomes automatically mask-agnostic and tail-agnostic, regardless of vta/vma settings.

**Coverpoint Goal**: Test overlapping cases at each LMUL, ensuring correct register portions are written.

---

## Masking

When `vm=0` (instruction bit 25 = 0), element `i` is active only if `v0[i] = 1`.

Mask edge cases:
- All zeros (nothing active)
- All ones (everything active)
- First VLMAX-1 ones (last element inactive)
- Alternating pattern

**Coverpoint Goal**: Test mask edge patterns with the `cp_masking_edges` coverpoint.

---

## vill: Illegal vtype

When `vill=1` (illegal vtype):
- vl is forced to 0
- All vector instructions that depend on vtype trap (illegal instruction)
- Exceptions: `vsetvli/vsetivli/vsetvl` and whole-register load/store work with vill=1

**Coverpoint Goal**: Verify that operations trap when vill=1 (for privileged tests).

---

## CSV Column Interpretation Guide

### Register Coverpoints

| Column | Meaning | Example Values |
|--------|---------|----------------|
| `cp_vd` | Destination vector register | `x` (all regs), `emul2` (aligned to 2), `nv0` (not v0) |
| `cp_vs1`, `cp_vs2` | Source registers | Same variants as vd |
| `cp_vs3` | Third source (for FMA) | Usually same as vd |
| `cmp_vd_vs1` | Test vd == vs1 | `x` or variant |
| `cmp_vd_vs2` | Test vd == vs2 | `x` or variant |

**Variants**:
- `emul2/emul4/emul8`: Requires alignment for EMUL
- `nv0`: Register cannot be v0 (v0 is mask)
- `lte24-lte30`: vd <= specified value (for segment loads)

### Edge Coverpoints

| Column | Tests |
|--------|-------|
| `cp_vs1_edges`, `cp_vs2_edges` | Element values: zero, one, min, max, all-ones |
| `cr_vs2_vs1_edges` | Cross of vs1 and vs2 edge values |
| `cr_vs2_rs1_edges` | Cross vs2 vector edges with rs1 scalar edges |
| `cp_rs1_edges` | Scalar register edge values |

**Edge Variants**:
- `f`: Floating-point edges (NaN, Inf, subnormal, etc.)
- `f_sew16/32/64`: FP edges for specific SEW
- `wv`, `wx`: Widening variants (different EMUL for sources)

### Vector Length Coverpoints

| Column | Tests |
|--------|-------|
| `cr_vl_lmul` | Cross of vl edges (1, vlmax, random) with all legal LMULs |
| `cp_vl_0` | Test with vl=0 specifically |

**Variants**:
- `e8/e16/e32/e64`: Filter by SEW
- `emul1max/emul2max/emul4max`: Limit LMUL for widening
- `lmul4max`: LMUL limited to 4 (for widening that doubles)

### Agnostic Coverpoints

| Column | Tests |
|--------|-------|
| `cr_vtype_agnostic` | Cross vta/vma with masking |
| `nomask` variant | No masking (vm=1) |

### Custom Coverpoints

| Prefix | Purpose |
|--------|---------|
| `shift_vv`, `shift_vx` | Shift amount extraction (SEW-specific) |
| `wvv`, `wvx` | Widening with vv/vx operands, overlap tests |
| `wwv` | Double-widening (dest 2x source, source already widened) |
| `vext2/4/8` | Extension operations (source narrower) |
| `red`, `wred` | Reductions (scalar dest, vector source) |
| `maskwrite_masked/unmasked` | Mask-producing instructions |

---

## Instruction Categories

### Arithmetic (Vx.csv)

Basic forms:
- `.vv` - vector-vector
- `.vx` - vector-scalar (x register)
- `.vi` - vector-immediate

Widening prefix: `vw` (e.g., `vwadd.vv`)
Narrowing prefix: `vn` (e.g., `vnsrl.wi`)

### Floating-Point (Vf.csv)

Same forms as integer plus:
- `.vf` - vector-scalar (f register)

Special concerns:
- `cp_csr_fflags`: FP exception flags raised
- `cp_csr_frm`: Rounding mode cross
- FP edge cases: NaN, Inf, subnormal, denormal

### Load/Store (Vls.csv)

Types:
- Unit stride: `vle8.v`, `vse8.v`, etc.
- Strided: `vlse8.v`, `vsse8.v`, etc.
- Indexed: `vluxei8.v`, `vloxei8.v`, etc.
- Segment: `vlseg2e8.v`, etc.
- Fault-only-first: `vle8ff.v`

EEW is encoded in instruction (8, 16, 32, 64), not from vtype.

---

## Translating User Requirements

### User says: "Test shift instructions properly handle large shift amounts"

**Interpret as**:
- Shift amount comes from rs1 (scalar) or vs1 (vector)
- Only low lg2(SEW) bits should matter
- Upper bits should be ignored

**Coverpoint goal**: Ensure upper bits of shift amount are all-ones while lower bits vary

**Use**: `cp_custom_shift_vx_sewN` or `cp_custom_shift_vv_sewN`

### User says: "Test widening operations with register overlap"

**Interpret as**:
- Widening: dest EMUL = 2 * source EMUL
- Overlap rule: highest-numbered register must match
- Source fits in upper half of widened destination

**Coverpoint goal**: Cross LMUL values with overlap conditions

**Use**: `cp_custom_wvv` or `cp_custom_wvx`

### User says: "Test reductions properly"

**Interpret as**:
- Reduction: vector -> scalar (element 0 of vd)
- vd can be any register (not constrained by LMUL)
- vs1 is the scalar accumulator (also any register)
- vs2 is the vector source (constrained by LMUL)

**Coverpoint goal**: Test vd off-group (not aligned to LMUL)

**Use**: `cp_custom_red` or `cp_custom_wred`

### User says: "Test with vstart > 0"

**Interpret as**:
- vstart skips initial elements
- Edge: vstart = vl-1 (only last element active)
- Edge: vstart = vl/2 (half elements active)
- Edge: vstart >= vl (no body elements)

**Coverpoint goal**: Test vstart at edge values

**Use**: `cp_vstart` or `cp_vstart_gt_vl`

---

## Quick Decision Matrix

| User Describes | Category | Likely Coverpoints |
|---------------|----------|-------------------|
| Register overlap | Widening/Narrowing | `cp_custom_wvv`, `cmp_vd_vs*` |
| Shift amounts | Integer arithmetic | `cp_custom_shift_*_sew*` |
| Edge values | All | `cp_vs*_edges`, `cr_vs2_vs1_edges` |
| Masking behavior | All | `cr_vtype_agnostic`, `cp_masking_edges` |
| LMUL/SEW combinations | Configuration | `cr_vl_lmul` |
| Scalar operations | Reductions/moves | `cp_custom_red`, vd/vs1 any register |
| FP exceptions | Floating-point | `cp_csr_fflags`, `cp_csr_frm` |
| Memory alignment | Load/store | `cp_rs2_edges` for stride |

---

## Related Files
REFERENCE STRICTLY WHEN NECESSARY
- [Vector Reference Lookup](./CLAUDE-vector-reference.md) - Detailed tables and encodings
- [Coverpoint Writer](./CLAUDE-coverpoint-writer.md) - Template syntax
- [Coverpoint Reference](./CLAUDE-coverpoint-reference.md) - `ins` object API
