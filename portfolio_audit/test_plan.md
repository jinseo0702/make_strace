# ft_strace Baseline Test Plan

## Objective

Measure the untouched implementation's observable behavior against GNU strace 6.19. Tests and generated evidence remain under `portfolio_audit/`; normal project build artifacts are recorded separately and are not treated as source changes.

## Build policy

1. Run the repository's documented default build path: `make`.
2. Capture the exact command, stdout, stderr, exit code, and duration.
3. Never modify source to make the build pass.
4. If the default build fails, report that failure. A separate diagnostic binary may be compiled only by changing command-line warning policy, never the source, and must be clearly identified as a non-default diagnostic build.
5. Compile test programs with `gcc -Wall -Wextra -Werror -O0 -g` into `portfolio_audit/bin/`.

## Selected syscall scope

Fifteen representative syscall names are selected across six categories:

| Category | Syscalls |
|---|---|
| File I/O | `write`, `read`, `lseek` |
| Filesystem / descriptor | `openat`, `close`, `newfstatat` |
| Memory | `mmap`, `mprotect`, `munmap` |
| Process | `getpid`, `execve`, `clone` |
| Signal | `rt_sigaction`, `kill` |
| Network | `socketpair` |

Control cases additionally cover an unknown syscall number and tracee exit-status propagation. A freestanding i386 compatibility case reuses `getpid` and `write` without increasing the selected-syscall count.

## Deterministic cases

| ID | Target behavior | Core comparison |
|---|---|---|
| t01_write_binary | Four-byte write containing NUL and newline | buffer bytes, length, return |
| t02_write_efault | Invalid pointer passed to write | pointer/error semantics and `EFAULT` |
| t03_read_pipe | Read known `READ` payload into a preinitialized buffer | completed output buffer and return |
| t04_open_close | `/dev/null` success plus guaranteed nonexistent path | dirfd, path, flags, fd, `ENOENT` |
| t05_lseek64 | Seek to `0x100000002` | preservation of a value above 32 bits |
| t06_newfstatat | Stat `/dev/null` | path, flags, output structure detail |
| t07_memory | Anonymous mmap, mprotect, munmap | length/protection/flags/return sequence |
| t08_getpid | Direct no-argument syscall | syscall name and numeric return |
| t09_execve | Exec helper with `alpha`, `beta`, empty environment | path, argv, process-image replacement, final exit 23 |
| t10_signal | Install SIGUSR1 handler and signal self | action setup, signal number, delivery/resume |
| t11_clone_descendant | Direct fork-like clone; child writes marker | clone and descendant trace coverage |
| t12_socketpair | Create and close a local socket pair | domain/type/protocol and returned fd pair |
| t13_unknown | Invoke syscall number 999 | unknown fallback and `ENOSYS` |
| t14_exit_status | Tracee returns 7 | trace report and tracer status propagation |
| t15_i386_smoke | Freestanding 32-bit `getpid` plus `write(EFAULT)` | ABI selection and signed errno handling |

Each program self-checks its setup and syscall result. A setup failure is distinguished from a tracer failure by its distinct exit status and captured stdout/stderr.

## Execution protocol

For each case, execute the same binary and arguments under:

```text
./ft_strace ./portfolio_audit/bin/<case> [arguments]
strace ./portfolio_audit/bin/<case> [arguments]
```

Use a five-second timeout per engine. Capture exact argv, stdout, stderr, return code, timeout flag, duration, and execution exception under `raw/cases/<case>/`.

For t11, also run `strace -f` as a separately named reference (`gnu_follow`). GNU's default run remains captured; only the `gnu_follow` evidence is used to measure the explicit descendant-tracing capability.

The host lacks 32-bit libc development headers, so t15 is assembled and linked without libc using `as --32` and `ld -m elf_i386`. Its build and paired runs are recorded separately in `raw/i386_run_index.json`.

## Semantic comparison and normalization

Raw output is never modified. A derived comparison may normalize only:

- process IDs and addresses/pointer values that legitimately vary;
- decimal versus hexadecimal representation of the same integer;
- equivalent errno symbol/text representations;
- equivalent escaping of the same byte sequence;
- ordering of symbolic flag tokens when the numeric flag set is equivalent;
- dynamic-loader and unrelated auxiliary syscalls by filtering to the case's declared targets.

The following are not normalized away:

- a missing target syscall;
- a wrong syscall name, core argument, return value, or errno;
- missing kernel-produced output data when that data is central to the case;
- a missing child event in the descendant-tracing case;
- timeout, crash, tracee corruption, or wrong tracer exit behavior.

## Classification

- **PASS**: target syscall semantics match GNU strace after allowed normalization.
- **PARTIAL**: tracing completes and core invocation/result is correct, but non-core argument structure, symbolic decoding, or formatting detail is missing.
- **FAIL**: a core syscall, argument, output value, return, errno, sequence, or declared tracer behavior is wrong or absent.
- **CRASH**: ft_strace or the tracee is abnormally terminated or unusably timed out because of tracing.

Counts are derived from `test_results.json`; they are never entered independently into summaries.
