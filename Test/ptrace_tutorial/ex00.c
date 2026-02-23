#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char *argv[]){
    if (argc < 2){
        fprintf(stderr, "Usage: %s <prog> [args...]\n", argv[0]);
        return 1;
    }

    pid_t child = fork();
    if (child == 0) {
        // 자식 : 부모 프로세스가 나를 추적할 수 있도록 커널에 등록
        ptrace(PTRACE_TRACEME, 0, NULL, NULL);
        execvp(argv[1], &argv[1]);
        perror("execvp");
        exit(1);
    }

    int status;
    waitpid(child, &status, 0);
    printf("[tracer] child stopped, signal=%d signal content %s\n", WSTOPSIG(status), strsignal(WSTOPSIG(status)));

    ptrace(PTRACE_CONT, child, NULL, NULL);
    waitpid(child, &status, 0);
    printf("[tracer] child exited: %d\n", WEXITSTATUS(status));
    return 0;
}