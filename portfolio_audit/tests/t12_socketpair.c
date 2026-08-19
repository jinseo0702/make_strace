#define _GNU_SOURCE
#include <sys/socket.h>
#include <sys/syscall.h>
#include <unistd.h>

int main(void)
{
    int sockets[2] = {-1, -1};
    long result;

    result = syscall(SYS_socketpair, AF_UNIX, SOCK_STREAM, 0, sockets);
    if (result != 0)
        return 121;
    if (sockets[0] < 0 || sockets[1] < 0)
        return 122;
    if (sockets[0] == sockets[1])
        return 123;
    if (syscall(SYS_close, sockets[0]) != 0)
        return 124;
    if (syscall(SYS_close, sockets[1]) != 0)
        return 125;
    return 0;
}
