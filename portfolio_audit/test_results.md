# ft_strace Baseline Test Results

- Main run ID: `20260818T014136.002211Z-24035`
- i386 run ID: `i386-20260818T014525.931589Z`
- Generated: `2026-08-18T02:25:28.100768Z`
- Existing source changes: none (verified separately in `baseline.md`)

## Summary

| Metric | Count |
|---|---:|
| Regression tests | 15 |
| PASS | 5 |
| PARTIAL | 3 |
| FAIL | 7 |
| CRASH | 0 |
| Selected syscall names | 15 |

The full-table `Fully decoded syscalls` count is **확인 불가**. The suite measures 15 focused cases, not every populated ABI row.

## Classification table

| Case | Category | Target syscall(s) | Result | Evidence-backed finding |
|---|---|---|---|---|
| `t01_write_binary` | File I/O | `write` | **PASS** | The same four bytes and return value are recoverable; ft_strace uses decimal backslash escapes (`\0`, `\10`). |
| `t02_write_efault` | File I/O / error | `write` | **FAIL** | ft_strace displays a fabricated 16-byte zero buffer, then reports Bad address. |
| `t03_read_pipe` | File I/O | `read`, `write` | **FAIL** | ft_strace prints the pre-syscall sentinel `XXXX` instead of the returned bytes `READ`. |
| `t04_open_close` | Filesystem | `openat`, `close` | **PASS** | Names, numeric dirfd/flags, paths, fd, success returns, and errno meaning match; only symbolic formatting differs. |
| `t05_lseek64` | File I/O | `lseek` | **FAIL** | ft_strace prints the argument as 2 while the kernel returns 0x100000002. |
| `t06_newfstatat` | Filesystem | `newfstatat` | **PARTIAL** | ft_strace recognizes the syscall/path and return 0 but prints only the structure address. |
| `t07_memory` | Memory | `mmap`, `mprotect`, `munmap` | **PASS** | All numeric arguments, success returns, and sequence match after address and symbolic-flag normalization. |
| `t08_getpid` | Process | `getpid` | **PASS** | ft_strace reports a positive hexadecimal PID; GNU reports a different positive decimal PID from its separate run. |
| `t09_execve` | Process | `execve` | **FAIL** | The exec path, argv, continued tracing after process-image replacement, and `exited with 23` line are correct, but ft_strace itself returns 0 while GNU strace returns 23. |
| `t10_signal` | Signal | `rt_sigaction`, `kill` | **PARTIAL** | ft_strace preserves delivery and execution but prints numeric/raw action fields and abbreviated siginfo. |
| `t11_clone_descendant` | Process | `clone` | **FAIL** | ft_strace observes parent clone/wait and the program succeeds, but no child syscall appears in its trace. |
| `t12_socketpair` | Network | `socketpair` | **PARTIAL** | ft_strace records numeric domain/type/protocol and success but leaves the fd array as an address. |
| `t13_unknown` | Control | control | **PASS** | ft_strace prints decimal 999 with `Function not implemented`; GNU prints hexadecimal 0x3e7 with ENOSYS. |
| `t14_exit_status` | Control | control | **FAIL** | ft_strace reports `exited with 7` but returns 0; GNU strace returns 7. |
| `t15_i386_smoke` | ABI compatibility | `getpid`, `write` | **FAIL** | 32-bit mode and getpid work, but ft_strace prints a zero-filled buffer and treats -14 as successful hex `0xfffffff2`. |

## Per-case evidence

### t01_write_binary — PASS

- Expected: write fd 1 with bytes 41 00 42 0a, length 4, return 4
- Actual: The same four bytes and return value are recoverable; ft_strace uses decimal backslash escapes (`\0`, `\10`).
- Decision: The byte payload, length, return, tracee stdout, and sequence match after the documented escape normalization.
- ft_strace evidence:
  - `write(1, "A\0B\10", 4) = 0x4`
- gnu evidence:
  - `write(1, "A\0B\n", 4)                   = 4`

### t02_write_efault — FAIL

- Expected: display pointer 0x1 and return EFAULT
- Actual: ft_strace displays a fabricated 16-byte zero buffer, then reports Bad address.
- Decision: Ignoring the failed process_vm_readv changes a core argument from pointer 0x1 to data that was never read.
- ft_strace evidence:
  - `write(1, "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0", 16) = -1 Bad address`
- gnu evidence:
  - `write(1, 0x1, 16)                       = -1 EFAULT (Bad address)`

### t03_read_pipe — FAIL

- Expected: read(fd, "READ", 4) = 4 after the kernel fills the buffer
- Actual: ft_strace prints the pre-syscall sentinel `XXXX` instead of the returned bytes `READ`.
- Decision: A core output argument is wrong because all arguments are formatted at syscall entry.
- ft_strace evidence:
  - `read(3, "XXXX", 4) = 0x4`
- gnu evidence:
  - `read(3, "READ", 4)                      = 4`

### t04_open_close — PASS

- Expected: open /dev/null, close fd 3, then receive ENOENT for a nonexistent path
- Actual: Names, numeric dirfd/flags, paths, fd, success returns, and errno meaning match; only symbolic formatting differs.
- Decision: AT_FDCWD=-100, O_RDONLY=0, hexadecimal success values, and strerror text are semantically equivalent.
- ft_strace evidence:
  - `openat(-100, "/dev/null", 0x0, 0) = 0x3`
  - `close(3) = 0x0`
  - `openat(-100, "/proc/self/fd/2147483647", 0x0, 0) = -1 No such file or directory`
- gnu evidence:
  - `openat(AT_FDCWD, "/dev/null", O_RDONLY) = 3`
  - `close(3)                                = 0`
  - `openat(AT_FDCWD, "/proc/self/fd/2147483647", O_RDONLY) = -1 ENOENT (No such file or directory)`

### t05_lseek64 — FAIL

- Expected: lseek offset 4294967298 with the same return value
- Actual: ft_strace prints the argument as 2 while the kernel returns 0x100000002.
- Decision: The high 32 bits of a core argument are lost by the int formatter.
- ft_strace evidence:
  - `lseek(3, 2, 0) = 0x100000002`
- gnu evidence:
  - `lseek(3, 4294967298, SEEK_SET)          = 4294967298`

### t06_newfstatat — PARTIAL

- Expected: path and successful stat result including the kernel-produced stat structure
- Actual: ft_strace recognizes the syscall/path and return 0 but prints only the structure address.
- Decision: The syscall is traced correctly while a significant output structure is omitted rather than misreported.
- ft_strace evidence:
  - `newfstatat(-100, "/dev/null", 0x7ffe5de503f0, 0x0) = 0x0`
- gnu evidence:
  - `newfstatat(AT_FDCWD, "/dev/null", {st_mode=S_IFCHR|0666, st_rdev=makedev(0x1, 0x3), ...}, 0) = 0`

### t07_memory — PASS

- Expected: map one 4096-byte RW anonymous page, protect it read-only, then unmap it
- Actual: All numeric arguments, success returns, and sequence match after address and symbolic-flag normalization.
- Decision: Raw numeric protection/map flags retain the same semantic values as GNU's symbolic rendering.
- ft_strace evidence:
  - `mmap(0x0, 0x1000, 0x3, 0x22, -1, 0x0) = 0x7880991f9000`
  - `mprotect(0x7880991f9000, 4096, 0x1) = 0x0`
  - `munmap(0x7880991f9000, 4096) = 0x0`
- gnu evidence:
  - `mmap(NULL, 4096, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) = 0x784aca7dc000`
  - `mprotect(0x784aca7dc000, 4096, PROT_READ) = 0`
  - `munmap(0x784aca7dc000, 4096)            = 0`

### t08_getpid — PASS

- Expected: getpid() with a positive PID return
- Actual: ft_strace reports a positive hexadecimal PID; GNU reports a different positive decimal PID from its separate run.
- Decision: PID is a documented dynamic value and the syscall name, arity, and return semantics match.
- ft_strace evidence:
  - `getpid() = 0x5e62`
- gnu evidence:
  - `getpid()                                = 24165`

### t09_execve — FAIL

- Expected: decode helper path/argv, continue after exec, report exit 23, and return status 23 from the tracer
- Actual: The exec path, argv, continued tracing after process-image replacement, and `exited with 23` line are correct, but ft_strace itself returns 0 while GNU strace returns 23.
- Decision: Tracee exit-status propagation is declared core behavior for this case and is wrong.
- ft_strace evidence:
  - `execve("portfolio_audit/bin/exec_target", ["portfolio_audit/bin/exec_target", "alpha", "beta"], 0x7fff5e1e8108) = 0x0`
  - `+++ exited with 23 +++`
- gnu evidence:
  - `execve("portfolio_audit/bin/exec_target", ["portfolio_audit/bin/exec_target", "alpha", "beta"], 0x7fff1114d108 /* 0 vars */) = 0`
  - `+++ exited with 23 +++`

### t10_signal — PARTIAL

- Expected: install SIGUSR1 handler, send SIGUSR1 to self, deliver it, and exit 0
- Actual: ft_strace preserves delivery and execution but prints numeric/raw action fields and abbreviated siginfo.
- Decision: Core signal behavior works; symbolic signal/action structure detail is omitted.
- ft_strace evidence:
  - `rt_sigaction(0xa, 0x7ffd677227c0, 0x0, 8) = 0x0`
  - `kill(24172, 0xa) = 0x0`
  - `--- USR1 {si_signo=USR1, si_code=0, si_pid=24172, si_uid=1000} ---`
- gnu evidence:
  - `rt_sigaction(SIGUSR1, {sa_handler=0x5cb2337861c9, sa_mask=[], sa_flags=SA_RESTORER, sa_restorer=0x76688ac45cb0}, NULL, 8) = 0`
  - `kill(24175, SIGUSR1)                    = 0`
  - `--- SIGUSR1 {si_signo=SIGUSR1, si_code=SI_USER, si_pid=24175, si_uid=1000} ---`

### t11_clone_descendant — FAIL

- Expected: observe clone plus the child's write and exit when measured against GNU strace -f
- Actual: ft_strace observes parent clone/wait and the program succeeds, but no child syscall appears in its trace.
- Decision: A central descendant-tracing behavior is absent; GNU's follow run records the child write and exit.
- ft_strace evidence:
  - `clone(0x11, 0x0, 0x0, 0x0, 0x0) = 0x5e72`
- gnu_follow evidence:
  - `clone(child_stack=NULL, flags=SIGCHLDstrace: Process 24186 attached`
  - `[pid 24186] write(1, "clone-child\n", 12) = 12`
  - `[pid 24186] +++ exited with 42 +++`

### t12_socketpair — PARTIAL

- Expected: AF_UNIX/SOCK_STREAM success with returned descriptors [3, 4]
- Actual: ft_strace records numeric domain/type/protocol and success but leaves the fd array as an address.
- Decision: The syscall completes correctly while kernel-produced output detail is omitted.
- ft_strace evidence:
  - `socketpair(1, 1, 0, 0x7fff01dbe190) = 0x0`
- gnu evidence:
  - `socketpair(AF_UNIX, SOCK_STREAM, 0, [3, 4]) = 0`

### t13_unknown — PASS

- Expected: identify syscall number 999 as unknown and report ENOSYS
- Actual: ft_strace prints decimal 999 with `Function not implemented`; GNU prints hexadecimal 0x3e7 with ENOSYS.
- Decision: The syscall number and errno meaning match after numeric and errno-text normalization.
- ft_strace evidence:
  - `syscall_999(/* unknown */) = -1 Function not implemented`
- gnu evidence:
  - `syscall_0x3e7(0x7fff77560ef8, 0x7fff77560f08, 0x5ab249f0adb8, 0x71ccab412680, 0x71ccab413fa0, 0) = -1 ENOSYS (Function not implemented)`

### t14_exit_status — FAIL

- Expected: report tracee exit 7 and return 7 from the tracer
- Actual: ft_strace reports `exited with 7` but returns 0; GNU strace returns 7.
- Decision: The observable wrapper exit status is wrong.
- ft_strace evidence:
  - `+++ exited with 7 +++`
- gnu evidence:
  - `+++ exited with 7 +++`

### t15_i386_smoke — FAIL

- Expected: recognize 32-bit mode, getpid, and render write(0x1,16) as -1 EFAULT
- Actual: 32-bit mode and getpid work, but ft_strace prints a zero-filled buffer and treats -14 as successful hex `0xfffffff2`.
- Decision: Unsigned i386 eax handling loses negative errno semantics, and failed memory reading also changes the argument.
- ft_strace evidence:
  - `[ Process PID=26829 runs in 32 bit mode. ]`
  - `getpid() = 0x68cd`
  - `write(1, "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0", 16) = 0xfffffff2`
- gnu evidence:
  - `[ Process PID=26832 runs in 32 bit mode. ]`
  - `getpid()                                = 26832`
  - `write(1, 0x1, 16)                       = -1 EFAULT (Bad address)`

## Reproduction

```text
python3 portfolio_audit/tools/run_baseline.py
python3 portfolio_audit/tools/run_i386_smoke.py
python3 portfolio_audit/tools/analyze_results.py
```

The two ptrace runners require an environment that permits local ptrace. Raw commands, outputs, and result metadata are under `raw/`.
