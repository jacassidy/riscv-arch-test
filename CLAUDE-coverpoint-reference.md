# CLAUDE-coverpoint-reference.md

## Coverpoint Writer Reference - Lookup Material

This file contains reference material for writing coverpoints. Consult when you need to look up specific `ins` object fields, helper functions, or advanced patterns.

---

## The `ins` Object

The `ins` object provides access to instruction state during coverage sampling.

### Direct Fields

| Field | Type | Description |
|-------|------|-------------|
| `ins.trap` | bit | 1 if instruction trapped, 0 otherwise |
| `ins.hart` | int | Hart ID (for multi-core) |
| `ins.issue` | int | Issue number |
| `ins.ins_str` | string | Instruction mnemonic (e.g., "add") |

---

## `ins.current` Fields

Post-instruction state (after execution).

### Instruction Bits

- `ins.current.insn[31:0]` - raw instruction bits

**Common bit ranges**:
| Bits | Field | Description |
|------|-------|-------------|
| `[6:0]` | opcode | Instruction opcode |
| `[11:7]` | rd | Destination register |
| `[14:12]` | funct3 | Function code 3 |
| `[19:15]` | rs1 | Source register 1 |
| `[24:20]` | rs2/vs2 | Source register 2 |
| `[25]` | vm | Vector mask (0=masked, 1=unmasked) |
| `[26:25]` | aq/rl | Acquire/release for atomics |
| `[31:25]` | funct7 | Function code 7 |

### Register Values

**Integer (GPR)**:
- `ins.current.rd_val` - destination value after instruction
- `ins.current.rd_val_pre` - destination value before instruction
- `ins.current.rs1_val` - source 1 value before instruction
- `ins.current.rs2_val` - source 2 value before instruction
- `ins.current.rs3_val` - source 3 value before instruction

**Floating-Point (FPR)**:
- `ins.current.fd_val`, `ins.current.fd_val_pre`
- `ins.current.fs1_val`, `ins.current.fs2_val`, `ins.current.fs3_val`

**Vector (VR)**:
- `ins.current.vd_val`, `ins.current.vd_val_pre`
- `ins.current.vs1_val`, `ins.current.vs2_val`, `ins.current.vs3_val`
- `ins.current.v0_val` - mask register value

### Operand Names (strings)

- `ins.current.rd`, `ins.current.rs1`, `ins.current.rs2`, `ins.current.rs3`
- `ins.current.fd`, `ins.current.fs1`, `ins.current.fs2`, `ins.current.fs3`
- `ins.current.vd`, `ins.current.vs1`, `ins.current.vs2`, `ins.current.vs3`

### Operand Presence Flags

- `ins.current.has_rd`, `ins.current.has_rs1`, `ins.current.has_rs2`, `ins.current.has_rs3`
- `ins.current.has_fd`, `ins.current.has_fs1`, `ins.current.has_fs2`, `ins.current.has_fs3`
- `ins.current.has_vd`, `ins.current.has_vs1`, `ins.current.has_vs2`, `ins.current.has_vs3`
- `ins.current.has_v0` - mask register presence

### Vector State

- `ins.current.vm` - mask enabled (1=unmasked, 0=masked)
- `ins.current.eSEW` - element width (0=e8, 1=e16, 2=e32, 3=e64)
- `ins.current.mLMUL` - LMUL (5=mf8, 6=mf4, 7=mf2, 0=m1, 1=m2, 2=m4, 3=m8)
- `ins.current.ta` - tail agnostic (1=agnostic, 0=undisturbed)
- `ins.current.ma` - mask agnostic (1=agnostic, 0=undisturbed)

### Other Fields

- `ins.current.imm` - immediate value
- `ins.current.mem_addr` - calculated memory address (rs1_val + imm)
- `ins.current.pc_rdata` - PC of this instruction
- `ins.current.pc_wdata` - PC of next instruction
- `ins.current.mode` - privilege mode (0=User, 1=Supervisor, 3=Machine)
- `ins.current.valid` - instruction retired (not trapped)
- `ins.current.trap` - same as `ins.trap`

---

## `ins.prev` Fields

Pre-instruction state (before execution). Same structure as `ins.current`.

Use when you need source values or previous state:
- `ins.prev.x_wdata[idx]` - GPR values before instruction
- `ins.prev.f_wdata[idx]` - FPR values before instruction

---

## Methods on `ins`

### Register Lookups

```systemverilog
// Get register enum from name
ins.get_gpr_reg(ins.current.rd)   // returns gpr_name_t (x0, x1, ... x31)
ins.get_fpr_reg(ins.current.fs1)  // returns fpr_name_t (f0, f1, ... f31)
ins.get_vr_reg(ins.current.vs1)   // returns vr_name_t (v0, v1, ... v31)

// Compressed registers (x8-x15 only)
ins.get_gpr_c_reg(string_key)     // returns gpr_reduced_name_t
ins.get_fpr_c_reg(string_key)     // returns fpr_reduced_name_t

// Get register value
ins.get_gpr_val(ins.hart, ins.issue, "x1", `SAMPLE_BEFORE)  // signed XLEN value
ins.get_fpr_val(ins.hart, ins.issue, "f1", `SAMPLE_BEFORE)  // signed FLEN value
ins.get_vr_val(ins.hart, ins.issue, "v1", `SAMPLE_BEFORE)   // signed VLEN value
```

### Immediate Parsing

```systemverilog
ins.get_imm(string)  // parse immediate string to int (handles hex, decimal, negative)
```

### Program Counter

```systemverilog
ins.get_pc()  // returns current instruction PC (same as ins.current.pc_rdata)
```

---

## Global Helper Functions

### CSR Access

```systemverilog
get_csr_val(ins.hart, ins.issue, prev_flag, csr_name, field_name)
```

**Parameters**:
- `prev_flag`: `` `SAMPLE_BEFORE `` (1) or `` `SAMPLE_AFTER `` (0)
- `csr_name`: "vtype", "vl", "vstart", "fcsr", "mstatus", etc.
- `field_name`: sub-field or "" for full value

**Common CSR accesses**:
```systemverilog
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill")   // vill bit
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")  // LMUL field
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")   // SEW field
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")        // vector length
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") // vstart
get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags")   // FP flags after
```

### Register Number Conversion

```systemverilog
get_gpr_num("x1")   // returns 1
get_gpr_num("ra")   // returns 1 (ABI name)
get_fpr_num("f1")   // returns 1
get_vr_num("v1")    // returns 1

get_gpr_name(1)     // returns "x1" or "ra" (depends on ABI_REG_NAMES)
get_fpr_name(1)     // returns "f1"
get_vr_name(1)      // returns "v1"
get_c_gpr_name(0)   // returns "x8" (compressed register)
get_c_fpr_name(0)   // returns "f8"
```

### Vector Helpers

```systemverilog
// Get element 0 based on current SEW
get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)

// Calculate VLMAX
get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)

// Check vector element edge cases
vs_edges_check(ins.hart, ins.issue, val, sew_multiplier)
// Returns: vs_zero, vs_one, vs_min, vs_max, vs_ones, vs_random

// Check mask edge cases
mask_edges_check(ins.hart, ins.issue, mask_val)
```

### Floating-Point Rounding Mode

```systemverilog
get_frm("rne")        // returns frm_name_t enum
get_frm_string(3'b000) // returns "rne"
```

### Vector Type Conversion

```systemverilog
get_vtype_eSEW_val("e8")    // returns 3'b000
get_vtype_eSEW_val("e16")   // returns 3'b001
get_vtype_eSEW_val("e32")   // returns 3'b010
get_vtype_eSEW_val("e64")   // returns 3'b011

get_vtype_mLMUL_val("mf8")  // returns 3'b101
get_vtype_mLMUL_val("mf4")  // returns 3'b110
get_vtype_mLMUL_val("mf2")  // returns 3'b111
get_vtype_mLMUL_val("m1")   // returns 3'b000
get_vtype_mLMUL_val("m2")   // returns 3'b001
get_vtype_mLMUL_val("m4")   // returns 3'b010
get_vtype_mLMUL_val("m8")   // returns 3'b011

get_vtype_ta_val("ta")      // returns 1'b1
get_vtype_ta_val("tu")      // returns 1'b0
get_vtype_ma_val("ma")      // returns 1'b1
get_vtype_ma_val("mu")      // returns 1'b0

get_vm("v0.t")              // returns 1'b0 (masked)
get_vm("")                  // returns 1'b1 (unmasked)
```

---

## Sampling Constants

```systemverilog
`SAMPLE_BEFORE  // (1) - state before instruction
`SAMPLE_AFTER   // (0) - state after instruction
`SAMPLE_CURRENT // (0) - alias for SAMPLE_AFTER
```

---

## XLEN/SEW Conditionals

```systemverilog
`ifdef XLEN32
    bins val32 = {32'hFFFFFFFF};
`endif

`ifdef XLEN64
    bins val64 = {64'hFFFFFFFFFFFFFFFF};
`endif

`ifdef SEW8_SUPPORTED
    // SEW=8 specific code
`endif

`ifdef SEW16_SUPPORTED
    // SEW=16 specific code
`endif

`ifdef SEW32_SUPPORTED
    // SEW=32 specific code
`endif

`ifdef SEW64_SUPPORTED
    // SEW=64 specific code
`endif
```

---

## LMUL Encoding Reference

| LMUL | vlmul field value |
|------|-------------------|
| mf8 | 5 (3'b101) |
| mf4 | 6 (3'b110) |
| mf2 | 7 (3'b111) |
| m1 | 0 (3'b000) |
| m2 | 1 (3'b001) |
| m4 | 2 (3'b010) |
| m8 | 3 (3'b011) |

---

## SEW Encoding Reference

| SEW | vsew field value |
|-----|------------------|
| e8 | 0 (3'b000) |
| e16 | 1 (3'b001) |
| e32 | 2 (3'b010) |
| e64 | 3 (3'b011) |

---

## Register Alignment Patterns

For LMUL-based register alignment checks:

```systemverilog
// Divisible by 2 (LMUL=2)
wildcard bins divisible_by_2 = {5'b????0};

// Divisible by 4 (LMUL=4)
wildcard bins divisible_by_4 = {5'b???00};

// Divisible by 8 (LMUL=8)
wildcard bins divisible_by_8 = {5'b??000};

// NOT divisible (off-group) - use ignore_bins
wildcard ignore_bins divisible_by_4 = {5'b???00};
```

---

## Common CSR Addresses

| CSR | Address |
|-----|---------|
| cycle | 0xC00 |
| instret | 0xC02 |
| vtype | 0xC21 |
| vl | 0xC20 |
| vstart | 0x008 |
| fcsr | 0x003 |
| fflags | 0x001 |
| frm | 0x002 |
| mstatus | 0x300 |
| sstatus | 0x100 |
