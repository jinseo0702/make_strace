# FT_STRACE BASELINE

## Baseline summary

```text
Commit: 5a59c386c69332bd2dacc5824bf2a8958c9d9037

Architecture:
ptrace-based Linux syscall tracer; one spawned tracee; table-driven generic formatting

Recognized syscall metadata rows:
x86-64: 365 / 470 table slots
i386:   426 / 470 table slots
Total ABI rows: 791
Unique printed names: 421

Fully decoded syscalls across the entire table:
확인 불가

Selected syscall names tested: 15
Regression tests: 15

PASS:    5
PARTIAL: 3
FAIL:    7
CRASH:   0
```

The result totals are generated from `test_results.json` by `tools/analyze_results.py`. They are not independently entered measurements. A full-table decoded count is not stated because fifteen focused cases cannot establish semantic completeness for 791 ABI rows.

## Baseline environment

| Field | Recorded value |
|---|---|
| Phase 0 time | 2026-08-18 10:25:07 +09:00 |
| Commit | `5a59c386c69332bd2dacc5824bf2a8958c9d9037` |
| Initial dirty state | No; `main` matched `origin/main` (+0/-0) |
| OS | Ubuntu 26.04 LTS (Resolute Raccoon) |
| Kernel | `7.0.0-29-generic` |
| Architecture | `x86_64` |
| Compiler | gcc 15.2.0 (`gcc (Ubuntu 15.2.0-16ubuntu1) 15.2.0`) |
| GNU strace | 6.19 |
| Binutils used for i386 | GNU assembler/ld 2.46 |
| Project build | `make` |
| Project run | `./ft_strace <path-to-executable> [arguments...]` |

Machine-readable execution environment and commands are in `raw/environment.json`, `raw/build/`, `raw/compile/`, and `raw/run_index.json`.

## Source integrity

The following hashes were recorded before test execution and reproduced after all evidence generation:

| Existing file | SHA-256 |
|---|---|
| `ft_strace.c` | `bc681b6e8881df382d07b49e89f33e66c925486935bd24beea62f808b4b69e37` |
| `include/strace_data.h` | `55ec7206e72a999c92c2452c6e5df22357c7db896114ff7c1d8c590c70fc9ed0` |
| `include/user.h` | `b7a9af9bcc85bb352997fc687485efbd8106a57e466eac5d5da71b1850feb79d` |
| `Makefile` | `3455dfe06f6640f6b1bd1ff827f08e35269f9deca2c7ad508846a0b8df23667b` |
| `README.md` | `3c54975cf2fa43ab5bce41319377a0cbb3c77e8903158823ed17a42fe7a91dc4` |

`git diff` and `git diff --cached` contain no tracked changes. The post-audit working tree contains only generated `ft_strace`/`ft_strace.o` build products and the new `portfolio_audit/` evidence tree.

## Build result

- Default `make`: exit 0, no timeout.
- Test sources compiled with `gcc -Wall -Wextra -Werror -O0 -g`: 14 case binaries plus one exec helper, all exit 0.
- Freestanding i386 case: `as --32` and `ld -m elf_i386`, both exit 0.
- Produced i386 binary: ELF 32-bit LSB i386, statically linked.

Evidence:

- `raw/build/make.result.json`
- `raw/compile/*.result.json`
- `raw/i386_run_index.json`

## Measurement scope

The suite contains fifteen cases over fifteen selected syscall names:

```text
clone, close, execve, getpid, kill,
lseek, mmap, mprotect, munmap, newfstatat,
openat, read, rt_sigaction, socketpair, write
```

- Fourteen cases use normal x86-64 executables.
- One freestanding i386 case validates ABI selection and negative errno handling without requiring 32-bit libc development headers.
- GNU strace uses its default non-following mode except the explicit descendant capability comparison, which additionally records `strace -f` as `gnu_follow`.
- Each engine receives a five-second timeout; the authoritative run produced no timeout or crash.
- Raw output remains unfiltered. Target-syscall filtering and documented normalization occur only in the derived result artifacts.

## Classification result

| Result | Count | Cases |
|---|---:|---|
| PASS | 5 | `t01`, `t04`, `t07`, `t08`, `t13` |
| PARTIAL | 3 | `t06`, `t10`, `t12` |
| FAIL | 7 | `t02`, `t03`, `t05`, `t09`, `t11`, `t14`, `t15` |
| CRASH | 0 | — |

See `test_results.md` for every expected/actual pair and `test_results.json` for the exact calculation inputs.

## Key verified results

### Successes

- `openat`/`close`: paths, descriptor values, success returns, and ENOENT meaning matched after numeric/symbolic normalization.
- `mmap` → `mprotect` → `munmap`: the same target address was followed through all three calls, and numeric flag values matched GNU semantics.
- Unknown syscall 999: number and ENOSYS meaning matched despite decimal/hex and errno-text differences.
- `execve`: path, argv vector, continued tracing after process-image replacement, and final `exited with 23` reporting all worked; the wrapper exit code still failed separately.

### Failures and omissions

- Output buffers are decoded at entry: `read` reports pre-call `XXXX` rather than returned `READ`.
- `ARG_OFFSET` narrows the 64-bit lseek argument `4294967298` to `2`.
- A failed string read from pointer `0x1` is rendered as a fabricated zero buffer.
- i386 `-EFAULT` is zero-extended and printed as successful `0xfffffff2`.
- Descendant syscalls are not traced after `clone`.
- Tracee exit status is printed but not propagated by the tracer process.
- Stat structures, socketpair output descriptors, signal structures, flags, and similar typed data are not semantically decoded.

## Counting and reproduction

```text
python3 portfolio_audit/tools/generate_syscall_matrix.py
python3 portfolio_audit/tools/run_baseline.py
python3 portfolio_audit/tools/run_i386_smoke.py
python3 portfolio_audit/tools/analyze_results.py
```

The ptrace runners require a local environment that permits ptrace. `analyze_results.py` verifies case-specific raw lines, engine health, return statuses, stdout bytes, build results, source inventory invariants, selected syscall count, and final classification totals before regenerating the results.

## Limitations of this baseline

- It does not execute every populated syscall-table row; untested rows remain unverified.
- The i386 measurement covers `getpid`, `write(EFAULT)`, and `exit`, not the entire 32-bit table.
- It does not benchmark performance or make optimization claims.
- It does not test existing-PID attachment because no such CLI path exists.
- It does not test privileged, destructive, architecture-specific, or environment-dependent syscalls.
- Table presence is reported as recognition metadata, not full support.
