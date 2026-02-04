# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**RISC-V Architectural Certification Tests (ACTs)** is a framework for generating self-checking assembly tests that certify conformance to the RISC-V specification. The ACT4 Framework uses Makefiles, Python, and configuration files to generate, compile, and manage tests for a configurable RISC-V Device Under Test (DUT).

The framework generates tests based on:
1. **CSV-driven testplans** (unprivileged instructions) specifying instruction coverage and coverpoints
2. **Spreadsheet-driven specifications** (privileged operations)
3. **UDB configuration files** describing the DUT's supported extensions and parameters
4. **DUT-specific macros** (Trickbox) for console output, test termination, and interrupt control
5. **Reference model (Sail RISC-V)** for computing expected results

Repository: https://github.com/riscv-non-isa/riscv-arch-test (act4 branch)

## Multi-Agent Workflow

This project uses three specialized Claude agents working together:

### Hub Agent: CSV Editor
**[Full Guide →](./CLAUDE-csv-editor.md)**
- **Role**: Interpret user's natural language test requirements and coordinate specialists
- **Model**: Opus
- **Key Skill**: Understanding what the user wants to test
- **Communication**: Back-and-forth dialogue with specialists
- **Output**: Structured requirements for Coverpoint and Test Writers

### Specialist Agent 1: Coverpoint Writer
**[Full Guide →](./CLAUDE-coverpoint-writer.md)**
- **Role**: Write `.txt` SystemVerilog coverpoint templates in professor's exact format
- **Model**: Opus (training), Haiku (execution)
- **Output**: `.txt` template files with keyword placeholders for Python assembly
- **Constraint**: Very specific formatting requirements - deviations break assembly

### Specialist Agent 2: Test Writer
**[Full Guide →](./CLAUDE-test-writer.md)**
- **Role**: Modify Python test generation code and assembly macros
- **Model**: Opus (training), Haiku (execution)
- **Output**: Modified Python code that generates assembly tests
- **Focus**: Code patterns, assembly macros, test structure

### Workflow

```
User (natural language)
  ↓
CSV Editor (interprets & coordinates)
  ↓
  ├→ Coverpoint Writer (writes .txt templates)
  ├→ Test Writer (modifies Python code)
  ↓
CSV Editor (validates outputs)
  ↓
User (reviews results)
```

## Common Development Tasks

### Building and Running Tests

```bash
# Generate and compile all tests for configured DUTs
make --jobs

# Generate only test files without compilation (faster, only needs make + uv)
make tests

# Generate tests for specific extensions
make CONFIG_FILES=config/duts/cvw/cvw-rv64gc/test_config.yaml EXTENSIONS=I,M,A

# Exclude specific extensions
make EXCLUDE_EXTENSIONS=V

# Generate coverage metrics (for reference model configs)
make coverage

# Clean all generated artifacts
make clean

# Clean only generated tests (not build artifacts)
make clean-tests
```

### Python Quality Tools

All Python code must pass linting and type checking before submission:

```bash
# Run linter and type checker
make lint

# Auto-fix linting issues
make lint-fix

# Format code (handled by ruff)
make format
```

All commands must be run via `uv` to ensure correct Python environment and versions.

### Running Tests on Hardware/Simulation

Generated self-checking ELFs are output to `work/<config_name>/elfs/`. Each test produces output to stdout:
- **PASSED**: `RVCP-SUMMARY: Test File "<test_name.S>": PASSED`
- **FAILED**: `RVCP-SUMMARY: Test File "<test_name.S>": FAILED`

For test failures, the output includes:
- Failing program counter
- Failing instruction
- Register mismatch details (register name, expected vs. actual value)

## High-Level Architecture

### Core Components

The framework consists of several key layers:

1. **Configuration Layer** (`config/duts/`, `config/ref/`)
   - **test_config.yaml**: Framework configuration (compiler paths, reference model, UDB file location)
   - **\*.yaml** (UDB config): Device Under Test specification (extensions, parameter values)
   - **model_test.h**: DUT-specific macros (Trickbox) for I/O, interrupts, timers
   - **link.ld**: Linker script for DUT's memory layout
   - **sail.json**: Reference model configuration (memory regions, parameter mappings)

2. **Test Generation Layer** (`generators/`, `testplans/`)
   - **testgen**: Generates unprivileged instruction tests from CSV testplans
   - **coverage**: Generates coverpoint definitions and coverage groups
   - **testplans/*.csv**: Instruction-to-coverpoint mappings for each extension
   - **ctp generator scripts**: Create CTP documentation and normative rule mappings

3. **Framework Layer** (`framework/src/act/`)
   - **act.py**: Main entry point; orchestrates test generation pipeline
   - **makefile_gen.py**: Generates build Makefiles for compilation, simulation, and coverage
   - **select_tests.py**: Filters tests based on DUT configuration
   - **parse_udb_config.py**: Reads and validates UDB configuration
   - **fcov/**: Functional coverage and disassembly infrastructure

4. **Output Layer** (`work/`, `work-ref/`)
   - **tests/**: Generated assembly test files (.S)
   - **build/**: Intermediate compilation artifacts (.sig.elf, signatures)
   - **elfs/**: Final self-checking ELFs ready for execution
   - **coverage/**: Coverage reports (when `--coverage` flag used)

### Workflow: From CSV to Self-Checking ELF

1. **Testplan CSV** (e.g., `testplans/I.csv`)
   - Maps instructions to coverpoints
   - Specifies XLEN applicability (RV32, RV64)

2. **Coverpoint Generators** (`generators/testgen/src/testgen/coverpoints/`)
   - Generate test assembly templates based on coverpoint type
   - Handle variants (e.g., `cp_imm_edges` with `20bit` variant for `auipc`)

3. **Test Generation** (`make tests`)
   - testgen reads CSV, invokes coverpoint generators
   - Creates `.S` assembly files organized by: `tests/{rv32i,rv64i,rv32e,rv64e,priv}/*`
   - Coverage groups generated for functional coverage tracking

4. **Configuration Filtering** (act.py)
   - UDB config selects applicable tests based on supported extensions
   - Filters by parameter values (e.g., misalignment support, PMP entries)

5. **Compilation & Simulation** (act.py → makefile_gen.py)
   - Compiles tests to `.sig.elf` (signature-generating versions)
   - Runs on reference model (Sail) to compute expected results
   - Compiles final self-checking ELFs with expected values embedded

6. **Output ELFs** (`work/<config>/elfs/`)
   - Self-checking: print PASS/FAIL without external oracle
   - Suitable for DUT testbench execution

### Key Design Patterns

**Configuration-Driven Selection**:
- UDB file specifies DUT capabilities (extensions, parameter values)
- ACT framework reads UDB and selects only applicable tests
- No spurious test failures due to unsupported features

**Signature-Based Validation**:
- Intermediate `.sig.elf` files generate architectural signatures
- Sail reference model runs same ELF and computes expected signatures
- Final ELF embeds expected signatures for self-checking

**CSV-to-Code Mapping**:
- Coverpoint generators are registered in testplan CSV processing
- Each row (instruction) + column (coverpoint) maps to generator function
- Variants allow parameterization (e.g., immediate field sizes)

**Extensibility**:
- New instructions: Add row to testplan CSV + decoder entry
- New coverpoints: Create generator module in `generators/testgen/src/testgen/coverpoints/`
- New extensions: Create new CSV testplan file

## Directory Structure

```
riscv-arch-test/
├── config/                    # DUT and reference model configurations
│   ├── duts/cvw/             # CVW-specific configs (rv32gc, rv64gc, rv32imc)
│   ├── ref/                  # Reference model (Sail) configs
│   └── duts/<vendor>/<config>/
│       ├── test_config.yaml  # Framework config (compiler, model paths)
│       ├── <dut>.yaml        # UDB configuration (extensions, parameters)
│       ├── model_test.h      # Trickbox macros (DUT-specific I/O, interrupts)
│       ├── link.ld           # Linker script (memory layout)
│       ├── sail.json         # Sail model config
│       └── rvtest_config.*   # Additional configs (auto-gen in future)
│
├── generators/
│   ├── testgen/              # Unprivileged test generation
│   │   ├── src/testgen/
│   │   │   ├── coverpoints/  # Coverpoint generator modules (cp_*.py)
│   │   │   ├── __main__.py   # Entry point for test generation
│   │   │   └── ...
│   │   └── pyproject.toml    # testgen package config
│   │
│   ├── coverage/             # Coverage generation
│   │   └── covergroupgen.py  # Generates coverage group definitions
│   │
│   └── ctp/                  # Test plan and CTP document generation
│       ├── generate_*.py     # Various CTP-related generators
│       └── ...
│
├── framework/                # ACT4 framework (Python)
│   ├── src/act/
│   │   ├── act.py            # Main CLI entry point
│   │   ├── config.py         # Configuration parsing
│   │   ├── makefile_gen.py   # Makefile generation for build/sim/coverage
│   │   ├── select_tests.py   # Test selection based on UDB config
│   │   ├── parse_udb_config.py
│   │   ├── fcov/             # Functional coverage infrastructure
│   │   └── ...
│   └── pyproject.toml        # Framework package config
│
├── testplans/                # CSV testplans for unprivileged extensions
│   ├── I.csv                 # Base integer extension
│   ├── M.csv, A.csv, F.csv, D.csv, etc.
│   └── *.csv                 # One per supported extension
│
├── tests/                    # Generated assembly tests (auto-created)
│   ├── rv32i/, rv64i/        # Unprivileged 32/64-bit tests
│   ├── rv32e/, rv64e/        # E-variant tests
│   ├── priv/                 # Privileged tests
│   └── env/                  # Test environment headers
│
├── coverpoints/              # Coverpoint definitions
│   ├── norm/                 # Normative rule → coverpoint mappings (YAML)
│   ├── param/                # Parameter effect mappings (YAML)
│   └── *.yaml                # One per test suite
│
├── work/                     # Build output for DUTs (auto-created)
│   ├── cvw-rv64gc/           # Per-config subdirectory
│   │   ├── tests/            # Generated .S files (copies)
│   │   ├── build/            # Intermediate .sig.elf, .sig files
│   │   ├── elfs/             # Final self-checking ELFs
│   │   ├── objdump/          # Disassembly (if objdump_exe configured)
│   │   ├── Makefile          # Generated build Makefile
│   │   └── ...
│   └── ...
│
├── work-ref/                 # Build output for reference model (coverage)
│   └── [same structure as work/]
│
├── ctp/                      # Certification Test Plan documentation (AsciiDoc)
├── docs/                     # Developer guides and documentation
├── testplans/                # Test plan CSV files
├── Makefile                  # Top-level build orchestration
├── README.md                 # Setup and getting started
├── CONTRIBUTION.md           # Contribution guidelines
└── ...
```

## Configuration Files Explained

### test_config.yaml (ACT Framework Config)

Specifies framework settings and tool paths:

```yaml
name: cvw-rv64gc              # DUT identifier (used in output dirs)
compiler_exe: riscv64-unknown-elf-gcc   # Compiler path
objdump_exe: riscv64-unknown-elf-objdump
ref_model_exe: sail_riscv_sim # Sail reference model
ref_model_type: sail
udb_config: cvw-rv64gc.yaml   # Path to UDB config (relative to this file)
linker_script: link.ld
dut_include_dir: .            # Directory containing model_test.h
```

### \*.yaml (UDB Config)

Specifies DUT capabilities and implementation details:

```yaml
hart_isa: RV64IMAFDC          # Base ISA
extensions:
  - name: I                   # Supported extensions
  - name: M
  - name: A
  # ... more extensions
parameters:
  - name: XLEN
    value: 64
  - name: misaligned_access_support
    value: true
  # ... more parameters
```

The Sail reference model is also configured to match these extensions/parameters so expected results are computed correctly.

### model_test.h (Trickbox Macros)

DUT-specific assembly macros for:
- **RVMODEL_HALT_PASS / RVMODEL_HALT_FAIL**: Terminate test with status
- **RVMODEL_IO_INIT / RVMODEL_IO_WRITE_STR**: Console output (if available)
- **RVMODEL_BOOT**: Pre-test boot code
- **Timer/Interrupt macros**: If supported by DUT

### Testplan CSV Format

Each row is an instruction; columns are coverpoints:

```csv
Instruction,Type,RV32,RV64,cp_rs1,cp_rs2,cp_rd,cp_rs1_edges,...
add,R,x,x,x,x,x,x,...
addi,I,x,x,x,,x,x,...
auipc,U,x,x,,,x,,20bit,...
```

- **Instruction**: Mnemonic
- **Type**: Instruction encoding type (R, I, U, etc.)
- **RV32/RV64**: Mark with `x` if applicable
- **Coverpoint columns**: Mark with `x` or variant name (e.g., `20bit`)

## Important Notes on Working with the Codebase

### UDB Configuration is Critical

The UDB configuration file is the source of truth. All test selection and expected results depend on it being accurate. Common issues:
- Mismatched extensions between UDB and Sail config → wrong expected results
- Incorrect parameter values → spurious test failures
- Missing extensions in UDB but needed by DUT → missing test coverage

### Reference Model Must Match DUT Config

The Sail reference model (`sail.json`) must have identical extensions and parameters as the UDB config. The framework doesn't validate this match automatically.

### Test Failures Indicate Configuration Problems First

If a test fails:
1. Check if it's a configuration mismatch (e.g., DUT supports feature but UDB says it doesn't)
2. Check the objdump file to understand what the test is doing
3. Check if Sail model was configured to match
4. Only then suspect a DUT bug

### Adding Instructions

To add support for a new instruction:
1. Add row to `testplans/<extension>.csv` with instruction mnemonic, type, XLEN applicability, and coverpoints
2. Add decoding entry to `framework/src/act/fcov/disassemble.svh`
3. Ensure coverpoint generators exist for referenced coverpoints
4. Run `make tests` to verify generation

### Pre-Commit Hooks

The repository uses `pre-commit` for code quality checks. Configuration in `.pre-commit-config.yaml`:
- Trailing whitespace, end-of-file fixes
- YAML validation
- No large files

Ensure hooks pass before submitting PRs: `pre-commit run --all-files`

## Python Environment

- **Tool**: `uv` (fast Python package manager)
- **Location**: `.venv/` (auto-created and managed by uv)
- **Python version**: 3.12+
- **Key packages**: pydantic, pyjson5, ruamel-yaml, typer

**Important**: Always invoke Python tools via `uv` to ensure correct environment:
```bash
uv run act ...              # Run act framework
uv run testgen ...          # Run test generator
uv run ruff check           # Run linter
make lint                   # Wrapper for linting
```

## Understanding Test Output and Debugging

### Successful Test Compilation

When tests compile successfully, you'll see:
- `.S` files in `tests/rv{32,64}{i,e}/`
- `.sig.elf` files in `work/<config>/build/` (signature versions)
- `.sig` files in `work/<config>/build/` (Sail simulation results)
- Final `.elf` files in `work/<config>/elfs/` (self-checking versions)

### Test Failures at Runtime

Debug output includes:
- **PC (Program Counter)**: Where the test failed
- **Instruction**: The failing instruction
- **Register mismatch**: Which register had wrong value, expected vs. actual

Use the objdump file to find the instruction:
```bash
# Search objdump for failing PC
grep "PC_VALUE" work/config_name/objdump/test_name.elf.objdump
```

### Coverage Reports

When `make coverage` is run with reference model configs, coverage reports are generated showing:
- Which coverpoints were hit
- Which were missed
- Overall coverage percentage

Located in `work-ref/<config>/coverage/`

## Contributing Guidelines

See `CONTRIBUTION.md` for full details. Key points:
1. Update `CHANGELOG.md` with entry following Semantic Versioning
2. Ensure `make lint` passes (run via `uv`)
3. Ensure `make coverage` succeeds (tests generate and compile)
4. Add SPDX license identifier to new files: `// SPDX-License-Identifier: BSD-3-Clause`
5. Set up pre-commit hooks before submitting PRs
