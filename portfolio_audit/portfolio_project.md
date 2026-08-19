# ft_strace 포트폴리오 프로젝트 설명

## 한 줄

42 과제 요구사항인 `PTRACE_SEIZE`로 단일 tracee의 Linux syscall을 추적하고, X-macro 기반 x86-64/i386 metadata와 공통 formatter dispatch를 적용한 뒤 GNU strace 6.19 대비 15개 회귀 사례로 실제 동작 범위와 한계를 검증한 프로젝트입니다.

## Problem

시스템 프로그램을 개발하고 시험하면서 사용하던 strace가 프로세스를 어떻게 관찰하는지 직접 이해하고 싶었습니다. 사용자 영역의 프로그램이 kernel과 상호작용하는 syscall 경계를 추적하면 실행 흐름과 오류 원인을 추론할 수 있다고 보았고, 단순히 도구 사용법을 익히는 대신 tracer를 구현하면서 ptrace stop, ABI별 register convention, tracee memory 해석을 학습하는 것을 목표로 삼았습니다.

성능 문제와 memory 관련 이상을 조사할 가능성은 프로젝트의 출발 동기였지만, 이 프로젝트에서 성능 개선이나 memory leak 검출 성능을 측정하지는 않았습니다.

## Implementation

자식 process를 `fork`하고 `SIGSTOP`으로 동기화한 뒤, 부모가 `PTRACE_SEIZE`와 `PTRACE_SYSCALL`을 사용해 syscall stop을 반복 처리하도록 구성했습니다. 각 stop에서는 `PTRACE_GETREGSET`으로 x86-64 또는 i386 register를 읽고, entry에서 syscall 번호와 argument를 출력한 뒤 exit에서 공통 return path로 결과를 출력합니다.

syscall마다 별도 decoder를 반복 작성하는 대신 다음과 같은 table-driven 구조를 사용했습니다.

- x86-64와 i386의 syscall 번호, 이름, argument 개수, type tag를 X-macro row로 정의했습니다.
- 같은 row에서 enum과 sparse lookup table을 생성했습니다.
- 17개 argument tag를 7개 formatter 함수로 dispatch했습니다.
- 문자열과 `argv`는 `process_vm_readv`로 tracee memory에서 읽었습니다.
- table에 없는 번호는 `syscall_N(/* unknown */)` 형태로 처리했습니다.

현재 metadata에는 x86-64 365개와 i386 426개의 populated ABI row가 있습니다. 이는 이름과 generic argument metadata의 lookup 범위이며, 791개 row 전체의 semantic decode를 뜻하지 않습니다.

## Engineering Decision

첫째, `PTRACE_SEIZE`는 42 과제의 명시적 제약이었습니다. tracee가 스스로 `PTRACE_TRACEME`를 호출하는 구조 대신 부모가 정지된 자식을 seize하고, `TRACESYSGOOD`로 일반 signal stop과 syscall stop을 구분하는 흐름을 구성했습니다.

둘째, syscall별로 유사한 switch와 출력 코드를 반복하지 않기 위해 X-macro, sparse lookup table, argument-type function dispatch를 선택했습니다. 이 구조는 enum과 lookup metadata가 같은 row를 공유하고 새로운 metadata가 공통 출력 경로를 재사용하게 합니다. 다만 유지보수 시간이나 runtime 성능 개선은 별도로 측정하지 않았으므로 이를 "최적화" 결과로 주장하지 않습니다.

추적 범위는 의도적으로 단일 자식 process로 한정했습니다. i386은 x86-64와 같은 기능 수준을 목표로 별도 register mapping과 table을 구현했지만, baseline 결과는 두 ABI의 기능 동등성을 입증하지 않았습니다.

## Verification

기준 commit `5a59c386c69332bd2dacc5824bf2a8958c9d9037`을 Ubuntu 26.04, Linux 7.0.0-29-generic, x86_64, gcc 15.2.0 환경에서 build했습니다. 서로 다른 범주의 syscall을 포함하는 deterministic case 15개를 만들고, 동일한 program을 ft_strace와 GNU strace 6.19로 각각 실행했습니다.

전체 문자열을 그대로 diff하지 않고 syscall name, 핵심 argument, return value, errno, sequence를 비교했습니다. PID, address, decimal/hex 표현, symbolic flag와 같은 정상적인 차이는 case별 규칙으로 정규화했습니다. 14개 case는 x86-64 executable, 1개 case는 freestanding i386 executable을 사용했습니다. 각 회귀 case의 ft_strace/GNU strace 실행 명령, stdout/stderr, exit status와 판정 입력은 `raw/`, `test_results.json`, `test_results.md`에 보존했습니다.

기존 source는 변경하지 않았고, 측정 전후 다섯 개 기준 파일(`ft_strace.c`, 두 header, `Makefile`, `README.md`)의 SHA-256이 동일함을 확인했습니다.

## Result

```text
Recognized syscall metadata:
  x86-64: 365 / 470 table slots
  i386:   426 / 470 table slots
  Total:  791 ABI rows
  Unique printed names across both ABIs: 421

Fully decoded syscalls across the entire table:
  확인 불가

Regression tests: 15
PASS:     5
PARTIAL:  3
FAIL:     7
CRASH:    0
```

PASS 사례에서는 binary `write`, `openat`/`close`, `mmap` → `mprotect` → `munmap`, `getpid`, unknown syscall의 핵심 의미가 GNU strace와 일치했습니다. `execve`는 path와 argv, process image가 교체된 뒤에도 계속된 추적, exit 23 출력까지 동작했지만 tracer process가 23이 아닌 0을 반환해 전체 case는 FAIL로 분류했습니다.

실패 결과는 단순 합계에 그치지 않고 원인까지 연결했습니다. `read` buffer를 syscall entry에서 읽어 kernel이 채우기 전의 `XXXX`를 출력했고, 64-bit `lseek` offset `4294967298`을 `int` formatter가 `2`로 축소했습니다. i386에서는 `-EFAULT`가 sign extension 없이 `0xfffffff2`로 출력됐습니다. 15개 사례에서 ft_strace나 tracee가 crash한 경우는 없었습니다.

## Limitation

- 모든 argument가 entry에서 출력되므로 `read`, stat 구조체, descriptor array처럼 kernel이 채우는 output data를 exit에서 decode하지 못합니다.
- flag, mode, signal, structure와 syscall별 return type을 symbolic하게 해석하지 않고 generic 숫자 또는 pointer로 출력합니다.
- 일부 size/offset type이 `int`로 좁혀지고, i386 음수 errno 처리에 오류가 있습니다.
- 단일 tracee만 관리하므로 `fork`/`vfork`/`clone` descendant의 syscall을 따라가지 않습니다. 이는 의도한 초기 범위이면서 현재 기능 한계입니다.
- tracee의 종료 상태를 출력하지만 tracer process의 exit status로 전달하지 않습니다.
- 전체 791개 ABI row를 실행하지 않았으므로 fully decoded syscall 수와 전체 안정성은 **확인 불가**입니다.
- 성능 benchmark와 memory leak 검출 test를 수행하지 않았으므로 성능 향상 또는 memory leak 분석 성과를 주장하지 않습니다.
