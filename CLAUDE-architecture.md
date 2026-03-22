# CLAUDE-architecture.md
# Project Architecture & Reference Guide

Read this when you need project overview, directory structure, commands, config formats, or debugging procedures.

## Project Overview

**RISC-V Architectural Certification Tests (ACTs)** — generates self-checking assembly tests that certify RISC-V conformance. The ACT4 Framework uses Makefiles, Python, and config files to generate, compile, and manage tests for a configurable DUT.

Framework generates tests from:
1. **CSV-driven testplans** — instruction coverage and coverpoints
2. **UDB configuration files** — DUT's supported extensions and parameters
3. **DUT-specific macros** (Trickbox) — console output, test termination, interrupt control
4. **Reference model (Sail RISC-V)** — computing expected results

Repository: https://github.com/riscv-non-isa/riscv-arch-test (act4 branch)

## Common Commands

```bash
make --jobs                                                      # Generate and compile all tests
make tests                                                       # Generate only (faster)
make CONFIG_FILES=config/duts/cvw/cvw-rv64gc/test_config.yaml EXTENSIONS=I,M,A
make EXCLUDE_EXTENSIONS=V
make coverage                                                    # Generate coverage metrics
make clean / make clean-tests
make lint / make lint-fix / make format                         # Python quality tools (via uv)

uv run act ...       # Run act framework
uv run testgen ...   # Run test generator
```

## High-Level Architecture

### Core Layers

1. **Configuration** (`config/duts/`, `config/ref/`)
   - `test_config.yaml` — compiler paths, reference model, UDB location
   - `*.yaml` (UDB config) — DUT extensions and parameter values
   - `model_test.h` — Trickbox macros for I/O, interrupts
   - `link.ld` — linker script; `sail.json` — Sail model config

2. **Test Generation** (`generators/`, `testplans/`)
   - `testgen` — generates tests from CSV testplans
   - `coverage` — generates coverpoint definitions and coverage groups
   - `testplans/*.csv` — instruction-to-coverpoint mappings

3. **Framework** (`framework/src/act/`)
   - `act.py` — main entry point
   - `makefile_gen.py` — generates build Makefiles
   - `select_tests.py` — filters tests based on UDB config
   - `fcov/` — functional coverage infrastructure

4. **Output** (`work/`, `work-ref/`)
   - `tests/` — generated .S files; `build/` — .sig.elf, signatures
   - `elfs/` — final self-checking ELFs; `coverage/` — coverage reports

### CSV → ELF Pipeline

1. CSV testplan maps instructions → coverpoints
2. Coverpoint generators create assembly templates
3. `make tests` invokes testgen, creates `.S` files
4. UDB config filters applicable tests
5. Sail model runs tests, computes expected results
6. Final self-checking ELFs embedded with expected values

### Key Design Patterns

- **Configuration-driven**: UDB selects tests; no spurious failures from unsupported features
- **Signature-based**: Sail runs intermediate ELFs → expected signatures embedded in final ELF
- **CSV-to-code mapping**: each (instruction row, coverpoint col) maps to a generator function

## Directory Structure

```
riscv-arch-test/
├── config/duts/cvw/          # CVW-specific configs (rv32gc, rv64gc, rv32imc)
├── config/ref/               # Reference model (Sail) configs
├── generators/
│   ├── testgen/src/testgen/coverpoints/   # Coverpoint generator modules (cp_*.py)
│   ├── coverage/covergroupgen.py
│   └── ctp/                  # CTP document generation
├── framework/src/act/        # ACT4 framework
├── testplans/*.csv           # One per extension
├── tests/rv32i,rv64i,rv32e,rv64e,priv/   # Generated .S files
├── work/<config>/            # build/, elfs/, objdump/, Makefile
└── work-ref/<config>/        # Coverage output
```

## Configuration File Formats

### test_config.yaml
```yaml
name: cvw-rv64gc
compiler_exe: riscv64-unknown-elf-gcc
objdump_exe: riscv64-unknown-elf-objdump
ref_model_exe: sail_riscv_sim
ref_model_type: sail
udb_config: cvw-rv64gc.yaml
linker_script: link.ld
dut_include_dir: .
```

### UDB Config (*.yaml)
```yaml
hart_isa: RV64IMAFDC
extensions:
  - name: I
  - name: M
parameters:
  - name: XLEN
    value: 64
  - name: misaligned_access_support
    value: true
```

### Testplan CSV Format
```csv
Instruction,Type,RV32,RV64,cp_rs1,cp_rs2,cp_rd,cp_rs1_edges,...
add,R,x,x,x,x,x,x,...
addi,I,x,x,x,,x,x,...
auipc,U,x,x,,,x,,20bit,...
```

## Debugging

### Test Failures — Check in Order
1. Configuration mismatch (UDB vs Sail not aligned)
2. `objdump` file to understand what the test does
3. Verify Sail model was configured to match
4. Only then suspect a DUT bug

### UDB / Sail Must Match
Mismatched extensions or parameters → wrong expected results or spurious failures. Not auto-validated.

### Test Output
- Pass: `RVCP-SUMMARY: Test File "<name.S>": PASSED`
- Fail: includes failing PC, instruction, register mismatch (expected vs actual)
- Find instruction: `grep "PC_VALUE" work/<config>/objdump/<test>.elf.objdump`

### Adding a New Instruction
1. Add row to `testplans/<extension>.csv`
2. Add decoding entry to `framework/src/act/fcov/disassemble.svh`
3. Ensure coverpoint generators exist
4. Run `make tests`

## Python Environment
- Tool: `uv`; Location: `.venv/`; Python 3.12+
- Always invoke via `uv` to ensure correct environment

## Contributing
1. Update `CHANGELOG.md` (Semantic Versioning)
2. `make lint` must pass
3. Add SPDX header to new files: `// SPDX-License-Identifier: BSD-3-Clause`
4. Pre-commit hooks: `pre-commit run --all-files`
