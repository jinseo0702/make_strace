#define _GNU_SOURCE
#include <sys/syscall.h>
#include <unistd.h>

int main(void)
{
    static const char payload[4] = {'A', '\0', 'B', '\n'};
    long written;

    written = syscall(SYS_write, STDOUT_FILENO, payload, sizeof(payload));
    if (written < 0)
        return 11;
    if (written != (long)sizeof(payload))
        return 12;
    return 0;
}
