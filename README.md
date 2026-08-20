# ft_strace

Linux process가 만드는 system call을 관찰하는 원리를 이해하기 위해 구현한
학습용 tracer입니다. 추적할 프로그램을 자식으로 실행하고 `ptrace` stop마다
x86-64/i386 register를 읽어 syscall entry, argument, return을 출력합니다.

## 만든 이유

시스템 프로그램을 시험할 때 사용하던 `strace`가 process의 행동을 어떻게
보여 주는지 내부에서부터 이해하고 싶었습니다. 42 과제의 `PTRACE_SEIZE` 제약을
출발점으로, ptrace stop 흐름, ABI register 규약, 다른 process의 memory 읽기를
작은 tutorial과 dummy program으로 나누어 확인한 뒤 하나의 tracer로 연결했습니다.

## 핵심 기능

- `fork`/`execvp`로 시작한 단일 tracee 추적과 인자 전달
- `PTRACE_SEIZE`, `PTRACE_SYSCALL`, `PTRACE_O_TRACESYSGOOD` 기반 stop 처리
- `PTRACE_GETREGSET` 결과 길이에 따른 x86-64/i386 register 해석
- syscall 번호를 sparse table에서 찾아 이름, argument 수, type tag 조회
- `process_vm_readv`를 이용한 C string과 argv vector 읽기
- 17개 argument tag를 7개 공통 formatter로 dispatch
- 알 수 없는 번호의 `syscall_N(/* unknown */)` fallback
- tracee의 정상 종료·signal 종료와 제한된 signal stop 출력

metadata table에는 x86-64 365개, i386 426개의 populated row가 있습니다. 이는
번호로 syscall 이름과 generic metadata를 lookup할 수 있는 범위이며, 그 수만큼의
syscall 의미를 완전히 decode한다는 뜻은 아닙니다.

## 동작 구조

```text
ft_strace <program> [args...]
  -> fork -> child SIGSTOP -> execvp
  -> parent PTRACE_SEIZE + PTRACE_SYSCALL
  -> waitpid -> GETREGSET -> ABI/table 선택
  -> entry: argument formatting
  -> exit: generic return/errno formatting
  -> tracee 종료 상태 출력
```

실행과 stop loop는 `ft_strace.c`, ABI register layout은 `include/user.h`, 두 ABI의
syscall 정의와 sparse table은 `include/strace_data.h`에 있습니다.

## 설계하면서 고민한 점

- syscall별 enum과 lookup table을 따로 반복하지 않도록 같은 X-macro row에서
  두 구조를 생성했습니다.
- syscall마다 decoder 함수를 만드는 대신 argument type별 formatter를 공유해
  반복 코드를 줄였습니다. flags, mode, signal, structure는 아직 주로 숫자나
  address로 표시됩니다.
- 원래 process 범위는 단일 자식이었고 i386도 x86-64와 같은 기능 수준을
  목표로 했습니다. 현재 구현은 PID별 상태를 갖지 않으며 i386 동등성도
  실행 검증에서 확인되지 않았습니다.
- entry/exit는 하나의 `in_syscall` boolean을 토글해 구분합니다. 구조는 단순하지만
  entry argument를 보존하지 않아 kernel이 채우는 output buffer를 exit에서
  다시 해석할 수 없습니다.

## Build

```sh
make
```

기본 target은 GCC로 루트의 `ft_strace`를 생성합니다. GNU/Linux 환경이 필요합니다.

## Run

```sh
./ft_strace /bin/echo hello
./ft_strace ./my_program arg1 arg2
```

현재 구현은 실행 전 `lstat(argv[1])`으로 경로와 실행 bit를 확인하므로 `PATH`에서만
찾을 수 있는 명령보다 `/bin/echo` 같은 명시적 경로를 사용해야 합니다. 실행에는
local child에 대한 `ptrace`가 허용된 환경이 필요합니다.

## 검증 결과

| 범위 | 결과 |
|---|---|
| 비교 기준 | GNU strace 6.19 |
| regression cases | 15 |
| 결과 | PASS 5 · PARTIAL 3 · FAIL 7 · CRASH 0 |
| 대표 관찰 | t03 `read()`가 kernel이 쓴 `READ` 대신 entry 시점의 `XXXX` 출력 |

binary `write`, `openat`/`close`, `mmap`/`mprotect`/`munmap`, `getpid`, unknown
syscall 사례에서는 핵심 의미가 비교 기준과 맞았습니다. 전체 table의 fully decoded
syscall 수는 이 audit으로 확인할 수 없습니다.

전체 결과: [`portfolio_audit/test_results.md`](portfolio_audit/test_results.md)

## 확인된 한계

- t03처럼 kernel이 채우는 output buffer를 syscall entry에서 읽어 이전 값을
  출력합니다. exit 시점 decoder와 저장된 entry state가 없습니다.
- t15 i386 경로는 mode와 `getpid`를 인식했지만, 32-bit 음수 errno `-EFAULT`를
  sign extension하지 않아 성공값 `0xfffffff2`처럼 표시했습니다.
- t11의 descendant syscall은 추적하지 않으며, t14에서는 tracee의 exit 7을
  출력하고도 `ft_strace` process 자체는 0을 반환했습니다.

## 상세 문서

- [Audit 개요](portfolio_audit/README.md)
- [Architecture](portfolio_audit/architecture.md)
- [기능 범위](portfolio_audit/feature_inventory.md)
- [Syscall metadata matrix](portfolio_audit/syscall_matrix.md)
- [Failure 분석](portfolio_audit/failures.md)
- [설계 근거와 주장 경계](portfolio_audit/design_rationale.md)
