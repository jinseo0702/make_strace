#define _GNU_SOURCE
#include <signal.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>

static volatile sig_atomic_t g_seen;

static void handle_sigusr1(int signal_number)
{
    if (signal_number == SIGUSR1)
        g_seen = 1;
}

int main(void)
{
    struct sigaction action;
    long pid;

    memset(&action, 0, sizeof(action));
    action.sa_handler = handle_sigusr1;
    if (sigemptyset(&action.sa_mask) != 0)
        return 101;
    if (sigaction(SIGUSR1, &action, NULL) != 0)
        return 102;
    pid = syscall(SYS_getpid);
    if (pid <= 0)
        return 103;
    if (syscall(SYS_kill, (pid_t)pid, SIGUSR1) != 0)
        return 104;
    if (g_seen != 1)
        return 105;
    return 0;
}
