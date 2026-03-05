// step3_regs.c
#include "../../include/strace_data.h"
#include "../../include/user.h"
#include <ctype.h>
#include <sys/wait.h>
#include <stddef.h>
#include <string.h>
#include <stdint.h>
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
#include <sys/stat.h>

int pid_temp = 0;

void handler(int sig) {
    (void)sig;
    if (pid_temp > 0) {
        kill(pid_temp, SIGKILL);
        waitpid(pid_temp, NULL, 0);
    }
	fprintf(stderr, "\nstrace: Process %d detached\n", pid_temp);
    _exit(1);
}

void handler_term(int sig) {
    (void)sig;
    if (pid_temp > 0) {
        kill(pid_temp, SIGKILL);
        waitpid(pid_temp, NULL, 0);
    }
	fprintf(stderr, "= ?\n");
	fprintf(stderr, "+++ killed by SIGKILL +++\n");
    _exit(1);
}

void fmt_int(unsigned long long v, char *out, const int *type, int *offset, int i, t_syscall_args args){
	(void)i;
	(void)args;
	(void)type;
	int temp = (int)v;
	*offset += sprintf(out + *offset, "%d", temp);
}

void fmt_long(unsigned long long v, char *out, const int *type, int *offset, int i, t_syscall_args args){
	(void)i;
	(void)args;
	(void)type;
	long long temp = (long long)v;
	*offset += sprintf(out + *offset, "%lld", temp);
}

void fmt_uint(unsigned long long v, char *out, const int *type, int *offset, int i, t_syscall_args args){
	(void)i;
	(void)args;
	(void)type;
	unsigned int temp = (unsigned int)v;
	*offset += sprintf(out + *offset, "%u", temp);
}

void fmt_ulong(unsigned long long v, char *out, const int *type, int *offset, int i, t_syscall_args args){
	(void)i;
	(void)args;
	(void)type;
	*offset += sprintf(out + *offset, "0x%llx", v);
};

void fmt_ptr(unsigned long long v, char *out, const int *type, int *offset, int i, t_syscall_args args){
	(void)i;
	(void)args;
	(void)type;
	*offset += sprintf(out + *offset, "0x%llx", v);
};

void fmt_str(unsigned long long v, char *out, const int *type, int *offset, int i, t_syscall_args args){
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
			temp = args.a0;
		break;
		case 1:
			temp = args.a1;
		break;
		case 2:
			temp = args.a2;
		break;
		case 3:
			temp = args.a3;
		break;
		case 4:
			temp = args.a4;
		break;
		case 5:
			temp = args.a5;
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

void fmt_vstr(unsigned long long v, char *out, const int *type, int *offset, int i, t_syscall_args args){
    (void)i;
    (void)args;
    (void)type;

    char buf[4095];
    uintptr_t elem = 0;              // argv[idx] 값 (char* 주소)
    uintptr_t argv_base = (uintptr_t)v;
    int first = 1;

    *offset += sprintf(out + *offset, "[");

    for (size_t idx = 0; idx < 128; idx++) {
        struct iovec local[1];
        struct iovec remote[1];

        // 1) argv[idx] 포인터값 읽기
        elem = 0;
        local[0].iov_base = &elem;
        local[0].iov_len = sizeof(elem);
        remote[0].iov_base = (void *)(argv_base + idx * sizeof(uintptr_t));
        remote[0].iov_len = sizeof(elem);

        ssize_t n = process_vm_readv(pid_temp, local, 1, remote, 1, 0);
        if (n != (ssize_t)sizeof(elem)) break;
        if (elem == 0) break; // NULL 종단

        // 2) elem이 가리키는 문자열 읽기
        memset(buf, 0, sizeof(buf));
        struct iovec local2[1];
        struct iovec remote2[1];
        local2[0].iov_base = buf;
        local2[0].iov_len = sizeof(buf) - 1;
        remote2[0].iov_base = (void *)elem;
        remote2[0].iov_len = sizeof(buf) - 1;

        n = process_vm_readv(pid_temp, local2, 1, remote2, 1, 0);
        if (n < 0) break;
        buf[sizeof(buf) - 1] = '\0';

        if (!first) *offset += sprintf(out + *offset, ", ");
        first = 0;
        *offset += sprintf(out + *offset, "\"%s\"", buf);
    }

    *offset += sprintf(out + *offset, "]");
}

typedef void (*arg_fmt_fn)(unsigned long long v, char *out, const int *type, int *offset, int i, t_syscall_args args);

static arg_fmt_fn g_fmt[] = {
	[ARG_FD] = fmt_int,
	[ARG_STR] = fmt_str,
	[ARG_VSTR] = fmt_vstr,
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
	if (argc < 2) {
		fprintf(stderr, "Usage: strace <program>\n");
		return 1;
	}

	struct stat st;
	int executable = 0;
	if (lstat(argv[1], &st) == -1) {
		fprintf(stderr, "stat error\n");
		return 1;
	}
	if (st.st_mode & S_IXUSR) {
		executable = 1;
	} else if (st.st_mode & S_IXGRP) {
		executable = 1;
	} else if (st.st_mode & S_IXOTH) {
		executable = 1;
	}
	if (executable == 0) {
		fprintf(stderr, "strace: is not executable\n");
		return 1;
	}

	pid_t child = fork();
	pid_temp = child;

	if (child == 0) {
		raise(SIGSTOP);
		execvp(argv[1], &argv[1]);
		exit(1);
	}
	static int flag = 0;
	signal(SIGINT,  handler);
	signal(SIGTERM, handler);
	signal(SIGHUP,  handler);
	int status;
	waitpid(child, &status,  WUNTRACED);
	ptrace(PTRACE_SEIZE, child, NULL, PTRACE_O_TRACESYSGOOD | PTRACE_O_EXITKILL);
	ptrace(PTRACE_INTERRUPT, child, NULL, NULL);
	waitpid(child, &status, 0);
	int in_syscall = 0;
	while (1) {
		ptrace(PTRACE_SYSCALL, child, NULL, NULL);
		waitpid(child, &status, 0);

		if (WIFEXITED(status) || WIFSIGNALED(status)) break;

		if (WIFSTOPPED(status) && WSTOPSIG(status) == (SIGTRAP | 0x80)) {
			u_user_regs_struct regs;
			struct iovec iov;
			iov.iov_base = &regs;
			iov.iov_len = sizeof(regs);
			t_syscall_args args;
			memset(&args, 0, sizeof(args));
			ptrace(PTRACE_GETREGSET, child, NT_PRSTATUS, &iov);
			if (iov.iov_len == sizeof(struct user_regs_struct64)) {
				args.a0 = regs.regs64.rdi;
				args.a1 = regs.regs64.rsi;
				args.a2 = regs.regs64.rdx;
				args.a3 = regs.regs64.r10;
				args.a4 = regs.regs64.r8;
				args.a5 = regs.regs64.r9;
				args.orig_ax = regs.regs64.orig_rax;
				args.rax = regs.regs64.rax;
			}
			else {
				flag += 1;
				args.a0 = regs.regs32.ebx;
				args.a1 = regs.regs32.ecx;
				args.a2 = regs.regs32.edx;
				args.a3 = regs.regs32.esi;
				args.a4 = regs.regs32.edi;
				args.a5 = regs.regs32.ebp;
				args.orig_ax = regs.regs32.orig_eax;
				args.rax = regs.regs32.eax;
			}
			//rdi , rsi , rdx , r10 , r8 , r9

			if (!in_syscall) {
				int offset = 0;
				char buf[4095];
				memset(buf, 0, sizeof(buf));
				const t_SYS_TABLE *temp = (flag == 0)
				? (const t_SYS_TABLE *)&get_SYS64_TABLE[args.orig_ax]
				: (const t_SYS_TABLE *)&get_SYS32_TABLE[args.orig_ax];
				offset += sprintf(buf, "%s(", temp->name);
				for (int i = 0; i < temp->argCount; i++) {
					arg_fmt_fn fn = g_fmt[temp->argType[i]];
					switch (i) {
						case 0:
							fn(args.a0, buf, temp->argType, &offset, i, args);
						break;
						case 1:
							fn(args.a1, buf, temp->argType, &offset, i, args);
						break;
						case 2:
							fn(args.a2, buf, temp->argType, &offset, i, args);
						break;
						case 3:
							fn(args.a3, buf, temp->argType, &offset, i, args);
						break;
						case 4:
							fn(args.a4, buf, temp->argType, &offset, i, args);
						break;
						case 5:
							fn(args.a5, buf, temp->argType, &offset, i, args);
						break;
					}
					if ((i + 1) < temp->argCount) {
						offset += sprintf(buf + offset, ", ");
					}
				}
				sprintf(buf + offset, ")");
				fprintf(stderr, "%s", buf);
				in_syscall = 1;
			} else {
				if ((long long)args.rax < 0 && (long long)args.rax > -4096){
					int err = (int)(-(long long)args.rax);
					fprintf(stderr, " = -1 %s\n", strerror(err));
				}
				else {
					fprintf(stderr, " = 0x%llx\n", (long long)args.rax);
				}
				in_syscall = 0;
			}
			if (flag == 1){
				fprintf(stderr, "[ Process PID=%d runs in 32 bit mode. ]\n", child);
			}
		} else if (WIFSTOPPED(status)) {
			siginfo_t siginfo;
			int sig = WSTOPSIG(status);
			if (status  >> 16 != 0){
				continue;
			}
			ptrace(PTRACE_GETSIGINFO, child, NULL, &siginfo);
			fprintf(stderr, "--- %s {si_signo=%s, si_code=%d, si_pid=%d, si_uid=%d} ---\n", sigabbrev_np(sig), sigabbrev_np(siginfo.si_signo), siginfo.si_code, siginfo.si_pid, siginfo.si_uid);
			ptrace(PTRACE_SYSCALL, child, NULL, sig);
		}
	}
	if (WIFEXITED(status)) {
		if (in_syscall) fprintf(stderr, " = ?\n");
		fprintf(stderr, "+++ exited with %d +++\n", WEXITSTATUS(status));
	} else if (WIFSIGNALED(status)) {
		if (in_syscall) fprintf(stderr, " = ?\n");
		fprintf(stderr, "+++ killed by SIG%s +++\n", sigabbrev_np(WTERMSIG(status)));
	}
	return 0;
}

/*void fmt_vstr(unsigned long long v, char *out, const int *type, int *offset, int i, struct user_regs_struct regs){
	(void)i;
	(void)regs;
	(void)type;
	char buf[4095];
	void *temp = 0;
	*offset += sprintf(out + *offset, "[");
	memset(buf, 0, sizeof(buf));
	struct iovec local[1];
	struct iovec remote[1];
	local[0].iov_base = &temp;
	local[0].iov_len = sizeof(void *);
	remote[0].iov_base = (void *)v;
	remote[0].iov_len = sizeof(void *);
	process_vm_readv(pid_temp, local, 1, remote, 1, 0);
	while (temp != NULL) {
		memset(buf, 0, sizeof(buf));
		struct iovec local2[1];
		struct iovec remote2[1];
		local2[0].iov_base = buf;
		local2[0].iov_len = sizeof(buf);
		remote2[0].iov_base = temp;
		remote2[0].iov_len = 8;
		process_vm_readv(pid_temp, local2, 1, remote2, 1, 0);
		*offset += sprintf(out + *offset, "\"%s\"", buf);
		temp++;
		if (temp != NULL) {
			*offset += sprintf(out + *offset, ", ");
		}
	}
	*offset += sprintf(out + *offset, "]");
};*/