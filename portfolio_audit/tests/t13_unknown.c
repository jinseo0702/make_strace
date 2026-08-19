#define _GNU_SOURCE
#include <errno.h>
#include <unistd.h>

int main(void)
{
    long result;

    errno = 0;
    result = syscall(999);
    if (result != -1)
        return 131;
    if (errno != ENOSYS)
        return 132;
    return 0;
}
