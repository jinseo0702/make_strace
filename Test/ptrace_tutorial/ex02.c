// step3_regs.c
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ptrace.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/user.h>   // struct user_regs_struct
#include <unistd.h>

int main(int argc, char *argv[]){
	if (argc < 2) return 1;

	pid_t child = fork();
	if (child == 0) {
		ptrace(PTRACE_TRACEME, 0, NULL, NULL);
		execvp(argv[1], &argv[1]);
		exit(1);
	}

	int status;
	waitpid(child, &status, 0);
	ptrace(PTRACE_SETOPTIONS, child, NULL, PTRACE_O_TRACESYSGOOD);

	int in_syscall = 0;

	while (1) {
		ptrace(PTRACE_SYSCALL, child, NULL, NULL);
		waitpid(child, &status, 0);

		if (WIFEXITED(status) || WIFSIGNALED(status)) break;

		if (WIFSTOPPED(status) && WSTOPSIG(status) == (SIGTRAP | 0x80)) {
			struct user_regs_struct regs;
			ptrace(PTRACE_GETREGS, child, NULL, &regs);

			if (!in_syscall) {
				printf("syscall (%lld, 0x%llx, 0x%llx, 0x%llx)",
					(long long)regs.orig_rax,
					(long long)regs.rdi,
					(long long)regs.rsi,
					(long long)regs.rdx);
				in_syscall = 1;
			} else {
				printf(" = %lld\n", (long long)regs.rax);
				in_syscall = 0;
			}
		}
	}
	return 0;
}