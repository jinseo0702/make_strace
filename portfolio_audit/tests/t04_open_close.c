#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <sys/syscall.h>
#include <unistd.h>

int main(void)
{
    static const char missing[] = "/proc/self/fd/2147483647";
    long fd;
    long result;

    fd = syscall(SYS_openat, AT_FDCWD, "/dev/null", O_RDONLY, 0);
    if (fd < 0)
        return 41;
    result = syscall(SYS_close, (int)fd);
    if (result != 0)
        return 42;
    errno = 0;
    fd = syscall(SYS_openat, AT_FDCWD, missing, O_RDONLY, 0);
    if (fd != -1)
        return 43;
    if (errno != ENOENT)
        return 44;
    return 0;
}
