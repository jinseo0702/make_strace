#define _GNU_SOURCE
#include <sys/syscall.h>
#include <unistd.h>

int main(void)
{
    long pid;

    pid = syscall(SYS_getpid);
    if (pid <= 0)
        return 81;
    return 0;
}
