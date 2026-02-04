# CLAUDE-vector-reference.md

## Vector Extension Technical Reference

Quick-lookup tables for vector coverpoint development. Use this when you need exact encodings, bit positions, or formulas.

---

## CSR Encodings

### vtype Fields

| Field | Bits | Values |
|-------|------|--------|
| vill | XLEN-1 | 0=legal, 1=illegal |
| vma | 7 | 0=undisturbed, 1=agnostic |
| vta | 6 | 0=undisturbed, 1=agnostic |
| vsew | 5:3 | 000=e8, 001=e16, 010=e32, 011=e64 |
| vlmul | 2:0 | See LMUL table below |

### vlmul Encoding

| LMUL | vlmul[2:0] | Decimal | Registers |
|------|------------|---------|-----------|
| mf8  | 101        | 5       | 1 (1/8)   |
| mf4  | 110        | 6       | 1 (1/4)   |
| mf2  | 111        | 7       | 1 (1/2)   |
| m1   | 000        | 0       | 1         |
| m2   | 001        | 1       | 2         |
| m4   | 010        | 2       | 4         |
| m8   | 011        | 3       | 8         |

### vsew Encoding

| SEW | vsew[2:0] | Decimal |
|-----|-----------|---------|
| e8  | 000       | 0       |
| e16 | 001       | 1       |
| e32 | 010       | 2       |
| e64 | 011       | 3       |

---

## Instruction Bit Fields

### Standard Vector Format

```
31    26 25  24   20 19   15 14  12 11    7 6     0
[funct6][vm][  vs2 ][vs1/rs1][funct3][ vd  ][opcode]
```

| Field | Bits | Description |
|-------|------|-------------|
| opcode | 6:0 | Operation code |
| vd/rd | 11:7 | Destination register |
| funct3 | 14:12 | Operation variant |
| vs1/rs1/imm | 19:15 | Source 1 / scalar / immediate |
| vs2 | 24:20 | Source 2 |
| vm | 25 | 0=masked, 1=unmasked |
| funct6 | 31:26 | Function code |

### Access Patterns

```systemverilog
ins.current.insn[11:7]   // vd register number
ins.current.insn[19:15]  // vs1/rs1 register number
ins.current.insn[24:20]  // vs2 register number
ins.current.insn[25]     // vm bit (0=masked)
```

---

## Register Alignment Patterns

### Wildcard Bins for LMUL Alignment

```systemverilog
// LMUL=1: Any register (0-31)
// No alignment needed

// LMUL=2: Even registers (0,2,4,...,30)
wildcard bins divisible_by_2 = {5'b????0};

// LMUL=4: Multiples of 4 (0,4,8,...,28)
wildcard bins divisible_by_4 = {5'b???00};

// LMUL=8: Multiples of 8 (0,8,16,24)
wildcard bins divisible_by_8 = {5'b??000};
```

### Unaligned (Off-Group) Patterns

```systemverilog
// Not divisible by 2
wildcard bins odd = {5'b????1};

// Not divisible by 4 (but could be div by 2)
wildcard ignore_bins divisible_by_4 = {5'b???00};

// Specifically offset from aligned by N
// For LMUL=4, register mod 4 == 2 or 3
wildcard bins mod4_eq_2or3 = {5'b???1?};  // catches 2,3,6,7,...
```

### Segment Load vd Constraints

Segment loads use NFIELDS consecutive register groups. vd must leave room:

| Segments | Constraint | Max vd | Coverpoint |
|----------|-----------|--------|------------|
| 2 | vd + EMUL*2 <= 32 | 30 (EMUL=1) | lte30 |
| 3 | vd + EMUL*3 <= 32 | 29 (EMUL=1) | lte29 |
| 4 | vd + EMUL*4 <= 32 | 28 (EMUL=1) | lte28 |
| 5 | vd + EMUL*5 <= 32 | 27 (EMUL=1) | lte27 |
| 6 | vd + EMUL*6 <= 32 | 26 (EMUL=1) | lte26 |
| 7 | vd + EMUL*7 <= 32 | 25 (EMUL=1) | lte25 |
| 8 | vd + EMUL*8 <= 32 | 24 (EMUL=1) | lte24 |

---

## Formulas

### VLMAX

```
VLMAX = (VLEN * LMUL) / SEW

// In fractional LMUL:
VLMAX = (VLEN * numerator) / (SEW * denominator)
// e.g., mf4: VLMAX = VLEN / (SEW * 4)
```

### EMUL (Effective LMUL)

```
EMUL = (EEW / SEW) * LMUL

// Widening destination:
EMUL_dst = 2 * LMUL  (since EEW_dst = 2 * SEW)

// Narrowing source:
EMUL_src = 2 * LMUL  (since EEW_src = 2 * SEW)

// Extension source:
EMUL_src = LMUL / N  (vzext.vfN, vsext.vfN where N=2,4,8)
```

### Constraint: EMUL Range

```
1/8 <= EMUL <= 8

// Therefore for widening (EMUL=2*LMUL):
LMUL <= 4  (else EMUL > 8)

// For narrowing source (EMUL=2*LMUL):
LMUL <= 4

// For extension source (EMUL=LMUL/N):
LMUL >= N/8  (fractional limit)
```

---

## Element Index Regions

```
Index:    0        vstart       vl        VLMAX
          |           |         |           |
          |--prestart-|--body---|---tail----|

Prestart: i < vstart       -> skip, no exceptions
Body:     vstart <= i < vl -> execute if mask[i]=1
Tail:     vl <= i < VLMAX  -> skip (agnostic if vta=1)
```

### Body Sub-regions

```
Body Active:   body AND mask[i]=1  -> execute, update dest
Body Inactive: body AND mask[i]=0  -> skip (agnostic if vma=1)
```

---

## Overlap Bit Patterns

For detecting register overlap in widening operations:

### LMUL=1 (2-register widened group)

```systemverilog
// vd[4:1] == vs2[4:1] means upper halves of groups match
vs2_vd_overlap_lmul1: coverpoint (ins.current.insn[24:21] == ins.current.insn[11:8]) {
    bins overlapping = {1'b1};
}
```

### LMUL=2 (4-register widened group)

```systemverilog
// vd[4:2] == vs2[4:2] for 4-register group alignment
vs2_vd_overlap_lmul2: coverpoint (ins.current.insn[24:22] == ins.current.insn[11:9]) {
    bins overlapping = {1'b1};
}
```

### LMUL=4 (8-register widened group)

```systemverilog
// vd[4:3] == vs2[4:3] for 8-register group alignment
vs2_vd_overlap_lmul4: coverpoint (ins.current.insn[24:23] == ins.current.insn[11:10]) {
    bins overlapping = {1'b1};
}
```

---

## Standard Conditions Coverpoint

Use this pattern for valid vector operation:

```systemverilog
std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                    ins.trap == 0
                }
{
    bins true = {1'b1};
}
```

---

## CSR Access Patterns

```systemverilog
// Before instruction
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill")
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vta")
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vma")
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart")

// After instruction (for FP flags)
get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags")
```

---

## Shift Amount Extraction

Shift instructions only use low `lg2(SEW)` bits:

| SEW | Bits Used | Mask |
|-----|-----------|------|
| 8   | 2:0       | 0x07 |
| 16  | 3:0       | 0x0F |
| 32  | 4:0       | 0x1F |
| 64  | 5:0       | 0x3F |

### Testing Upper Bits Ignored

For SEW=16, bits 15:4 should be ignored. Test with upper bits all 1s:

```systemverilog
// XLEN=32: rs1 = 0xFFFFFFF? where ? is the actual shift
wildcard bins sew16 = {34'b01_????????_????????_11111111_1111????};

// XLEN=64: similar but 66 bits total ({vsew[1:0], rs1[63:0]})
```

---

## Floating-Point Edge Values

### Half-Precision (16-bit)

| Name | Hex | Description |
|------|-----|-------------|
| pos0 | 0x0000 | +0.0 |
| neg0 | 0x8000 | -0.0 |
| pos1 | 0x3C00 | +1.0 |
| neg1 | 0xBC00 | -1.0 |
| posInf | 0x7C00 | +Infinity |
| negInf | 0xFC00 | -Infinity |
| qNaN | 0x7E00 | Quiet NaN |
| sNaN | 0x7D01 | Signaling NaN |
| maxNorm | 0x7BFF | Largest normalized |
| minNorm | 0x0400 | Smallest normalized |
| maxSubnorm | 0x03FF | Largest subnormal |
| minSubnorm | 0x0001 | Smallest subnormal |

### Single-Precision (32-bit)

| Name | Hex | Description |
|------|-----|-------------|
| pos0 | 0x00000000 | +0.0 |
| neg0 | 0x80000000 | -0.0 |
| pos1 | 0x3F800000 | +1.0 |
| neg1 | 0xBF800000 | -1.0 |
| posInf | 0x7F800000 | +Infinity |
| negInf | 0xFF800000 | -Infinity |
| qNaN | 0x7FC00000 | Quiet NaN |
| sNaN | 0x7F800001 | Signaling NaN |
| maxNorm | 0x7F7FFFFF | Largest normalized |
| minNorm | 0x00800000 | Smallest normalized |
| maxSubnorm | 0x007FFFFF | Largest subnormal |
| minSubnorm | 0x00000001 | Smallest subnormal |

### Double-Precision (64-bit)

| Name | Hex | Description |
|------|-----|-------------|
| pos0 | 0x0000000000000000 | +0.0 |
| neg0 | 0x8000000000000000 | -0.0 |
| pos1 | 0x3FF0000000000000 | +1.0 |
| neg1 | 0xBFF0000000000000 | -1.0 |
| posInf | 0x7FF0000000000000 | +Infinity |
| negInf | 0xFFF0000000000000 | -Infinity |
| qNaN | 0x7FF8000000000000 | Quiet NaN |
| sNaN | 0x7FF0000000000001 | Signaling NaN |
| maxNorm | 0x7FEFFFFFFFFFFFFF | Largest normalized |
| minNorm | 0x0010000000000000 | Smallest normalized |
| maxSubnorm | 0x000FFFFFFFFFFFFF | Largest subnormal |
| minSubnorm | 0x0000000000000001 | Smallest subnormal |

---

## Integer Edge Values

### By SEW

| SEW | Zero | One | Max Signed | Min Signed | Max Unsigned | All Ones |
|-----|------|-----|------------|------------|--------------|----------|
| 8   | 0x00 | 0x01 | 0x7F | 0x80 | 0xFF | 0xFF |
| 16  | 0x0000 | 0x0001 | 0x7FFF | 0x8000 | 0xFFFF | 0xFFFF |
| 32  | 0x00000000 | 0x00000001 | 0x7FFFFFFF | 0x80000000 | 0xFFFFFFFF | 0xFFFFFFFF |
| 64  | 0x0...0 | 0x0...1 | 0x7F...F | 0x80...0 | 0xFF...F | 0xFF...F |

---

## vl Edge Values

| Name | Value | Purpose |
|------|-------|---------|
| vl_one | 1 | Minimum active elements |
| vl_vlmax | VLMAX | Maximum elements |
| vl_legal | random in [2, VLMAX-1] | General coverage |

### vstart Edge Values

| Name | Value | Purpose |
|------|-------|---------|
| vstart_one | 1 | Skip first element |
| vstart_vlmaxm1 | VLMAX-1 | Only last element active |
| vstart_vlmaxd2 | VLMAX/2 | Half elements skipped |
| vstart_legal | random | General coverage |

---

## Mask Edge Values

| Name | Pattern | Purpose |
|------|---------|---------|
| mask_zero | All 0s | No active elements |
| mask_ones | All 1s | All elements active |
| mask_vlmaxm1ones | (VLMAX-1) 1s, then 0 | Last element inactive |
| mask_vlmaxd2p1ones | (VLMAX/2+1) 1s | Just over half active |
| mask_random | Random | General coverage |

---

## Instruction Type Encoding (funct3 for OPIVV/OPIVX/OPIVI)

| funct3 | Type | Source 2 | Source 1 |
|--------|------|----------|----------|
| 000 | OPIVV | vector | vector |
| 001 | OPFVV | vector | vector (FP) |
| 010 | OPMVV | vector | vector (mask/reduction) |
| 011 | OPIVI | vector | immediate |
| 100 | OPIVX | vector | scalar (x reg) |
| 101 | OPFVF | vector | scalar (f reg) |
| 110 | OPMVX | vector | scalar (x reg, mask/reduction) |
| 111 | OPCFG | - | config instructions |

---

## Load/Store EEW

Memory instructions encode EEW directly:

| Instruction | EEW |
|-------------|-----|
| vle8.v, vse8.v | 8 |
| vle16.v, vse16.v | 16 |
| vle32.v, vse32.v | 32 |
| vle64.v, vse64.v | 64 |

EMUL is calculated from EEW:
```
EMUL = (EEW / SEW) * LMUL
```

---

## Indexed Load/Store

Index EEW from instruction, data EEW from SEW:

| Instruction | Index EEW | Data EEW |
|-------------|-----------|----------|
| vluxei8.v | 8 | SEW |
| vluxei16.v | 16 | SEW |
| vluxei32.v | 32 | SEW |
| vluxei64.v | 64 | SEW |

Index EMUL:
```
Index_EMUL = (Index_EEW / SEW) * LMUL
```

---

## Constraint Summary

| Operation | LMUL Constraint | Reason |
|-----------|-----------------|--------|
| Widening | LMUL <= 4 | Dest EMUL = 2*LMUL <= 8 |
| Narrowing | LMUL <= 4 | Source EMUL = 2*LMUL <= 8 |
| vzext.vf8 | LMUL >= 1 | Source EMUL = LMUL/8 >= 1/8 |
| vzext.vf4 | LMUL >= 1/2 | Source EMUL = LMUL/4 >= 1/8 |
| vzext.vf2 | LMUL >= 1/4 | Source EMUL = LMUL/2 >= 1/8 |
| Segment N | EMUL*N <= 8 | Total registers <= 8 groups |
