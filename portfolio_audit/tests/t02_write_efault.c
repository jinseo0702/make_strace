#define _GNU_SOURCE
#include <errno.h>
#include <stdint.h>
#include <sys/syscall.h>
#include <unistd.h>

int main(void)
{
    const void *bad_address;
    long result;

    bad_address = (const void *)(uintptr_t)0x1;
    errno = 0;
    result = syscall(SYS_write, STDOUT_FILENO, bad_address, (size_t)16);
    if (result != -1)
        return 21;
    if (errno != EFAULT)
        return 22;
    return 0;
}
