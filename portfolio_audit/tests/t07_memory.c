#define _GNU_SOURCE
#include <stdint.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>

int main(void)
{
    volatile unsigned char *bytes;
    long map_result;
    long page_size;

    page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0)
        return 71;
    map_result = syscall(SYS_mmap, NULL, (size_t)page_size,
            PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (map_result == -1)
        return 72;
    bytes = (volatile unsigned char *)(uintptr_t)map_result;
    bytes[0] = 0x5a;
    if (syscall(SYS_mprotect, (void *)bytes, (size_t)page_size,
            PROT_READ) != 0) {
        (void)syscall(SYS_munmap, (void *)bytes, (size_t)page_size);
        return 73;
    }
    if (bytes[0] != 0x5a) {
        (void)syscall(SYS_munmap, (void *)bytes, (size_t)page_size);
        return 74;
    }
    if (syscall(SYS_munmap, (void *)bytes, (size_t)page_size) != 0)
        return 75;
    return 0;
}
