#define _GNU_SOURCE
#include <sys/syscall.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    char *exec_argv[4];
    char *exec_envp[1];

    if (argc != 2)
        return 91;
    exec_argv[0] = argv[1];
    exec_argv[1] = (char *)"alpha";
    exec_argv[2] = (char *)"beta";
    exec_argv[3] = NULL;
    exec_envp[0] = NULL;
    (void)syscall(SYS_execve, argv[1], exec_argv, exec_envp);
    return 92;
}
