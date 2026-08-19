#define _GNU_SOURCE
#include <sys/syscall.h>
#include <unistd.h>

int main(void)
{
    const long long expected = 0x100000002LL;
    long fd;
    long result;

    fd = syscall(SYS_memfd_create, "ft_strace-lseek64", 0U);
    if (fd < 0)
        return 51;
    result = syscall(SYS_lseek, (int)fd, expected, SEEK_SET);
    if (result < 0)
        return 52;
    if ((long long)result != expected)
        return 53;
    if (syscall(SYS_close, (int)fd) != 0)
        return 54;
    return 0;
}
