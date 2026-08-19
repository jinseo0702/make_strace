# Deterministic ft_strace baseline fixtures

These programs are isolated audit fixtures. They do not modify the tracer and
do not use printf or perror. A return value of zero means the fixture's own
assertions passed, except for the intentionally nonzero exec and exit-status
cases described below. Setup and assertion failures use distinct nonzero exit
codes in each source file.

Compile each source independently with:

    gcc -Wall -Wextra -Werror -O0 SOURCE.c -o OUTPUT

Do not combine the sources into one executable. For t09, build exec_target.c
separately and pass its executable path as the only argument to t09_execve.

| Fixture | Target syscall(s) | Native expected behavior |
| --- | --- | --- |
| t01_write_binary.c | write | Writes exactly four bytes: A, NUL, B, newline; exits 0. |
| t02_write_efault.c | write | write(1, 0x1, 16) fails with EFAULT; exits 0. |
| t03_read_pipe.c | read | Pipe is preloaded with READ; a buffer initialized to XXXX becomes READ; exits 0. |
| t04_open_close.c | openat, close | /dev/null opens and closes; the impossible proc fd path fails with ENOENT; exits 0. |
| t05_lseek64.c | memfd_create, lseek | Seeking to 0x100000002 returns that exact 64-bit offset; exits 0. |
| t06_newfstatat.c | newfstatat | Stat of /dev/null succeeds and reports a character device; exits 0. |
| t07_memory.c | mmap, mprotect, munmap | One anonymous page is mapped RW, changed to read-only, verified, and unmapped; exits 0. |
| t08_getpid.c | getpid | Direct syscall returns a positive PID; exits 0. |
| t09_execve.c | execve | Executes the helper with argv helper, alpha, beta and an empty environment. |
| exec_target.c | exec target | Validates argv and empty environment, then exits 23. |
| t10_signal.c | kill | Installs a SIGUSR1 handler, signals itself, observes the handler, and exits 0. |
| t11_clone_descendant.c | clone, write, exit | Fork-like clone child writes clone-child marker and exits 42; parent verifies and exits 0. |
| t12_socketpair.c | socketpair | Creates two distinct AF_UNIX SOCK_STREAM descriptors, closes them, and exits 0. |
| t13_unknown.c | syscall 999 | Unknown syscall fails with ENOSYS; exits 0. |
| t14_exit_status.c | process exit | Intentionally returns 7. |

These fixtures are intended to compare native execution with ft_strace output.
Tracer output assertions should distinguish syscall recognition from argument
decoding, return decoding, signal forwarding, descendant tracing, and final
exit-status reporting.
