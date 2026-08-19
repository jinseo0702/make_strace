#define _GNU_SOURCE
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

int main(void)
{
    struct stat status;
    long result;

    result = syscall(SYS_newfstatat, AT_FDCWD, "/dev/null", &status, 0);
    if (result != 0)
        return 61;
    if (!S_ISCHR(status.st_mode))
        return 62;
    return 0;
}
