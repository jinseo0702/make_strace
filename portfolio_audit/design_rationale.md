# ft_strace 설계 의도와 근거 구분

## 문서 목적

이 문서는 Checkpoint B에서 받은 사용자 답변을 코드 및 실행 증거와 결합하되, 다음 세 종류의 정보를 명시적으로 분리한다.

- **Verified from code/test**: 저장소 소스나 보존된 실행 결과로 확인한 사실
- **User-provided design rationale**: 구현자가 직접 설명한 동기, 제약, 의도, 회고
- **Inference**: 코드 구조와 사용자 설명을 함께 보고 내린 해석이며 측정된 사실은 아님

기준 commit은 `5a59c386c69332bd2dacc5824bf2a8958c9d9037`이다.

## Verified from code/test

| 확인된 사실 | 근거 |
|---|---|
| 실행할 프로그램을 `fork`한 뒤 자식이 `SIGSTOP`하고, 부모가 `PTRACE_SEIZE`로 그 자식을 추적한다. | `ft_strace.c:233-249` |
| `PTRACE_SYSCALL` stop마다 `PTRACE_GETREGSET`으로 register를 읽고 하나의 `in_syscall` 상태를 토글해 entry/exit를 구분한다. | `ft_strace.c:250-350` |
| x86-64와 i386용 syscall metadata는 두 X-macro 목록에서 enum과 sparse designated-initializer table로 생성된다. | `include/strace_data.h:4-797`, `include/strace_data.h:824-864` |
| table에는 x86-64 365개와 i386 426개의 populated ABI row가 있다. 합계는 791개 ABI row이며, 두 ABI를 합친 출력 이름은 421개로 중복 제거된다. | `syscall_matrix.md`, `tools/generate_syscall_matrix.py` |
| 17개 argument tag가 7개 공통 formatter 함수로 dispatch된다. syscall별 전용 decoder나 syscall 이름별 분기는 없다. | `ft_strace.c:45-207`, `ft_strace.c:293-338` |
| 문자열과 argv vector는 `process_vm_readv`로 tracee memory에서 읽는다. | `ft_strace.c:83-185` |
| i386 register/table 경로가 있으며 smoke test에서 32-bit mode와 `getpid` 추적은 동작했다. 같은 test에서 음수 errno 해석은 실패했다. | `ft_strace.c:266-285`, `raw/cases/t15_i386_smoke/`, `test_results.md` |
| tracer는 한 PID와 한 개의 syscall 상태만 관리하고 descendant trace option을 설정하지 않는다. | `ft_strace.c:233-250`, `ft_strace.c:251-366` |
| 점진적인 ptrace 예제 3개와 별도의 playground 프로그램이 저장소에 존재한다. | `Test/ptrace_tutorial/`, `Test/playground/` |
| GNU strace 6.19와 비교한 15개 회귀 사례의 결과는 PASS 5, PARTIAL 3, FAIL 7, CRASH 0이다. | `test_results.json`, `test_results.md` |

`populated ABI row`는 번호 lookup으로 이름과 generic metadata를 찾을 수 있다는 뜻이다. syscall 의미 전체를 정확히 decode한다는 뜻이 아니며, 전체 table의 fully decoded syscall 수는 **확인 불가**이다.

## User-provided design rationale

아래 내용은 Checkpoint B에서 구현자가 제공한 설명이다. 코드로 측정한 결과가 아니라 동기와 설계 배경으로 기록한다.

### 프로젝트 동기

시스템 프로그램을 개발하고 시험할 때 사용하던 strace의 내부 동작을 이해하고 싶었다. syscall 흐름을 관찰하면 프로세스가 무엇을 하는지 추론하고 성능 문제나 memory 관련 이상을 조사하는 출발점이 될 수 있다고 보았다. 따라서 tracer를 직접 만들면서 syscall, register, tracee memory, 프로세스 실행 흐름을 이해하는 것을 목표로 했다.

이 설명에서 성능 최적화와 memory leak 분석은 프로젝트를 시작한 관심사다. 이 baseline에서는 성능 benchmark나 memory leak 검출 능력을 측정하지 않았다.

### 외부 제약

42 과제 요구사항이 `PTRACE_SEIZE`를 사용해 strace 형태의 프로그램을 만드는 것이었다.

### table-driven 구조를 선택한 이유

syscall마다 유사한 코드를 반복해서 작성하기보다 공통 구조를 찾고 싶었다. 번호로 index할 수 있는 syscall table을 확인한 뒤, lookup table과 X-macro를 이용해 metadata 정의를 한곳에 모으고 반복적인 선언 생성을 전처리기에 맡기는 방식을 선택했다. argument type에 따른 공통 formatter dispatch도 같은 방향의 선택이었다.

### 의도한 ABI와 process 범위

i386은 x86-64와 같은 기능 수준을 목표로 했고, process 범위는 처음부터 단일 자식 프로세스로 구상했다.

이는 구현 의도에 대한 설명이다. 실제 baseline은 i386 기능 동등성을 입증하지 않았으며, 음수 errno 처리에서 차이를 확인했다. 단일 자식만 추적하는 동작은 소스와 test에서 확인됐다.

### 난점과 본인의 핵심 기여

가장 어려운 부분은 코드의 양보다 먼저 무엇을 알아야 하는지 파악하는 과정이었다. ptrace stop 흐름, register 사용 규약, 다른 프로세스 memory의 해석, GNU/Linux가 제공하는 함수와 interface를 조사했고, 작은 tutorial 및 dummy code를 작성해 각 동작을 분리해서 확인했다고 설명했다. 본인의 핵심 기여도 이 조사와 반복 실험을 통해 전체 설계에 필요한 지식의 경계를 찾아간 과정이라고 평가했다.

## Inference

| 추론 | 근거와 한계 |
|---|---|
| X-macro 구조는 syscall 식별자와 lookup table이 동일한 metadata row를 재사용하게 하므로 서로 다른 mapping을 별도로 유지하는 중복을 줄인다. | enum과 table이 같은 `SYS64_LIST`/`SYS32_LIST`에서 생성되는 구조로부터의 추론이다. 실제 유지보수 시간 감소는 측정하지 않았다. |
| formatter function table은 syscall별 argument-format 분기를 만들지 않고 type tag별 공통 경로를 재사용하려는 의도와 일치한다. | `g_fmt[tag]` dispatch는 확인되지만 argument 위치 선택용 `switch`는 남아 있다. 따라서 "모든 분기를 제거했다"고 표현할 수 없다. |
| 단일 PID와 단일 `in_syscall` 상태는 구현자가 밝힌 단일 자식 범위에는 맞지만, multi-process tracing으로 확장하려면 PID/TID별 상태가 필요하다. | 현재 구조와 `clone` 비교 test에서의 descendant 누락에 기반한 설계 추론이다. |
| 저장소의 단계별 tutorial과 playground 파일은 작은 실험으로 지식을 확인했다는 사용자 회고와 부합한다. | 파일의 존재와 내용은 확인했지만 학습 난이도와 개인 기여도의 크기는 구현자 설명에 의존한다. |

## 포트폴리오 주장 경계

| 사용하지 않는 표현 | 근거에 맞는 표현 |
|---|---|
| `791개 syscall을 완전히 지원했다` | `x86-64 365개와 i386 426개의 syscall metadata row를 lookup한다` |
| `코드를 최적화했다` | `반복적인 metadata 선언과 syscall별 formatter 작성을 줄이는 table-driven 구조를 선택했다` |
| `분기문을 없앴다` | `argument type을 function table로 dispatch해 syscall별 전용 분기를 두지 않았다` |
| `i386을 완전히 지원한다` | `i386 register/table 경로를 구현했으며 smoke test에서 mode 진입과 getpid는 동작했지만 음수 errno 해석 한계가 확인됐다` |
| `성능과 memory leak을 개선했다` | `syscall trace가 프로세스 동작과 성능 문제를 조사하는 데 어떻게 쓰이는지 이해하려고 시작했다` |
| `GNU strace와 동일하다` | `GNU strace 6.19를 reference로 15개 사례를 semantic 비교했다` |

