// step3_regs.c
#include "../../include/strace_data.h"
#include <string.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ptrace.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/user.h>   // struct user_regs_struct
#include <unistd.h>

int fmt_int(unsigned long long v, char *out, size_t n, int *offset){
	*offset += sprintf(out + *offset, "%d", (int)v);
	return n;
}

int fmt_ptr(unsigned long long v, char *out, size_t n, int *offset){
	*offset += sprintf(out + *offset, "0x%llx", v);
	return n;
};

typedef int (*arg_fmt_fn)(unsigned long long v, char *out, size_t n, int *offset);

static arg_fmt_fn g_fmt[] = {
	[ARG_FD] = fmt_int,
	[ARG_STR] = fmt_ptr,
	[ARG_FLAGS] = fmt_ptr,
	[ARG_MODE] = fmt_int,
	[ARG_SIZE] = fmt_int,
	[ARG_OFFSET] = fmt_int,
	[ARG_PID] = fmt_int,
	[ARG_UID] = fmt_int,
	[ARG_GID] = fmt_int,
	[ARG_SIGNAL] = fmt_ptr,
	[ARG_STRUCT_PTR] = fmt_ptr,
	[ARG_PTR] = fmt_ptr,
	[ARG_INT] = fmt_int,
};

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
			//rdi , rsi , rdx , r10 , r8 , r9
			if (!in_syscall) {
				int offset = 0;
				char buf[4095];
				memset(buf, 0, sizeof(buf));
				t_SYS64_TABLE const temp = get_SYS64_TABLE[regs.orig_rax];
				offset += sprintf(buf, "%s(", temp.name);
				for (int i = 0; i < temp.argCount; i++) {
					arg_fmt_fn fn = g_fmt[temp.argType[i]];
					switch (i) {
						case 0:
							fn(regs.rdi, buf, sizeof(buf) - strlen(buf), &offset);
						break;
						case 1:
							fn(regs.rsi, buf, sizeof(buf) - strlen(buf), &offset);
						break;
						case 2:
							fn(regs.rdx, buf, sizeof(buf) - strlen(buf), &offset);
						break;
						case 3:
							fn(regs.r10, buf, sizeof(buf) - strlen(buf), &offset);
						break;
						case 4:
							fn(regs.r8, buf, sizeof(buf) - strlen(buf), &offset);
						break;
						case 5:
							fn(regs.r9, buf, sizeof(buf) - strlen(buf), &offset);
						break;
					}
					if ((i + 1) < temp.argCount) {
						offset += sprintf(buf + offset, ", ");
					}
				}
				sprintf(buf + offset, ")");
				printf("%s", buf);
				in_syscall = 1;
			} else {
				if ((long long)regs.rax < 0){
					int err = (int)(-(long long)regs.rax);
					printf(" = -1 %s\n", strerror(err));
				}
				else {
					printf(" = %lld\n", (long long)regs.rax);
				}
				in_syscall = 0;
			}
		}
	}
	return 0;
}