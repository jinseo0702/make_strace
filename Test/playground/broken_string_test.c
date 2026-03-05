/*
gcc -Wall -Wextra -Werror -g -D_GNU_SOURCE \
Test/playground/broken_string_test.c \
-o Test/playground/broken_string_test
*/

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>

static void print_ret(const char *tag, long ret)
{
    if (ret < 0)
        fprintf(stderr, "%s -> -1 (errno=%d: %s)\n", tag, errno, strerror(errno));
    else
        fprintf(stderr, "%s -> %ld\n", tag, ret);
}

int main(void)
{
    char raw[24] = {
        'A', 'B', 'C', 0x00, 'X', 'Y', 'Z', '\n',
        (char)0xff, (char)0xfe, 'Q', '\n',
        '1', '2', '3', '4', '5', '6', '7', '8',
        '\n', 0x00, 'K', '\n'
    };

    long ret = syscall(SYS_write, STDOUT_FILENO, raw, sizeof(raw));
    print_ret("write(raw-with-nul-and-binary)", ret);

    size_t page = (size_t)sysconf(_SC_PAGESIZE);
    char *p = mmap(NULL, page * 2, PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) {
        perror("mmap");
        return 1;
    }

    memset(p, 'Z', page);
    if (mprotect(p + page, page, PROT_NONE) != 0) {
        perror("mprotect");
        munmap(p, page * 2);
        return 1;
    }

    char *edge = p + page - 8;
    memcpy(edge, "EDGE!!!!", 8);
    ret = syscall(SYS_write, STDOUT_FILENO, edge, 64);
    print_ret("write(cross-page)", ret);

    errno = 0;
    ret = syscall(SYS_write, STDOUT_FILENO, (void *)0x1, 16);
    print_ret("write(bad-pointer)", ret);

    munmap(p, page * 2);
    return 0;
}
