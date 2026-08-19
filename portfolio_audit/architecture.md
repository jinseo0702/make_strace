# ft_strace Architecture Baseline

## Snapshot and scope

- Commit: `5a59c386c69332bd2dacc5824bf2a8958c9d9037`
- Architecture evidence: repository source at that commit
- Runtime claims: excluded from this document unless explicitly linked to raw test evidence
- Existing implementation changes: none

## Actual control flow

```text
main(argc, argv)
  -> validate argv[1] with lstat and execute-bit checks
  -> fork
     child  -> raise(SIGSTOP) -> execvp(argv[1], &argv[1])
     parent -> install tracer signal handlers
            -> waitpid(child, WUNTRACED)
            -> PTRACE_SEIZE(TRACESYSGOOD | EXITKILL)
            -> PTRACE_INTERRUPT -> waitpid
            -> repeat:
                 PTRACE_SYSCALL -> waitpid
                 syscall-stop (SIGTRAP | 0x80)
                   -> PTRACE_GETREGSET(NT_PRSTATUS)
                   -> extract x86-64 or i386 register arguments
                   -> entry: sparse syscall-table lookup
                             -> ARG-type formatter dispatch
                             -> print name(arguments) to stderr
                   -> exit:  print generic rax/eax result or strerror text
                 other stop
                   -> print limited siginfo and reinject signal
            -> print tracee exit/signal summary
            -> return 0 from the tracer
```

Primary evidence: `ft_strace.c:209-376`.

## Components

| Component | Implementation | Evidence |
|---|---|---|
| CLI | One required executable path followed by tracee arguments; no option parser | `ft_strace.c:209-231` |
| Tracee creation | `fork`, child `SIGSTOP`, then `execvp` | `ft_strace.c:233-240` |
| ptrace setup | Parent seizes only the created child | `ft_strace.c:246-249` |
| Stop loop | One PID, one `in_syscall` boolean, synchronous `waitpid` | `ft_strace.c:250-366` |
| Register access | `PTRACE_GETREGSET` with manually declared x86-64/i386 layouts | `ft_strace.c:259-286`, `include/user.h:4-71` |
| Recognition metadata | Two X-macro lists expanded to sparse designated-initializer tables | `include/strace_data.h:4-864` |
| Argument formatting | Table type tags dispatch to seven formatter functions | `ft_strace.c:45-207`, `ft_strace.c:310-338` |
| Tracee memory reads | `process_vm_readv` for strings and argument vectors | `ft_strace.c:83-185` |
| Return formatting | One generic success/error branch for every syscall | `ft_strace.c:341-350` |
| Signal reporting | Limited `siginfo_t` output and attempted reinjection | `ft_strace.c:355-365` |

## Verified design boundaries

### Launch and attachment

The program launches a child; it has no existing-PID attach mode. The `lstat(argv[1])` precheck also means a bare executable name found only through `PATH` can be rejected before `execvp` is attempted.

### Syscall state

Entry and exit are inferred by toggling one process-global boolean on each syscall-stop. There is no `PTRACE_GET_SYSCALL_INFO`, PID/TID-indexed state, saved entry record, or explicit restart/exec resynchronization.

### ABI selection

The `PTRACE_GETREGSET` result length selects x86-64 only when it exactly equals the locally declared 64-bit structure size; every other length follows the i386 branch. The return status is not checked. A persistent `flag` chooses the table after a 32-bit observation.

### Decode model

The syscall table supplies only a printed name, argument count, and six argument type tags. There are no per-syscall decoder functions. `ARG_STR` and `ARG_VSTR` dereference tracee memory; flags, modes, signals, structures, and generic pointers are rendered as raw numeric values or addresses.

All arguments are formatted at syscall entry. Consequently, buffers populated by the kernel (for example `read`) cannot be decoded from their completed contents by the current exit path. The exit path retains only the new register snapshot and prints a generic result.

### Process tree and exec

`PTRACE_O_TRACEFORK`, `PTRACE_O_TRACEVFORK`, `PTRACE_O_TRACECLONE`, and `PTRACE_O_TRACEEXEC` are absent. Only the original child PID is waited on, so descendant tracing and per-process state are not implemented even though the relevant syscall names occur in the metadata table.

### Error handling

Argument-count and executable-path errors have explicit checks. `fork`, `waitpid`, `ptrace`, most `process_vm_readv` calls, and signal-resume operations do not have checked failure paths. The tracer returns zero after normal loop termination independently of the tracee's exit status.

## Static risks to verify at runtime

These are source observations, not runtime failure claims:

- `ARG_SIZE` and `ARG_OFFSET` use an `int` formatter and can lose upper bits on x86-64 (`ft_strace.c:45-51`, `ft_strace.c:195-196`).
- i386 `eax` is assigned through an unsigned field before the negative-errno test (`ft_strace.c:284-285`, `ft_strace.c:343-349`).
- `fmt_str` ignores the `process_vm_readv` result (`ft_strace.c:83-136`).
- `fmt_vstr` uses native `uintptr_t` stride, which is not the pointer width of a 32-bit tracee on a normal 64-bit build (`ft_strace.c:139-185`).
- Output is accumulated with unbounded `sprintf` calls in fixed-size buffers (`ft_strace.c:83-185`, `ft_strace.c:290-338`).

## Runtime validation of selected risks

| Source observation | Runtime result |
|---|---|
| Output strings are read at syscall entry | Confirmed: `read` prints pre-call `XXXX`, not returned `READ` (`t03`) |
| `ARG_OFFSET` uses `fmt_int` | Confirmed: `4294967298` is displayed as `2` (`t05`) |
| Failed `process_vm_readv` is ignored | Confirmed: pointer `0x1` becomes a zero-filled buffer (`t02`, `t15`) |
| i386 `eax` is not sign-extended | Confirmed: `-EFAULT` is displayed as `0xfffffff2` (`t15`) |
| No descendant trace options/state | Confirmed: child write/exit absent from ft_strace and present under GNU `-f` (`t11`) |
| Tracer always returns zero | Confirmed for tracee exits 7 and 23 (`t14`, `t09`) |

No runtime crash occurred in the fifteen focused cases. The fixed-buffer overflow risk was not exercised and remains unverified.
