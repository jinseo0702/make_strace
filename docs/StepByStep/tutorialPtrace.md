## ptrace_scope=1 에 대해 먼저

`ptrace_scope=1`은 `PTRACE_ATTACH`(실행 중인 임의 프로세스에 붙는 것)만 제한해. 우리가 만들 strace처럼 **직접 fork한 자식**을 추적하는 방식(`PTRACE_TRACEME`)은 전혀 제한 없이 동작하니까 걱정하지 않아도 돼.

***

## 핵심 구조 이해

strace의 동작 흐름은 단순해:

1. 부모(tracer)가 `fork()`
2. 자식(tracee)이 `PTRACE_TRACEME` 호출 → "나를 추적해"라고 커널에 등록
3. 자식이 `execvp()` 호출 → 커널이 자동으로 `SIGTRAP` 발생시켜 자식을 멈춤
4. 부모가 `waitpid()`로 깨어나서 제어권 획득
5. `PTRACE_SYSCALL`로 루프 돌며 시스템 콜마다 멈추게 함
6. `PTRACE_GETREGS`로 레지스터 읽어서 시스템 콜 번호/인자/반환값 출력

***

## Step 1 — fork + PTRACE_TRACEME

가장 기본. 자식이 멈추는 걸 확인하고 그냥 재개시키는 것만.

```c
// step1_basic.c
#include <stdio.h>
#include <stdlib.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc < 2) { fprintf(stderr, "Usage: %s <prog> [args...]\n", argv[0]); return 1; }

    pid_t child = fork();
    if (child == 0) {
        // 자식: 내 부모가 나를 추적하게 커널에 등록
        ptrace(PTRACE_TRACEME, 0, NULL, NULL);
        // execvp 호출 시 커널이 SIGTRAP 발생시켜 여기서 멈춤
        execvp(argv[1], &argv[1]);
        perror("execvp");
        exit(1);
    }

    int status;
    waitpid(child, &status, 0);
    // exec 직후의 첫 번째 stop
    printf("[tracer] child stopped, signal=%d\n", WSTOPSIG(status));

    // 그냥 자유롭게 실행 재개 (아직 syscall 추적 없음)
    ptrace(PTRACE_CONT, child, NULL, NULL);
    waitpid(child, &status, 0);
    printf("[tracer] child exited: %d\n", WEXITSTATUS(status));
    return 0;
}
```

```
$ gcc step1_basic.c -o step1 && ./step1 /bin/ls
[tracer] child stopped, signal=5    ← SIGTRAP(5), exec 직후 자동 stop
[tracer] child exited: 0
```

***

## Step 2 — PTRACE_SYSCALL 루프

이제 시스템 콜마다 멈추게 해서 개수를 세보자.

```c
// step2_count.c
#include <stdio.h>
#include <stdlib.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <unistd.h>
#include <signal.h>

int main(int argc, char *argv[]) {
    if (argc < 2) return 1;

    pid_t child = fork();
    if (child == 0) {
        ptrace(PTRACE_TRACEME, 0, NULL, NULL);
        execvp(argv[1], &argv[1]);
        exit(1);
    }

    int status;
    waitpid(child, &status, 0); // exec 직후 첫 stop 소비

    // TRACESYSGOOD: syscall-stop 시 signal에 0x80 비트 추가
    // → 일반 SIGTRAP(5)와 syscall-stop(5|0x80 = 133)을 구분 가능
    ptrace(PTRACE_SETOPTIONS, child, NULL, PTRACE_O_TRACESYSGOOD);

    long count = 0;
    while (1) {
        // 다음 syscall entry 또는 exit에서 stop
        ptrace(PTRACE_SYSCALL, child, NULL, NULL);
        waitpid(child, &status, 0);

        if (WIFEXITED(status) || WIFSIGNALED(status)) break;

        if (WIFSTOPPED(status) && WSTOPSIG(status) == (SIGTRAP | 0x80))
            count++;
    }
    // entry + exit = 2번씩 stop하므로 /2
    printf("syscall count: %ld\n", count / 2);
    return 0;
}
```

핵심: `PTRACE_SYSCALL`은 **syscall 진입(entry)** 과 **syscall 반환(exit)** 두 번 모두 stop시킨다. 그래서 실제 syscall 횟수는 `count / 2`.

***

## Step 3 — 레지스터 읽기 (syscall 번호 + 반환값)

x86-64에서 syscall 레지스터 규칙:

| 시점 | `orig_rax` | `rax` | `rdi~r9` |
|---|---|---|---|
| entry | syscall 번호 | syscall 번호 | 인자 1~6 |
| exit | syscall 번호 | **반환값** | 인자 1~6 |

`orig_rax`는 entry/exit 모두에서 syscall 번호를 보존해줘서 exit 시점에 "이게 어떤 syscall이었나"를 알 수 있어.

```c
// step3_regs.c
#include <stdio.h>
#include <stdlib.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <sys/user.h>   // struct user_regs_struct
#include <unistd.h>

int main(int argc, char *argv[]) {
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

    int in_syscall = 0; // 0=entry 대기, 1=exit 대기

    while (1) {
        ptrace(PTRACE_SYSCALL, child, NULL, NULL);
        waitpid(child, &status, 0);

        if (WIFEXITED(status) || WIFSIGNALED(status)) break;

        if (WIFSTOPPED(status) && WSTOPSIG(status) == (SIGTRAP | 0x80)) {
            struct user_regs_struct regs;
            ptrace(PTRACE_GETREGS, child, NULL, &regs);

            if (!in_syscall) {
                // Entry: syscall 번호와 처음 3개 인자 출력
                printf("syscall(%lld, 0x%llx, 0x%llx, 0x%llx)",
                    (long long)regs.orig_rax,
                    (long long)regs.rdi,
                    (long long)regs.rsi,
                    (long long)regs.rdx);
                in_syscall = 1;
            } else {
                // Exit: 반환값 출력
                printf(" = %lld\n", (long long)regs.rax);
                in_syscall = 0;
            }
        }
    }
    return 0;
}
```

```
$ ./step3 /bin/true
syscall(12, 0x0, 0x0, 0x0) = 94136...   ← brk
syscall(21, 0x7f..., 0x4, 0x0) = 0       ← access
...
```

***

## Step 4 — Syscall 이름 + 문자열 인자 읽기

### 이름 테이블

`/usr/include/asm/unistd_64.h`의 번호를 참고해서 테이블 만들면 돼:

```c
// syscall_names.h
static const char *g_syscall_names[] = {
    [0]   = "read",
    [1]   = "write",
    [2]   = "open",
    [3]   = "close",
    [4]   = "stat",
    [5]   = "fstat",
    [9]   = "mmap",
    [10]  = "mprotect",
    [11]  = "munmap",
    [12]  = "brk",
    [21]  = "access",
    [59]  = "execve",
    [60]  = "exit",
    [231] = "exit_group",
    // ...
};
#define SYSCALL_MAX 336

const char *syscall_name(long n) {
    if (n >= 0 && n < SYSCALL_MAX && g_syscall_names[n])
        return g_syscall_names[n];
    return "unknown";
}
```

### 문자열 인자 읽기 (PTRACE_PEEKDATA)

`rdi`에 `char *` 포인터가 담겨 있을 때, 자식 메모리에서 실제 문자열을 읽으려면 `PTRACE_PEEKDATA`를 써야 해. 이건 **word(8바이트) 단위**로만 읽을 수 있어.

```c
#include <errno.h>
#include <string.h>

void read_string(pid_t child, unsigned long addr, char *buf, size_t max) {
    size_t i = 0;
    while (i < max - 1) {
        errno = 0;
        long word = ptrace(PTRACE_PEEKDATA, child, (void *)(addr + i), NULL);
        if (errno) break; // 읽기 실패 (예: 잘못된 포인터)

        char *bytes = (char *)&word;
        for (int j = 0; j < (int)sizeof(long); j++) {
            buf[i++] = bytes[j];
            if (bytes[j] == '\0') return; // null terminator 발견
            if (i >= max - 1) { buf[i] = '\0'; return; }
        }
    }
    buf[i] = '\0';
}
```

이걸 entry 시점에서 `write(1, "hello", 5)` 같은 syscall의 두 번째 인자(`rsi`)를 읽을 때 쓰면 돼:

```c
if (regs.orig_rax == 1) { // write
    char buf[256];
    read_string(child, regs.rsi, buf, sizeof(buf));
    printf("write(%lld, \"%s\", %lld)",
        (long long)regs.rdi, buf, (long long)regs.rdx);
}
```

***

## 전체 빌드 방향 요약

지금까지 만든 것들을 조립하면 mini strace가 돼:

```
fork/exec + PTRACE_TRACEME
    ↓
PTRACE_SYSCALL 루프
    ↓
PTRACE_GETREGS → orig_rax (syscall 번호)
    ↓
entry: 이름 + 인자 출력 (PTRACE_PEEKDATA로 문자열 읽기)
exit:  "= 반환값" 출력
```

다음 단계로 넘어가면 다룰 것들:
- `PTRACE_PEEKDATA` 대신 `process_vm_readv` (더 빠름, 큰 버퍼에 유리)
- signal 처리 (`WIFSTOPPED`에서 시스템 콜 stop이 아닌 경우 signal 포워딩)
- `PTRACE_O_TRACEEXEC`로 exec 이벤트 처리
- 각 syscall별 인자 타입 정보 (숫자 vs 포인터 vs 플래그) → 이건 실제 strace도 하드코딩 테이블임