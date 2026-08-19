    .section .text
    .global _start

_start:
    # i386 getpid: verify the compat process is running.
    movl $20, %eax
    int $0x80
    testl %eax, %eax
    jle .Lfail_getpid

    # i386 write(1, (void *)1, 16): expect -EFAULT (-14) in eax.
    movl $4, %eax
    movl $1, %ebx
    movl $1, %ecx
    movl $16, %edx
    int $0x80
    cmpl $-14, %eax
    jne .Lfail_errno

    xorl %ebx, %ebx
    jmp .Lexit

.Lfail_getpid:
    movl $151, %ebx
    jmp .Lexit

.Lfail_errno:
    movl $152, %ebx

.Lexit:
    movl $1, %eax
    int $0x80

