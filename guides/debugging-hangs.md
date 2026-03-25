# Debugging Sail Hangs

**Read this guide when a test hangs during the build/sim phase.**

## Sail Binary & Location

- Binary: `/opt/riscv/bin/sail_riscv_sim`
- Config reference: `config/sail/sail-rv64-max/test_config.yaml` (field `ref_model_exe`)

## Step 1: Find the ELF

Hanging tests show in build output like:

```
oldest: .../work/sail-rv64-max/build/rv64i/VfCustom16/VfCustom16-vfmv.s.f.sig
```

The ELF is at that path with `.elf` appended. The partial log is at that path with `.log` appended.

## Step 2: Run with Instruction Trace and Limit

```bash
timeout 30 /opt/riscv/bin/sail_riscv_sim \
  --inst-limit 50000 \
  --trace-instr \
  --test-signature /dev/null \
  <path-to-elf>
```

- `--inst-limit 50000` prevents infinite loops (raise if needed)
- `--trace-instr` prints every executed instruction with address and disassembly
- `--test-signature /dev/null` is required (sail expects it)
- `timeout 30` as a safety net

The last few lines of output show exactly where the hang occurs. Look for:

- `illegal 0x...` — an illegal instruction causing a trap loop
- A repeating sequence of addresses — an infinite loop in trap handler
- A specific instruction that sail can't complete

## Step 3: Add Register Trace if Needed

```bash
timeout 30 /opt/riscv/bin/sail_riscv_sim \
  --inst-limit 500 \
  --trace-instr --trace-reg \
  --test-signature /dev/null \
  <path-to-elf>
```

- `--trace-reg` shows register reads/writes (very verbose, use smaller inst-limit)
- Useful for checking vtype/vl state: grep for `vtype` or `vl` in output

## Step 4: Cross-reference with Source

Use `objdump` to correlate addresses back to test labels:

```bash
riscv64-unknown-elf-objdump -d <path-to-elf> | grep -A2 -B2 "<address>"
```

The source `.S` file lives at `tests/rv64i/<Extension>/<filename>.S` (not in `work/`).

## Other Useful Sail Flags

| Flag                     | Purpose                                         |
| ------------------------ | ----------------------------------------------- |
| `--trace-mem`            | Trace memory accesses                           |
| `--trace-ptw`            | Trace page table walks                          |
| `--trace-rvfi`           | RVFI trace output                               |
| `--trace-output <file>`  | Write trace to file instead of stdout           |
| `--print-isa-string`     | Print supported ISA string                      |
| `--print-default-config` | Print full default config (includes VLEN, ELEN) |
| `--config <file>`        | Use specific config file                        |

## Common Hang Causes

### 1. Illegal vtype (vill bit set)

If `vsetvli` or `vsetvl` produces `vtype = 0x8000000000000000` (RV64) or `0x80000000` (RV32), the **vill** bit is set. All subsequent vector instructions become illegal, causing a trap loop.

**Diagnosis**: In `--trace-reg` output, look for `CSR vtype <- 0x80000000...`. This means the SEW/LMUL combination is unsupported.

**Common trigger**: Fractional LMUL values (mf8, mf4, mf2) where `VLMAX = VLEN * LMUL / SEW < 1`, or configurations the sail model doesn't support.

**Fix**: Either guard the code with appropriate `#ifdef` checks, or avoid the unsupported SEW/LMUL combination in the test generator.

### 2. No trap handler

The test framework doesn't install trap handlers. Any exception (illegal instruction, misaligned access, etc.) causes an infinite loop at the default trap vector.

### 3. vmv.v.i before vsetvli (historical, fixed)

See knowledge.md entry "vmv.v.i v0 Before vsetvli" — previously caused hangs when vtype.vill=1 after reset.

## Sail Model Configuration

- Default VLEN: 256 bits (`vlen_exp: 8` in config)
- Default ELEN: 64 bits (`elen_exp: 6` in config)
- VLMAX = VLEN \* LMUL / SEW (must be >= 1 for valid vtype)
