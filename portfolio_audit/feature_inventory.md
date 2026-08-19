# ft_strace Feature Inventory

## Status definitions

- **IMPLEMENTED**: a source path exists for the narrowly stated behavior.
- **PARTIAL**: a source path exists, but important semantics, cases, or error paths are absent.
- **NOT IMPLEMENTED**: no source path exists for the behavior.
- **UNKNOWN**: source inspection is insufficient and runtime evidence is not yet available.

An IMPLEMENTED status does not mean GNU strace parity.

## Inventory

| Feature | Status | Evidence and boundary |
|---|---|---|
| Required program argument | IMPLEMENTED | `argc` check at `ft_strace.c:209-213` |
| Tracee argument forwarding | IMPLEMENTED | `execvp(argv[1], &argv[1])`, `ft_strace.c:238` |
| PATH-only command launch | PARTIAL | `lstat(argv[1])` runs before `execvp`, `ft_strace.c:215-231` |
| Spawned-process tracing | IMPLEMENTED | `fork` plus `PTRACE_SEIZE`, `ft_strace.c:233-249` |
| Existing PID attach | NOT IMPLEMENTED | No PID option or attach path |
| Syscall-stop recognition | IMPLEMENTED | `TRACESYSGOOD` and `SIGTRAP|0x80`, `ft_strace.c:247,257` |
| Syscall entry/exit detection | PARTIAL | Single stop-toggle boolean, `ft_strace.c:250,288-350` |
| x86-64 register extraction | PARTIAL | Register mapping exists; ptrace result is unchecked, `ft_strace.c:259-275` |
| i386 register extraction | PARTIAL | 32-bit mode and `getpid` run, but negative errno is misrendered; `raw/cases/t15_i386_smoke/` |
| Known-number name lookup | IMPLEMENTED | Sparse-table lookup, `ft_strace.c:293-303` |
| Unknown-number fallback | IMPLEMENTED | `syscall_N(/* unknown */)`, `ft_strace.c:305-308` |
| Zero-argument syscall rendering | IMPLEMENTED | Name plus empty argument list through common entry path |
| Scalar argument rendering | PARTIAL | Generic casts/renderers can lose type width or meaning, `ft_strace.c:45-81` |
| C-string argument rendering | PARTIAL | Entry-time `process_vm_readv`; read result ignored, `ft_strace.c:83-137` |
| argv-vector rendering | PARTIAL | Maximum 128 entries and native pointer stride, `ft_strace.c:139-185` |
| Symbolic flag decoding | NOT IMPLEMENTED | `ARG_FLAGS` maps to raw pointer-style hex formatting |
| Symbolic signal decoding | NOT IMPLEMENTED | `ARG_SIGNAL` maps to raw pointer-style hex formatting |
| Symbolic mode decoding | NOT IMPLEMENTED | `ARG_MODE` maps to signed integer formatting |
| Structure decoding | NOT IMPLEMENTED | `ARG_STRUCT_PTR` prints only the address |
| Output-buffer decoding at exit | NOT IMPLEMENTED | No entry arguments are retained for exit-time use |
| Generic successful return rendering | IMPLEMENTED | Every non-error value is printed in hex, `ft_strace.c:347-349` |
| errno-range detection on x86-64 | IMPLEMENTED | `-4095..-1` branch, `ft_strace.c:343-346` |
| errno symbol decoding | NOT IMPLEMENTED | `strerror` text only; no symbolic errno name |
| Syscall-specific return decoding | NOT IMPLEMENTED | One return branch shared by every syscall |
| Signal-stop reporting | PARTIAL | Limited `siginfo_t` fields, `ft_strace.c:355-365` |
| Signal reinjection | PARTIAL | Resume call exists but return is unchecked and the loop resumes again |
| Tracer SIGINT/SIGHUP/SIGTERM handling | PARTIAL | Child is killed; message can claim detach although no detach occurs, `ft_strace.c:22-43` |
| Initial exec launch | IMPLEMENTED | Child calls `execvp` |
| Exec-event-specific handling | NOT IMPLEMENTED | No `PTRACE_O_TRACEEXEC` or event-state reset |
| fork/vfork/clone name recognition | IMPLEMENTED | Names occur in syscall metadata |
| Descendant process tracing | NOT IMPLEMENTED | No trace options, PID collection, or per-PID state |
| Tracee normal-exit reporting | IMPLEMENTED | `+++ exited with N +++`, `ft_strace.c:367-371` |
| Tracee signal-exit reporting | IMPLEMENTED | `+++ killed by SIG... +++`, `ft_strace.c:371-375` |
| Tracee exit-status propagation | NOT IMPLEMENTED | Tracer returns zero at `ft_strace.c:376` |
| ptrace/wait error handling | NOT IMPLEMENTED | Return values are not checked in the trace loop |
| Build automation | IMPLEMENTED | Default `make` target in `Makefile:1-14` |
| Automated regression harness | NOT IMPLEMENTED | No test target, assertion harness, or CI configuration in the baseline tree |
| Successful default build on baseline host | IMPLEMENTED | `make` exit 0; `raw/build/make.result.json` |
| Successful tracing on baseline host | PARTIAL | All 15 cases complete without crash, but result mix is 5 PASS / 3 PARTIAL / 7 FAIL |

## Runtime update

The static inventory above is now paired with fifteen measured cases. This does not change the baseline source-status definitions: table presence remains recognition, and broad semantic completeness remains unknown. The external audit harness is evidence tooling under `portfolio_audit/`; it is not counted as a regression harness that existed in the original implementation.

## Source-counted decoder inventory

| Metric | x86-64 | i386 | Method |
|---|---:|---:|---|
| Populated syscall metadata rows | 365 | 426 | Count `X64(` / `X32(` rows |
| Zero-argument rows | 20 | 25 | Parse table argument count |
| Nonzero-argument rows | 345 | 401 | Populated minus zero-argument rows |
| Declared argument positions | 1,058 | 1,203 | Sum table argument counts |
| Rows containing string/vector memory reading | 103 | 114 | Contains `ARG_STR` or `ARG_VSTR` |
| Vector-string rows | 2 | 2 | `execve`, `execveat` |

The 17 dispatched type tags map to seven formatter functions. This proves generic dispatch coverage for table-declared arguments; it does not prove semantic correctness or full decoding.
