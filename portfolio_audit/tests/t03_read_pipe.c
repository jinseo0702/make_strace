#define _GNU_SOURCE
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>

int main(void)
{
    static const char expected[4] = {'R', 'E', 'A', 'D'};
    char buffer[4] = {'X', 'X', 'X', 'X'};
    int pipefd[2];
    long result;

    if (pipe(pipefd) != 0)
        return 31;
    result = syscall(SYS_write, pipefd[1], expected, sizeof(expected));
    if (result != (long)sizeof(expected))
        return 32;
    result = syscall(SYS_read, pipefd[0], buffer, sizeof(buffer));
    if (result != (long)sizeof(buffer))
        return 33;
    if (memcmp(buffer, expected, sizeof(buffer)) != 0)
        return 34;
    (void)syscall(SYS_close, pipefd[0]);
    (void)syscall(SYS_close, pipefd[1]);
    return 0;
}
