#define _GNU_SOURCE
#include <signal.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void)
{
    static const char marker[] = "clone-child\n";
    int status;
    long child;
    long written;

    child = syscall(SYS_clone, (unsigned long)SIGCHLD, NULL, NULL, NULL, 0UL);
    if (child < 0)
        return 111;
    if (child == 0) {
        written = syscall(SYS_write, STDOUT_FILENO, marker,
                sizeof(marker) - 1);
        (void)syscall(SYS_exit,
                written == (long)(sizeof(marker) - 1) ? 42 : 43);
        return 119;
    }
    if (waitpid((pid_t)child, &status, 0) != (pid_t)child)
        return 112;
    if (!WIFEXITED(status))
        return 113;
    if (WEXITSTATUS(status) != 42)
        return 114;
    return 0;
}
