// step3_regs.c
#include "../../include/strace_data.h"
#include <ctype.h>
#include <stddef.h>
#include <string.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ptrace.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/user.h>   // struct user_regs_struct
#include <unistd.h>
#include <sys/uio.h>
#include <fcntl.h>
#include <elf.h>
#include <signal.h>

int pid_temp = 0;

void fmt_int(unsigned long long v, char *out, const int *type, int *offset, int i, struct user_regs_struct regs){
	(void)i;
	(void)regs;
	(void)type;
	int temp = (int)v;
	*offset += sprintf(out + *offset, "%d", temp);
}

void fmt_long(unsigned long long v, char *out, const int *type, int *offset, int i, struct user_regs_struct regs){
	(void)i;
	(void)regs;
	(void)type;
	long long temp = (long long)v;
	*offset += sprintf(out + *offset, "%lld", temp);
}

void fmt_uint(unsigned long long v, char *out, const int *type, int *offset, int i, struct user_regs_struct regs){
	(void)i;
	(void)regs;
	(void)type;
	unsigned int temp = (unsigned int)v;
	*offset += sprintf(out + *offset, "%u", temp);
}

void fmt_ulong(unsigned long long v, char *out, const int *type, int *offset, int i, struct user_regs_struct regs){
	(void)i;
	(void)regs;
	(void)type;
	*offset += sprintf(out + *offset, "0x%llx", v);
};

void fmt_ptr(unsigned long long v, char *out, const int *type, int *offset, int i, struct user_regs_struct regs){
	(void)i;
	(void)regs;
	(void)type;
	*offset += sprintf(out + *offset, "0x%llx", v);
};

void fmt_str(unsigned long long v, char *out, const int *type, int *offset, int i, struct user_regs_struct regs){
	unsigned long long temp = 0;
	char buf[4095];
	memset(buf, 0, sizeof(buf));
	struct iovec local[1];
	struct iovec remote[1];
	local[0].iov_base = buf;
	local[0].iov_len = sizeof(buf);
	remote[0].iov_base = (void *)v;
	remote[0].iov_len = 4095;
	process_vm_readv(pid_temp, local, 1, remote, 1, 0);
	switch (i + 1) {
		case 0:
			temp = regs.rdi;
		break;
		case 1:
			temp = regs.rsi;
		break;
		case 2:
			temp = regs.rdx;
		break;
		case 3:
			temp = regs.r10;
		break;
		case 4:
			temp = regs.r8;
		break;
		case 5:
			temp = regs.r9;
		break;
	}
	if (type[i + 1] == ARG_SIZE) {
		char buf2[9190];
		memset(buf2, 0, sizeof(buf2));
		int count_len = 0;
		for (size_t i = 0; i < temp; i++) {
			if (isprint(buf[i])) {
				count_len += sprintf(buf2 + count_len, "%c", buf[i]);
			}
			else {
				count_len += sprintf(buf2 + count_len, "\\%d", buf[i]);
			}
			if (strlen(buf2) >= 62) break;
		}
		*offset += sprintf(out + *offset, "\"%s\"", buf2);
		if (strlen(buf2) >= 62) {
			*offset += sprintf(out + *offset, "...");
		}
	}
	else {
		*offset += sprintf(out + *offset, "\"%s\"", buf);
	}
};

typedef void (*arg_fmt_fn)(unsigned long long v, char *out, const int *type, int *offset, int i, struct user_regs_struct regs);

static arg_fmt_fn g_fmt[] = {
	[ARG_FD] = fmt_int,
	[ARG_STR] = fmt_str,
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
	[ARG_UINT] = fmt_uint,
	[ARG_ULONG] =  fmt_ulong,
	[ARG_LONG] = fmt_long,
	[ARG_INT] = fmt_int,
};

int main(int argc, char *argv[]){
	if (argc < 2) return 1;

	pid_t child = fork();
	pid_temp = child;
	if (child == 0) {
		raise(SIGSTOP);
		execvp(argv[1], &argv[1]);
		exit(1);
	}

	int status;
	waitpid(child, &status,  WUNTRACED);
	ptrace(PTRACE_SEIZE, child, NULL, PTRACE_O_TRACESYSGOOD);
	ptrace(PTRACE_INTERRUPT, child, NULL, NULL);
	waitpid(child, &status, 0);
	kill(child, SIGCONT);
	int in_syscall = 0;
	/*
	//test print mem//
	char bufmem[4095];
	memset(bufmem, 0, sizeof(bufmem));
	sprintf(bufmem, "/proc/%d/maps", child);
	int cfd = open(bufmem, O_RDONLY);
	memset(bufmem, 0, sizeof(bufmem));
	read(cfd, bufmem, sizeof(bufmem));
	printf("%s", bufmem);
	pread(cfd, bufmem, sizeof(Elf64_Ehdr), 0);
	for (size_t i = 0; i < sizeof(Elf64_Ehdr); i++) {
		if (isprint(bufmem[i])) {
			printf("%c", bufmem[i]);
		}
		else {
			printf("\\%d", bufmem[i]);
		}
	}
	printf("\n");
	close(cfd);
	//---------//
	*/
	while (1) {
		ptrace(PTRACE_SYSCALL, child, NULL, NULL);
		waitpid(child, &status, 0);

		if (WIFEXITED(status) || WIFSIGNALED(status)) break;

		if (WIFSTOPPED(status) && WSTOPSIG(status) == (SIGTRAP | 0x80)) {
			struct user_regs_struct regs;
			struct iovec iov;
			iov.iov_base = &regs;
			iov.iov_len = sizeof(regs);
			ptrace(PTRACE_GETREGSET, child, NT_PRSTATUS, &iov);
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
							fn(regs.rdi, buf, temp.argType, &offset, i, regs);
						break;
						case 1:
							fn(regs.rsi, buf, temp.argType, &offset, i, regs);
						break;
						case 2:
							fn(regs.rdx, buf, temp.argType, &offset, i, regs);
						break;
						case 3:
							fn(regs.r10, buf, temp.argType, &offset, i, regs);
						break;
						case 4:
							fn(regs.r8, buf, temp.argType, &offset, i, regs);
						break;
						case 5:
							fn(regs.r9, buf, temp.argType, &offset, i, regs);
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
				if ((long long)regs.rax < 0 && (long long)regs.rax > -4096){
					int err = (int)(-(long long)regs.rax);
					printf(" = -1 %s\n", strerror(err));
				}
				else {
					printf(" = 0x%llx\n", (long long)regs.rax);
				}
				in_syscall = 0;
			}
		}
	}
	return 0;
}