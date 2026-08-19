# ft_strace Failure Analysis

This document selects three technically meaningful failures from the measured baseline. It diagnoses the current implementation without modifying it.

## 1. Kernel-produced read data is replaced by pre-call memory

### Expected

```text
read(3, "READ", 4) = 4
```

The test preloads a pipe with `READ`, initializes the destination buffer to `XXXX`, calls `read`, and verifies that the program received `READ`.

### Actual

```text
ft_strace: read(3, "XXXX", 4) = 0x4
GNU:       read(3, "READ", 4) = 4
```

The tracee itself exits successfully, proving that the kernel produced the expected data; only the tracer's representation is wrong.

### Relevant code path

- `read` metadata declares `ARG_STR, ARG_SIZE`: `include/strace_data.h:5`.
- Every argument formatter runs in the syscall-entry branch: `ft_strace.c:288-340`.
- `fmt_str` immediately calls `process_vm_readv`: `ft_strace.c:83-136`.
- The exit branch has only the new register snapshot and generic return formatting: `ft_strace.c:341-350`.

### Likely cause

The architecture does not retain the entry syscall number/arguments for exit-time output decoding. `fmt_str` therefore reads an output buffer before the kernel has filled it.

### How verified

- Test source: `tests/t03_read_pipe.c`
- ft_strace raw output: `raw/cases/t03_read_pipe/ft_strace.stderr`
- GNU raw output: `raw/cases/t03_read_pipe/gnu.stderr`
- Engine metadata: corresponding `.result.json` files
- Classification: `test_results.json`, case `t03_read_pipe`

## 2. A 64-bit lseek offset is narrowed to 32 bits

### Expected

```text
lseek(3, 4294967298, SEEK_SET) = 4294967298
```

### Actual

```text
ft_strace: lseek(3, 2, 0) = 0x100000002
GNU:       lseek(3, 4294967298, SEEK_SET) = 4294967298
```

The correct 64-bit return proves the kernel received the original offset, while the displayed entry argument has lost its high bits.

### Relevant code path

- `lseek` marks argument 2 as `ARG_OFFSET`: `include/strace_data.h:13`.
- `ARG_OFFSET` dispatches to `fmt_int`: `ft_strace.c:189-207`.
- `fmt_int` explicitly converts the register value to `int`: `ft_strace.c:45-51`.

### Likely cause

The generic type-to-formatter mapping assigns a 32-bit signed formatter to an ABI argument that is 64 bits on x86-64.

### How verified

- Test source: `tests/t05_lseek64.c`
- ft_strace raw output: `raw/cases/t05_lseek64/ft_strace.stderr`
- GNU raw output: `raw/cases/t05_lseek64/gnu.stderr`
- Classification: `test_results.json`, case `t05_lseek64`

## 3. i386 negative errno is treated as a successful hexadecimal return

### Expected

```text
write(1, 0x1, 16) = -1 EFAULT (Bad address)
```

### Actual

```text
ft_strace: write(1, "\0...", 16) = 0xfffffff2
GNU:       write(1, 0x1, 16) = -1 EFAULT (Bad address)
```

The freestanding 32-bit test independently checks that the kernel returned `-14`; it exits zero only after seeing that value.

### Relevant code path

- The i386 register definition stores `eax` as `unsigned int`: `include/user.h:35-54`.
- It is assigned to the 64-bit `args.rax` field without sign extension: `ft_strace.c:276-285`.
- The error branch tests `(long long)args.rax < 0`: `ft_strace.c:341-349`.

### Likely cause

`0xfffffff2` is zero-extended to `0x00000000fffffff2`; casting that value to 64-bit signed remains positive, so the negative errno branch is skipped. The simultaneous fabricated-zero argument comes from the independently verified unchecked `process_vm_readv` path.

### How verified

- Test source: `tests/t15_i386_smoke.S`
- Binary provenance: `raw/i386_run_index.json`
- ft_strace raw output: `raw/cases/t15_i386_smoke/ft_strace.stderr`
- GNU raw output: `raw/cases/t15_i386_smoke/gnu.stderr`
- Classification: `test_results.json`, case `t15_i386_smoke`

## Other measured gaps

| Case | Result | Finding |
|---|---|---|
| `t02_write_efault` | FAIL | Failed tracee-memory read becomes invented zero bytes instead of pointer `0x1`. |
| `t06_newfstatat` | PARTIAL | Path/return are correct; output `struct stat` is only an address. |
| `t09_execve` | FAIL | Exec tracing continues and exit 23 is printed, but ft_strace returns 0. |
| `t10_signal` | PARTIAL | Signal delivery works; signal/action/siginfo decoding is limited. |
| `t11_clone_descendant` | FAIL | Parent clone is shown; child write/exit appear only in GNU `-f` evidence. |
| `t12_socketpair` | PARTIAL | Success is shown; returned descriptor pair remains an address. |
| `t14_exit_status` | FAIL | Tracee exit 7 is printed but not propagated. |

