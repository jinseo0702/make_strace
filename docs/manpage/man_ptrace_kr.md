PTRACE(2) Linux 프로그래머 매뉴얼 PTRACE(2) 

### 이름 (NAME)

ptrace - 프로세스 추적 (process trace) 

### 시놉시스 (SYNOPSIS)

```c
#include <sys/ptrace.h>

long ptrace(enum __ptrace_request request, pid_t pid, void *addr, void *data);
```

### 설명 (DESCRIPTION)

ptrace() 시스템 호출은 한 프로세스("추적자" (tracer))가 다른 프로세스("피추적자" (tracee))의 실행을 관찰 및 제어하고, 피추적자의 메모리와 레지스터를 조사 및 변경할 수 있는 수단을 제공한다. 이는 주로 중단점 디버깅 (breakpoint debugging) 및 시스템 호출 추적 (system call tracing)을 구현하는 데 사용된다.

피추적자는 먼저 추적자에게 부착(attach)되어야 한다. 부착 및 이후의 명령은 스레드별로 이루어진다: 다중 스레드 프로세스에서, 모든 스레드는 개별적으로 (잠재적으로 다른) 추적자에게 부착되거나, 부착되지 않은 상태로 남아 디버깅되지 않을 수 있다. 따라서, "피추적자" (tracee)는 항상 "(하나의) 스레드"를 의미하며, 결코 "(다중 스레드일 수 있는) 프로세스"를 의미하지 않는다. Ptrace 명령은 항상 다음과 같은 형태의 호출을 사용하여 특정 피추적자에게 전송된다:

`ptrace(PTRACE_foo, pid, ...)`

여기서 pid는 해당 리눅스 스레드의 스레드 ID이다. (이 페이지에서 "다중 스레드 프로세스"는 clone(2) CLONE_THREAD 플래그를 사용하여 생성된 스레드들로 구성된 스레드 그룹을 의미함에 유의하라.) 

프로세스는 fork(2)를 호출하고 결과로 생성된 자식이 PTRACE_TRACEME를 수행한 후, (전형적으로) execve(2)를 뒤따르게 함으로써 추적을 개시할 수 있다. 대안적으로, 한 프로세스는 PTRACE_ATTACH 또는 PTRACE_SEIZE를 사용하여 다른 프로세스의 추적을 시작할 수 있다.

추적되는 동안, 피추적자는 신호가 전달될 때마다, 비록 그 신호가 무시되고 있더라도 멈출 것이다. (SIGKILL은 예외이며, 평상시의 효과를 가진다.) 추적자는 자신의 다음 waitpid(2) 호출(또는 관련된 "wait" 시스템 호출 중 하나)에서 통지받을 것이다; 그 호출은 피추적자의 정지 원인을 나타내는 정보를 포함하는 상태 값을 반환할 것이다. 피추적자가 정지된 동안, 추적자는 다양한 ptrace 요청을 사용하여 피추적자를 조사하고 수정할 수 있다. 추적자는 그 후 피추적자를 계속하게 하며, 선택적으로 전달된 신호를 무시하거나(또는 대신 다른 신호를 전달하거나) 할 수 있다.

PTRACE_O_TRACEEXEC 옵션이 효력이 없다면, 추적되는 프로세스에 의한 모든 성공적인 execve(2) 호출은 SIGTRAP 신호가 전송되게 하여, 새 프로그램이 실행을 시작하기 전에 부모가 제어권을 얻을 기회를 준다. 추적자가 추적을 마쳤을 때, PTRACE_DETACH를 통해 피추적자가 정상적이고 추적되지 않는 모드에서 실행을 계속하게 할 수 있다.

요청 (request)의 값은 수행될 동작을 결정한다: 

**PTRACE_TRACEME**
이 프로세스가 자신의 부모에 의해 추적될 것임을 나타낸다. 부모가 이를 추적할 것을 기대하지 않는다면 프로세스는 아마도 이 요청을 해서는 안 된다. (pid, addr, data는 무시된다.) 

PTRACE_TRACEME 요청은 피추적자에 의해서만 사용된다; 나머지 요청들은 추적자에 의해서만 사용된다. 다음 요청들에서, pid는 조작될 피추적자의 스레드 ID를 지정한다. PTRACE_ATTACH, PTRACE_SEIZE, PTRACE_INTERRUPT, PTRACE_KILL 이외의 요청들에 대해, 피추적자는 정지되어 있어야 한다.

**PTRACE_PEEKTEXT, PTRACE_PEEKDATA**
피추적자의 메모리 내 주소 addr에 있는 워드(word)를 읽어, ptrace() 호출의 결과로 그 워드를 반환한다. 리눅스는 별도의 텍스트 및 데이터 주소 공간을 갖지 않으므로, 이 두 요청은 현재 동일하다. (data는 무시된다; 하지만 비고(NOTES)를 참조하라.) 

**PTRACE_PEEKUSER**
레지스터 및 프로세스에 관한 기타 정보를 보유하는 피추적자의 USER 영역 내 오프셋 addr에서 워드를 읽는다 (<sys/user.h> 참조). 그 워드는 ptrace() 호출의 결과로 반환된다. 전형적으로 오프셋은 워드 정렬(word-aligned)되어야 하지만, 이는 아키텍처에 따라 다를 수 있다. 비고(NOTES)를 참조하라. (data는 무시된다; 하지만 비고를 참조하라.) 

**PTRACE_POKETEXT, PTRACE_POKEDATA**
워드 data를 피추적자의 메모리 내 주소 addr로 복사한다. PTRACE_PEEKTEXT 및 PTRACE_PEEKDATA와 마찬가지로, 이 두 요청은 현재 동일하다.

**PTRACE_POKEUSER**
워드 data를 피추적자의 USER 영역 내 오프셋 addr로 복사한다. PTRACE_PEEKUSER와 마찬가지로, 오프셋은 전형적으로 워드 정렬되어야 한다. 커널의 무결성을 유지하기 위해, USER 영역에 대한 일부 수정은 허용되지 않는다.

**PTRACE_GETREGS, PTRACE_GETFPREGS**
피추적자의 범용 또는 부동 소수점 레지스터를 각각 추적자의 주소 data로 복사한다. 이 데이터의 형식에 관한 정보는 <sys/user.h>를 참조하라. (addr은 무시된다.) SPARC 시스템은 data와 addr의 의미가 반대임에 유의하라; 즉, data는 무시되고 레지스터는 주소 addr로 복사된다. PTRACE_GETREGS 및 PTRACE_GETFPREGS는 모든 아키텍처에 존재하는 것은 아니다.

**PTRACE_GETREGSET (리눅스 2.6.34부터)**
피추적자의 레지스터를 읽는다 . addr은 아키텍처 의존적인 방식으로 읽을 레지스터의 유형을 지정한다. NT_PRSTATUS (수치 1)는 보통 범용 레지스터를 읽는 결과를 낳는다. 만약 CPU가 예를 들어 부동 소수점 및/또는 벡터 레지스터를 가지고 있다면, addr을 해당 NT_foo 상수로 설정함으로써 그것들을 가져올 수 있다 . data는 목적지 버퍼의 위치와 길이를 기술하는 struct iovec을 가리킨다. 반환 시, 커널은 실제 반환된 바이트 수를 나타내도록 iov.len을 수정한다.

**PTRACE_SETREGS, PTRACE_SETFPREGS**
추적자의 주소 data로부터 피추적자의 범용 또는 부동 소수점 레지스터를 각각 수정한다. PTRACE_POKEUSER와 마찬가지로, 일부 범용 레지스터 수정은 허용되지 않을 수 있다. (addr은 무시된다.) SPARC 시스템은 data와 addr의 의미가 반대임에 유의하라; 즉, data는 무시되고 레지스터는 주소 addr로부터 복사된다. PTRACE_SETREGS 및 PTRACE_SETFPREGS는 모든 아키텍처에 존재하는 것은 아니다.

**PTRACE_SETREGSET (리눅스 2.6.34부터)**
피추적자의 레지스터를 수정한다 . addr과 data의 의미는 PTRACE_GETREGSET과 유사하다.

**PTRACE_GETSIGINFO (리눅스 2.3.99-pre6부터)**
정지를 유발한 신호에 관한 정보를 가져온다 . siginfo_t 구조체(sigaction(2) 참조)를 피추적자로부터 추적자의 주소 data로 복사한다. (addr은 무시된다.) 

**PTRACE_SETSIGINFO (리눅스 2.3.99-pre6부터)**
신호 정보를 설정한다: 추적자의 주소 data로부터 siginfo_t 구조체를 피추적자로 복사한다. 이는 보통 피추적자에게 전달될 것이고 추적자에 의해 포착된 신호들에만 영향을 미칠 것이다. 이러한 일반적인 신호들과 ptrace() 자체에 의해 생성된 합성 신호들을 구별하는 것은 어려울 수 있다. (addr은 무시된다.) 

**PTRACE_PEEKSIGINFO (리눅스 3.10부터)**
큐에서 신호를 제거하지 않고 siginfo_t 구조체들을 가져온다 . addr은 신호 복사를 시작할 서수 위치(ordinal position)와 복사할 신호의 수를 지정하는 ptrace_peeksiginfo_args 구조체를 가리킨다 . siginfo_t 구조체들은 data가 가리키는 버퍼로 복사된다. 반환 값은 복사된 신호의 수를 포함한다 (0은 지정된 서수 위치에 해당하는 신호가 없음을 나타낸다). 반환된 siginfo 구조체 내에서, si_code 필드는 사용자 공간에 달리 노출되지 않는 정보(__SI_CHLD, __SI_FAULT 등)를 포함한다.

```c
struct ptrace_peeksiginfo_args {
    u64 off;    /* 신호 복사를 시작할 큐 내의 서수 위치 */
    u32 flags;  /* PTRACE_PEEKSIGINFO_SHARED 또는 0 */
    s32 nr;     /* 복사할 신호의 수 */
};
```

현재 프로세스 전체 신호 큐에서 신호를 덤프하기 위한 플래그는 PTRACE_PEEKSIGINFO_SHARED 하나뿐이다. 이 플래그가 설정되지 않으면, 지정된 스레드의 스레드별 큐에서 신호를 읽는다.

**PTRACE_GETSIGMASK (리눅스 3.11부터)**
차단된 신호의 마스크(sigprocmask(2) 참조) 사본을 data가 가리키는 버퍼에 배치하며, 이는 sigset_t 유형의 버퍼에 대한 포인터여야 한다 . addr 인수는 data가 가리키는 버퍼의 크기(즉, sizeof(sigset_t))를 포함한다.

**PTRACE_SETSIGMASK (리눅스 3.11부터)**
차단된 신호의 마스크(sigprocmask(2) 참조)를 data가 가리키는 버퍼에 지정된 값으로 변경하며, 이는 sigset_t 유형의 버퍼에 대한 포인터여야 한다 . addr 인수는 data가 가리키는 버퍼의 크기(즉, sizeof(sigset_t))를 포함한다.

**PTRACE_SETOPTIONS (리눅스 2.4.6부터; 주의사항은 결함(BUGS) 참조)**
data로부터 ptrace 옵션을 설정한다. (addr은 무시된다.) data는 다음 플래그들에 의해 지정되는 옵션들의 비트 마스크로 해석된다: 

- **PTRACE_O_EXITKILL (리눅스 3.8부터)**
추적자가 종료되면 피추적자에게 SIGKILL 신호를 보낸다. 이 옵션은 피추적자가 추적자의 제어를 절대 벗어나지 못하도록 보장하려는 ptrace 감옥(jailer)들에게 유용하다.
- **PTRACE_O_TRACECLONE (리눅스 2.5.46부터)**
다음 clone(2)에서 피추적자를 정지시키고 새로 복제된 프로세스를 자동으로 추적하기 시작하며, 새 프로세스는 SIGSTOP 또는 (PTRACE_SEIZE가 사용된 경우) PTRACE_EVENT_STOP으로 시작할 것이다. 추적자에 의한 waitpid(2)는 다음과 같은 상태 값을 반환할 것이다:
`status>>8 == (SIGTRAP | (PTRACE_EVENT_CLONE<<8))`
새 프로세스의 PID는 PTRACE_GETEVENTMSG로 가져올 수 있다. 이 옵션은 모든 경우에 clone(2) 호출을 포착하지 못할 수도 있다. 피추적자가 CLONE_VFORK 플래그와 함께 clone(2)을 호출하면, PTRACE_O_TRACEVFORK가 설정된 경우 대신 PTRACE_EVENT_VFORK가 전달될 것이다; 그렇지 않고 피추적자가 종료 신호가 SIGCHLD로 설정된 clone(2)을 호출하면, PTRACE_O_TRACEFORK가 설정된 경우 PTRACE_EVENT_FORK가 전달될 것이다.
- **PTRACE_O_TRACEEXEC (리눅스 2.5.46부터)**
다음 execve(2)에서 피추적자를 정지시킨다. 추적자에 의한 waitpid(2)는 다음과 같은 상태 값을 반환할 것이다:
`status>>8 == (SIGTRAP | (PTRACE_EVENT_EXEC<<8))`
exec를 수행하는 스레드가 스레드 그룹 리더가 아닌 경우, 이 정지 이전에 스레드 ID가 스레드 그룹 리더의 ID로 재설정된다. 리눅스 3.0부터, 이전 스레드 ID는 PTRACE_GETEVENTMSG로 가져올 수 있다.
- **PTRACE_O_TRACEEXIT (리눅스 2.5.60부터)**
종료 시 피추적자를 정지시킨다. 추적자에 의한 waitpid(2)는 다음과 같은 상태 값을 반환할 것이다:
`status>>8 == (SIGTRAP | (PTRACE_EVENT_EXIT<<8))`
피추적자의 종료 상태는 PTRACE_GETEVENTMSG로 가져올 수 있다. 피추적자는 프로세스 종료 중 레지스터가 여전히 사용 가능한 초기에 정지되므로, 추적자가 종료가 발생한 위치를 볼 수 있게 해준다. 반면 일반적인 종료 통지는 프로세스가 종료를 마친 후에 이루어진다. 문맥(context)이 가용함에도 불구하고, 추적자는 이 시점에서 종료가 일어나는 것을 막을 수 없다.
- **PTRACE_O_TRACEFORK (리눅스 2.5.46부터)**
다음 fork(2)에서 피추적자를 정지시키고 새로 포크된 프로세스를 자동으로 추적하기 시작하며, 새 프로세스는 SIGSTOP 또는 (PTRACE_SEIZE가 사용된 경우) PTRACE_EVENT_STOP으로 시작할 것이다. 추적자에 의한 waitpid(2)는 다음과 같은 상태 값을 반환할 것이다:
`status>>8 == (SIGTRAP | (PTRACE_EVENT_FORK<<8))`
새 프로세스의 PID는 PTRACE_GETEVENTMSG로 가져올 수 있다.
- **PTRACE_O_TRACESYSGOOD (리눅스 2.4.6부터)**
시스템 호출 트랩(trap)을 전달할 때, 신호 번호의 7번 비트를 설정한다 (즉, SIGTRAP|0x80을 전달함). 이는 추적자가 일반 트랩과 시스템 호출에 의해 유발된 트랩을 쉽게 구별할 수 있게 해준다.
- **PTRACE_O_TRACEVFORK (리눅스 2.5.46부터)**
다음 vfork(2)에서 피추적자를 정지시키고 새로 vfork된 프로세스를 자동으로 추적하기 시작하며, 새 프로세스는 SIGSTOP 또는 (PTRACE_SEIZE가 사용된 경우) PTRACE_EVENT_STOP으로 시작할 것이다. 추적자에 의한 waitpid(2)는 다음과 같은 상태 값을 반환할 것이다:
`status>>8 == (SIGTRAP | (PTRACE_EVENT_VFORK<<8))`
새 프로세스의 PID는 PTRACE_GETEVENTMSG로 가져올 수 있다.
- **PTRACE_O_TRACEVFORKDONE (리눅스 2.5.60부터)**
다음 vfork(2)의 완료 시 피추적자를 정지시킨다. 추적자에 의한 waitpid(2)는 다음과 같은 상태 값을 반환할 것이다:
`status>>8 == (SIGTRAP | (PTRACE_EVENT_VFORK_DONE<<8))`
새 프로세스의 PID는 (리눅스 2.6.18부터) PTRACE_GETEVENTMSG로 가져올 수 있다.
- **PTRACE_O_TRACESECCOMP (리눅스 3.5부터)**
seccomp(2) SECCOMP_RET_TRACE 규칙이 트리거될 때 피추적자를 정지시킨다. 추적자에 의한 waitpid(2)는 다음과 같은 상태 값을 반환할 것이다:
`status>>8 == (SIGTRAP | (PTRACE_EVENT_SECCOMP<<8))`
이것은 PTRACE_EVENT 정지를 트리거하지만, syscall-enter-stop과 유사하다. 자세한 내용은 아래 PTRACE_EVENT_SECCOMP에 관한 노트를 참조하라. seccomp 이벤트 메시지 데이터(seccomp 필터 규칙의 SECCOMP_RET_DATA 부분으로부터)는 PTRACE_GETEVENTMSG로 가져올 수 있다.
- **PTRACE_O_SUSPEND_SECCOMP (리눅스 4.3부터)**
피추적자의 seccomp 보호를 중단(suspend)시킨다. 이는 모드에 관계없이 적용되며, 피추적자가 아직 seccomp 필터를 설치하지 않았을 때 사용될 수 있다. 즉, 유효한 사용 사례는 피추적자가 필터를 설치하기 전에 피추적자의 seccomp 보호를 중단하고, 피추적자가 필터를 설치하게 한 다음, 필터가 재개되어야 할 때 이 플래그를 해제하는 것이다. 이 옵션을 설정하려면 추적자가 CAP_SYS_ADMIN 역량을 가져야 하며, 어떤 seccomp 보호도 설치되어 있지 않아야 하고, 자기 자신에게 PTRACE_O_SUSPEND_SECCOMP가 설정되어 있지 않아야 한다.

**PTRACE_GETEVENTMSG (리눅스 2.5.46부터)**
방금 발생한 ptrace 이벤트에 관한 메시지를 (unsigned long으로) 가져와 추적자의 주소 data에 배치한다. PTRACE_EVENT_EXIT의 경우, 이는 피추적자의 종료 상태이다. PTRACE_EVENT_FORK, PTRACE_EVENT_VFORK, PTRACE_EVENT_VFORK_DONE, PTRACE_EVENT_CLONE의 경우, 이는 새 프로세스의 PID이다. PTRACE_EVENT_SECCOMP의 경우, 이는 트리거된 규칙과 관련된 seccomp(2) 필터의 SECCOMP_RET_DATA이다. (addr은 무시된다.) 

**PTRACE_CONT**
정지된 피추적자 프로세스를 다시 시작한다. data가 0이 아니면, 이는 피추적자에게 전달될 신호의 번호로 해석된다; 그렇지 않으면 신호가 전달되지 않는다. 따라서 예를 들어, 추적자는 피추적자에게 보내진 신호가 전달될지 여부를 제어할 수 있다. (addr은 무시된다.) 

**PTRACE_SYSCALL, PTRACE_SINGLESTEP**
PTRACE_CONT와 마찬가지로 정지된 피추적자를 다시 시작하되, 각각 다음 시스템 호출의 진입 또는 진출 시에, 또는 단일 명령(instruction) 실행 후에 피추적자가 정지되도록 준비한다. (피추적자는 평상시와 마찬가지로 신호 수신 시에도 정지될 것이다.) 추적자의 관점에서, 피추적자는 SIGTRAP 수신에 의해 정지된 것처럼 보일 것이다. 따라서 PTRACE_SYSCALL의 경우, 예를 들어 첫 번째 정지에서 시스템 호출의 인수들을 조사한 다음, 다시 PTRACE_SYSCALL을 수행하여 두 번째 정지에서 시스템 호출의 반환 값을 조사하는 것이 아이디어이다. data 인수는 PTRACE_CONT와 동일하게 처리된다. (addr은 무시된다.) 

**PTRACE_SET_SYSCALL (리눅스 2.6.16부터)**
syscall-enter-stop 상태일 때, 곧 실행될 시스템 호출의 번호를 data 인수에 지정된 번호로 변경한다. addr 인수는 무시된다. 이 요청은 현재 arm(및 하위 호환성을 위해서만 arm64)에서만 지원되지만, 대부분의 다른 아키텍처는 이를 달성하기 위한 다른 수단(보통 사용자 공간 코드가 시스템 호출 번호를 전달한 레지스터를 변경함으로써)을 가지고 있다.

**PTRACE_SYSEMU, PTRACE_SYSEMU_SINGLESTEP (리눅스 2.6.14부터)**
PTRACE_SYSEMU의 경우, 계속 진행하다 다음 시스템 호출 진입 시 정지하며, 그 시스템 호출은 실행되지 않을 것이다. 아래의 시스템 호출 정지(syscall-stops)에 관한 문서를 참조하라. PTRACE_SYSEMU_SINGLESTEP의 경우, 동일하게 수행하되 시스템 호출이 아닐 경우 단일 단계 실행(singlestep)도 수행한다. 이 호출은 피추적자의 모든 시스템 호출을 에뮬레이트하려는 User Mode Linux와 같은 프로그램들에 의해 사용된다 . data 인수는 PTRACE_CONT와 동일하게 처리된다. addr 인수는 무시된다. 이 요청들은 현재 x86에서만 지원된다.

**PTRACE_LISTEN (리눅스 3.4부터)**
정지된 피추적자를 다시 시작하되, 실행은 방지한다. 결과적으로 발생하는 피추적자의 상태는 SIGSTOP(또는 다른 정지 신호)에 의해 정지된 프로세스와 유사하다. 추가 정보는 "그룹 정지(group-stop)" 소절을 참조하라. PTRACE_LISTEN은 PTRACE_SEIZE에 의해 부착된 피추적자에게만 작동한다.

**PTRACE_KILL**
피추적자를 종료시키기 위해 SIGKILL을 보낸다. (addr와 data는 무시된다.)  이 작업은 더 이상 사용되지 않으므로(deprecated) 사용하지 마라! 대신 kill(2) 또는 tgkill(2)을 사용하여 직접 SIGKILL을 보내라. PTRACE_KILL의 문제는 피추적자가 signal-delivery-stop 상태에 있어야 한다는 것이며, 그렇지 않으면 작동하지 않을 수 있다(즉, 성공적으로 완료되지만 피추적자를 죽이지 못할 수 있음). 반면, SIGKILL을 직접 보내는 것은 그러한 제한이 없다.

**PTRACE_INTERRUPT (리눅스 3.4부터)**
피추적자를 정지시킨다. 피추적자가 커널 공간에서 실행 중이거나 수면 중이고 PTRACE_SYSCALL이 효력 중이면, 시스템 호출이 중단되고 syscall-exit-stop이 보고된다. (중단된 시스템 호출은 피추적자가 다시 시작될 때 재시작된다.) 피추적자가 이미 신호에 의해 정지된 상태에서 PTRACE_LISTEN이 보내졌다면, 피추적자는 PTRACE_EVENT_STOP으로 정지하고 WSTOPSIG(status)는 정지 신호를 반환한다. 동시에 다른 ptrace-stop이 생성되면(예를 들어 피추적자에게 신호가 전송되면), 이 ptrace-stop이 발생한다. 위의 어느 것에도 해당하지 않으면(예를 들어 피추적자가 사용자 공간에서 실행 중이면), WSTOPSIG(status) == SIGTRAP인 PTRACE_EVENT_STOP으로 정지한다. PTRACE_INTERRUPT는 PTRACE_SEIZE로 부착된 피추적자에게만 작동한다.

**PTRACE_ATTACH**
pid에 지정된 프로세스에 부착하여, 호출 프로세스의 피추적자로 만든다. 피추적자에게 SIGSTOP이 전송되지만, 이 호출의 완료 시점에 반드시 정지되어 있는 것은 아니다; 피추적자가 정지하기를 기다리려면 waitpid(2)를 사용하라. 추가 정보는 "부착 및 탈착(Attaching and detaching)" 소절을 참조하라. (addr와 data는 무시된다.)  PTRACE_ATTACH를 수행할 권한은 ptrace 액세스 모드 PTRACE_MODE_ATTACH_REALCREDS 체크에 의해 제어된다; 아래를 참조하라.

**PTRACE_SEIZE (리눅스 3.4부터)**
pid에 지정된 프로세스에 부착하여, 호출 프로세스의 피추적자로 만든다. PTRACE_ATTACH와 달리, PTRACE_SEIZE는 프로세스를 정지시키지 않는다. 그룹 정지(Group-stops)는 PTRACE_EVENT_STOP으로 보고되며 WSTOPSIG(status)는 정지 신호를 반환한다. 자동으로 부착된 자식들은 SIGSTOP 신호가 전달되는 대신 PTRACE_EVENT_STOP으로 정지하며 WSTOPSIG(status)는 SIGTRAP을 반환한다. execve(2)는 추가적인 SIGTRAP을 전달하지 않는다. 오직 PTRACE_SEIZE된 프로세스만이 PTRACE_INTERRUPT 및 PTRACE_LISTEN 명령을 수용할 수 있다. 방금 설명한 "seized" 동작은 PTRACE_O_TRACEFORK, PTRACE_O_TRACEVFORK, PTRACE_O_TRACECLONE을 사용하여 자동으로 부착된 자식들에게 상속된다 . addr은 0이어야 한다. data는 즉시 활성화할 ptrace 옵션들의 비트 마스크를 포함한다. PTRACE_SEIZE를 수행할 권한은 ptrace 액세스 모드 PTRACE_MODE_ATTACH_REALCREDS 체크에 의해 제어된다; 아래를 참조하라.

**PTRACE_SECCOMP_GET_FILTER (리눅스 4.4부터)**
이 작업은 추적자가 피추적자의 클래식 BPF 필터를 덤프할 수 있게 해준다 . addr은 덤프할 필터의 인덱스를 지정하는 정수이다. 가장 최근에 설치된 필터의 인덱스가 0이다. addr이 설치된 필터의 수보다 크면, ENOENT 오류와 함께 작업이 실패한다 . data는 BPF 프로그램을 저장하기에 충분히 큰 struct sock_filter 배열에 대한 포인터이거나, 프로그램을 저장하지 않을 경우 NULL이다. 성공 시 반환 값은 BPF 프로그램의 명령어 수이다 . data가 NULL이었다면, 이 반환 값은 이후 호출에서 전달할 struct sock_filter 배열의 크기를 올바르게 정하는 데 사용될 수 있다. 이 작업은 호출자가 CAP_SYS_ADMIN 역량을 갖지 않거나 엄격(strict) 또는 필터(filter) seccomp 모드인 경우 EACCES 오류와 함께 실패한다 . addr에 의해 참조되는 필터가 클래식 BPF 필터가 아닌 경우, EMEDIUMTYPE 오류와 함께 작업이 실패한다. 이 작업은 커널이 CONFIG_SECCOMP_FILTER와 CONFIG_CHECKPOINT_RESTORE 옵션 모두와 함께 구성된 경우 사용 가능하다.

**PTRACE_DETACH**
PTRACE_CONT와 마찬가지로 정지된 피추적자를 다시 시작하되, 먼저 그로부터 탈착(detach)한다. 리눅스에서, 피추적자는 추적을 개시하는 데 어떤 방법이 사용되었는지에 관계없이 이 방식으로 탈착될 수 있다. (addr은 무시된다.) 

**PTRACE_GET_THREAD_AREA (리눅스 2.6.0부터)**
이 작업은 get_thread_area(2)와 유사한 작업을 수행한다 . addr에 지정된 인덱스를 가진 GDT 내의 TLS 항목을 읽어, data가 가리키는 struct user_desc로 그 항목의 사본을 배치한다. (get_thread_area(2)와 대조적으로, struct user_desc의 entry_number는 무시된다.) 

**PTRACE_SET_THREAD_AREA (리눅스 2.6.0부터)**
이 작업은 set_thread_area(2)와 유사한 작업을 수행한다 . addr에 지정된 인덱스를 가진 GDT 내의 TLS 항목을 설정하며, data가 가리키는 struct user_desc에서 제공된 데이터를 할당한다. (set_thread_area(2)와 대조적으로, struct user_desc의 entry_number는 무시된다; 다시 말해, 이 ptrace 작업은 빈 TLS 항목을 할당하는 데 사용될 수 없다.) 

**PTRACE_GET_SYSCALL_INFO (리눅스 5.3부터)**
정지를 유발한 시스템 호출에 관한 정보를 가져온다. 정보는 data 인수가 가리키는 버퍼에 배치되며, 이는 struct ptrace_syscall_info 유형의 버퍼에 대한 포인터여야 한다 . addr 인수는 data 인수가 가리키는 버퍼의 크기(즉, sizeof(struct ptrace_syscall_info))를 포함한다. 반환 값은 커널이 쓸 수 있는 바이트 수를 포함한다. 커널이 쓸 데이터의 크기가 addr 인수로 지정된 크기를 초과하면, 출력 데이터는 잘린다 . ptrace_syscall_info 구조체는 다음 필드들을 포함한다: 

```c
struct ptrace_syscall_info {
    __u8 op;                    /* 시스템 호출 정지 유형 */
    __u32 arch;                 /* AUDIT_ARCH_* 값; seccomp(2) 참조 */
    __u64 instruction_pointer;  /* CPU 명령 포인터 */
    __u64 stack_pointer;        /* CPU 스택 포인터 */
    union {
        struct {                /* op == PTRACE_SYSCALL_INFO_ENTRY */
            __u64 nr;           /* 시스템 호출 번호 */
            __u64 args[6];      /* 시스템 호출 인수 */
        } entry;
        struct {                /* op == PTRACE_SYSCALL_INFO_EXIT */
            __s64 rval;         /* 시스템 호출 반환 값 */
            __u8 is_error;      /* 시스템 호출 오류 플래그; 불리언: rval이 오류 값(-ERRCODE)을 포함하는가 아니면 비오류 반환 값을 포함하는가? */
        } exit;
        struct {                /* op == PTRACE_SYSCALL_INFO_SECCOMP */
            __u64 nr;           /* 시스템 호출 번호 */
            __u64 args[6];      /* 시스템 호출 인수 */
            __u32 ret_data;     /* SECCOMP_RET_TRACE 반환 값의 SECCOMP_RET_DATA 부분 */
        } seccomp;
    };
};
```

op, arch, instruction_pointer, stack_pointer 필드는 모든 종류의 ptrace 시스템 호출 정지에 대해 정의된다. 구조체의 나머지는 공용체(union)이다; op 필드에 의해 지정된 시스템 호출 정지 종류에 의미 있는 필드들만 읽어야 한다 . op 필드는 어떤 유형의 정지가 발생했고 공용체의 어느 부분이 채워졌는지를 나타내는 다음 값 중 하나(<linux/ptrace.h>에 정의됨)를 가진다: 

- **PTRACE_SYSCALL_INFO_ENTRY**
공용체의 entry 구성요소가 시스템 호출 진입 정지와 관련된 정보를 포함한다.
- **PTRACE_SYSCALL_INFO_EXIT**
공용체의 exit 구성요소가 시스템 호출 진출 정지와 관련된 정보를 포함한다.
- **PTRACE_SYSCALL_INFO_SECCOMP**
공용체의 seccomp 구성요소가 PTRACE_EVENT_SECCOMP 정지와 관련된 정보를 포함한다.
- **PTRACE_SYSCALL_INFO_NONE**
공용체의 어떤 구성요소도 관련 정보를 포함하지 않는다.

#### Ptrace 하에서의 죽음 (Death under ptrace)

(다중 스레드일 수 있는) 프로세스가 살해 신호(처분이 SIG_DFL로 설정되어 있고 기본 동작이 프로세스를 죽이는 신호)를 받으면, 모든 스레드가 종료된다. 피추적자들은 자신의 죽음을 추적자(들)에게 보고한다. 이 이벤트의 통지는 waitpid(2)를 통해 전달된다.

살해 신호는 먼저 (단 하나의 피추적자에게만) signal-delivery-stop을 유발할 것이며, 추적자에 의해 주입된 후에야 (또는 추적되지 않는 스레드에 파견된 후에야) 다중 스레드 프로세스 내의 모든 피추적자에게 신호에 의한 죽음이 일어날 것임에 유의하라. ("signal-delivery-stop"이라는 용어는 아래에서 설명된다.) 

SIGKILL은 signal-delivery-stop을 생성하지 않으며 따라서 추적자는 이를 억제할 수 없다. SIGKILL은 시스템 호출 중에도 죽인다 (SIGKILL에 의한 죽음 이전에 syscall-exit-stop이 생성되지 않는다). 순 결과는 SIGKILL이 프로세스의 일부 스레드가 ptrace 중이더라도 항상 프로세스(모든 스레드)를 죽인다는 것이다.

피추적자가 _exit(2)를 호출할 때, 자신의 죽음을 추적자에게 보고한다. 다른 스레드들은 영향을 받지 않는다. 어느 스레드든 exit_group(2)를 실행하면, 해당 스레드 그룹 내의 모든 피추적자가 자신의 죽음을 추적자에게 보고한다. PTRACE_O_TRACEEXIT 옵션이 켜져 있으면, 실제 죽음 이전에 PTRACE_EVENT_EXIT가 발생할 것이다. 이는 exit(2), exit_group(2)를 통한 종료, 신호에 의한 죽음(커널 버전에 따라 SIGKILL 제외; 아래 결함(BUGS) 참조), 그리고 다중 스레드 프로세스에서 execve(2) 시 스레드들이 해체될 때 적용된다.

추적자는 ptrace-정지된 피추적자가 존재한다고 가정할 수 없다. 정지된 동안 피추적자가 죽을 수 있는 시나리오(예: SIGKILL)가 많다. 그러므로 추적자는 어떤 ptrace 작업에서도 ESRCH 오류를 처리할 준비가 되어 있어야 한다. 불행히도, 피추적자가 존재하지만 ptrace-정지 상태가 아니거나(정지된 피추적자를 요구하는 명령의 경우), ptrace 호출을 발행한 프로세스에 의해 추적되고 있지 않은 경우에도 동일한 오류가 반환된다. 추적자는 피추적자의 정지/실행 상태를 추적해야 하며, 피추적자가 ptrace-정지에 진입하는 것이 관찰되었음을 알 때만 ESRCH를 "피추적자가 예기치 않게 죽음"으로 해석해야 한다 . ptrace 작업이 ESRCH를 반환했을 때 waitpid(WNOHANG)이 피추적자의 죽음 상태를 신뢰성 있게 보고할 것이라는 보장이 없음에 유의하라. waitpid(WNOHANG)은 대신 0을 반환할 수 있다. 다시 말해, 피추적자가 "아직 완전히 죽지는 않았지만" 이미 ptrace 요청을 거부하고 있을 수 있다.

추적자는 피추적자가 항상 WIFEXITED(status) 또는 WIFSIGNALED(status)를 보고하며 생을 마감한다고 가정할 수 없다; 이것이 발생하지 않는 경우가 있다. 예를 들어, 스레드 그룹 리더가 아닌 스레드가 execve(2)를 수행하면, 그 스레드는 사라진다; 그 PID는 다시는 보이지 않을 것이며, 이후의 모든 ptrace 정지는 스레드 그룹 리더의 PID 하에 보고될 것이다.

#### 정지 상태 (Stopped states)

피추적자는 두 가지 상태에 있을 수 있다: 실행 중(running) 또는 정지됨(stopped) . ptrace의 목적상, 시스템 호출(read(2), pause(2) 등)에서 차단된 피추적자는 비록 피추적자가 오랜 시간 차단되어 있더라도 실행 중인 것으로 간주된다. PTRACE_LISTEN 이후의 피추적자 상태는 다소 회색 영역이다: 어떤 ptrace-정지 상태도 아니며(ptrace 명령이 작동하지 않고, waitpid(2) 통지를 전달함), 명령을 실행하지 않고(스케줄링되지 않음) PTRACE_LISTEN 이전에 그룹 정지 상태였다면 SIGCONT를 받을 때까지 신호에 응답하지 않으므로 "정지된" 것으로 간주될 수도 있다.

피추적자가 정지되었을 때의 상태에는 많은 종류가 있으며, ptrace 논의에서 그것들은 종종 혼동된다. 그러므로 정확한 용어를 사용하는 것이 중요하다.

이 매뉴얼 페이지에서, 피추적자가 추적자로부터 ptrace 명령을 수용할 준비가 된 모든 정지 상태를 ptrace-정지(ptrace-stop)라고 부른다 . ptrace-정지는 다시 signal-delivery-stop, group-stop, syscall-stop, PTRACE_EVENT 정지 등으로 세분화될 수 있다. 이러한 정지 상태들은 아래에서 자세히 설명된다.

실행 중인 피추적자가 ptrace-정지에 진입하면, waitpid(2)(또는 다른 "wait" 시스템 호출 중 하나)를 사용하여 추적자에게 통지한다. 이 매뉴얼 페이지의 대부분은 추적자가 다음과 같이 기다린다고 가정한다: 

`pid = waitpid(pid_or_minus_1, &status, __WALL);` 

ptrace-정지된 피추적자들은 pid가 0보다 크고 WIFSTOPPED(status)가 참인 반환으로 보고된다. __WALL 플래그는 WSTOPPED 및 WEXITED 플래그를 포함하지 않지만, 그 기능을 암시한다 . waitpid(2)를 호출할 때 WCONTINUED 플래그를 설정하는 것은 권장되지 않는다: "계속된(continued)" 상태는 프로세스별이며 이를 소비하는 것은 피추적자의 실제 부모를 혼란스럽게 할 수 있다. WNOHANG 플래그의 사용은 추적자가 통지가 있어야 함을 알고 있더라도 waitpid(2)가 0("아직 대기 결과가 없음")을 반환하게 할 수 있다.

예시: 

```c
errno = 0;
ptrace(PTRACE_CONT, pid, 0L, 0L);
if (errno == ESRCH) {
    /* 피추적자가 죽음 */
    r = waitpid(tracee, &status, __WALL | WNOHANG);
    /* 여기서 r은 여전히 0일 수 있음! */
}
```

다음과 같은 종류의 ptrace-정지가 존재한다: signal-delivery-stops, group-stops, PTRACE_EVENT stops, syscall-stops. 그것들은 모두 WIFSTOPPED(status)가 참인 waitpid(2)에 의해 보고된다. 그것들은 status>>8 값을 조사함으로써, 그리고 그 값에 모호함이 있다면 PTRACE_GETSIGINFO를 쿼리함으로써 구별될 수 있다. (참고: WSTOPSIG(status) 매크로는 (status>>8) & 0xff 값을 반환하므로 이 조사에 사용될 수 없다.) 

**신호 전달 정지 (Signal-delivery-stop)**
(다중 스레드일 수 있는) 프로세스가 SIGKILL 이외의 신호를 받으면, 커널은 신호를 처리할 임의의 스레드를 선택한다. (신호가 tgkill(2)로 생성된 경우, 대상 스레드는 호출자에 의해 명시적으로 선택될 수 있다.) 선택된 스레드가 추적 중이면, 그것은 signal-delivery-stop에 진입한다. 이 시점에서 신호는 아직 프로세스에 전달되지 않았으며, 추적자에 의해 억제될 수 있다. 추적자가 신호를 억제하지 않으면, 다음 ptrace 재시작 요청에서 신호를 피추적자에게 전달한다. 신호 전달의 이 두 번째 단계는 이 매뉴얼 페이지에서 신호 주입(signal injection)이라고 부른다. 신호가 차단된 경우, SIGSTOP은 차단될 수 없다는 통상적인 예외와 함께, 신호가 차단 해제될 때까지 signal-delivery-stop은 발생하지 않음에 유의하라 . signal-delivery-stop은 추적자에 의해 WIFSTOPPED(status)가 참이고 WSTOPSIG(status)에 의해 신호가 반환되는 waitpid(2) 반환으로 관찰된다. 신호가 SIGTRAP인 경우, 이는 다른 종류의 ptrace-정지일 수 있다; 자세한 내용은 아래 "Syscall-stops" 및 "execve" 섹션을 참조하라. WSTOPSIG(status)가 정지 신호를 반환하면, 이는 그룹 정지일 수 있다; 아래를 참조하라.

**신호 주입 및 억제 (Signal injection and suppression)**
추적자에 의해 signal-delivery-stop이 관찰된 후, 추적자는 다음 호출로 피추적자를 다시 시작해야 한다:

`ptrace(PTRACE_restart, pid, 0, sig)`

여기서 PTRACE_restart는 재시작하는 ptrace 요청 중 하나이다 . sig가 0이면 신호가 전달되지 않는다. 그렇지 않으면 신호 sig가 전달된다. 이 작업은 signal-delivery-stop과 구별하기 위해 이 매뉴얼 페이지에서 신호 주입(signal injection)이라 불린다 . sig 값은 WSTOPSIG(status) 값과 다를 수 있다: 추적자는 다른 신호가 주입되게 할 수 있다. 억제된 신호라도 시스템 호출이 조기에 반환되게 함에 유의하라. 이 경우 시스템 호출은 재시작될 것이다: 추적자가 PTRACE_SYSCALL을 사용한다면 추적자는 피추적자가 중단된 시스템 호출(또는 재시작을 위해 다른 메커니즘을 사용하는 소수의 시스템 호출에 대해 restart_syscall(2) 시스템 호출)을 재실행하는 것을 관찰할 것이다. 신호 이후 재시작 가능하지 않은 시스템 호출(예: poll(2))조차도 신호가 억제된 후에는 재시작된다; 그러나 피추적자에게 관찰 가능한 신호가 주입되지 않았음에도 일부 시스템 호출이 EINTR과 함께 실패하게 만드는 커널 버그들이 존재한다.

signal-delivery-stop 이외의 ptrace-정지에서 발행된 재시작 ptrace 명령은 sig가 0이 아니더라도 신호 주입을 보장하지 않는다. 오류는 보고되지 않는다; 0이 아닌 sig는 단순히 무시될 수 있다. Ptrace 사용자들은 이런 방식으로 "새로운 신호를 생성"하려고 시도해서는 안 된다: 대신 tgkill(2)을 사용하라 . signal-delivery-stop이 아닌 ptrace 정지 후에 피추적자를 재시작할 때 신호 주입 요청이 무시될 수 있다는 사실은 ptrace 사용자들 사이에서 혼란의 원인이다. 한 가지 전형적인 시나리오는 추적자가 그룹 정지를 관찰하고 이를 signal-delivery-stop으로 오인하여, stopsig를 주입할 의도로 다음과 같이 피추적자를 재시작하지만:

`ptrace(PTRACE_restart, pid, 0, stopsig)`

stopsig는 무시되고 피추적자는 계속 실행되는 것이다.

SIGCONT 신호는 그룹 정지된 프로세스의 (모든 스레드를) 깨우는 부수 효과가 있다. 이 부수 효과는 signal-delivery-stop 이전에 발생한다. 추적자는 이 부수 효과를 억제할 수 없다(추적자는 신호 주입만을 억제할 수 있으며, 이는 피추적자에게 해당 핸들러가 설치된 경우 SIGCONT 핸들러가 실행되지 않게 할 뿐이다). 사실, 그룹 정지에서 깨어나는 것은 SIGCONT가 전달될 때 펜딩 중이었다면 SIGCONT 이외의 신호(들)에 대한 signal-delivery-stop이 뒤따를 수 있다. 다시 말해, SIGCONT는 전송된 후 피추적자에 의해 관찰되는 첫 번째 신호가 아닐 수도 있다. 정지 신호들은 프로세스의 (모든 스레드가) 그룹 정지에 진입하게 한다. 이 부수 효과는 신호 주입 후에 발생하며, 따라서 추적자에 의해 억제될 수 있다. 리눅스 2.4 및 그 이전 버전에서는 SIGSTOP 신호를 주입할 수 없다. PTRACE_GETSIGINFO는 전달된 신호에 해당하는 siginfo_t 구조체를 가져오는 데 사용될 수 있다. PTRACE_SETSIGINFO는 이를 수정하는 데 사용될 수 있다. PTRACE_SETSIGINFO가 siginfo_t를 변경하는 데 사용된 경우, si_signo 필드와 재시작 명령의 sig 매개변수가 일치해야 하며, 그렇지 않으면 결과는 정의되지 않는다.

**그룹 정지 (Group-stop)**
(다중 스레드일 수 있는) 프로세스가 정지 신호를 받으면, 모든 스레드가 정지한다. 일부 스레드가 추적 중이면, 그것들은 그룹 정지에 진입한다. 정지 신호는 먼저 (단 하나의 피추적자에게만) signal-delivery-stop을 유발할 것이며, 추적자에 의해 주입된 후에야 (또는 추적되지 않는 스레드에 파견된 후에야) 다중 스레드 프로세스 내의 모든 피추적자에게 그룹 정지가 개시될 것임에 유의하라. 평상시와 같이, 모든 피추적자는 자신의 그룹 정지를 해당 추적자에게 개별적으로 보고한다. 그룹 정지는 추적자에 의해 WIFSTOPPED(status)가 참이고 WSTOPSIG(status)를 통해 정지 신호를 사용할 수 있는 waitpid(2) 반환으로 관찰된다. 동일한 결과가 다른 부류의 ptrace-정지에 의해서도 반환되므로, 권장되는 관행은 다음 호출을 수행하는 것이다:

`ptrace(PTRACE_GETSIGINFO, pid, 0, &siginfo)`

신호가 SIGSTOP, SIGTSTP, SIGTTIN, SIGTTOU가 아니라면 이 호출은 피할 수 있다; 오직 이 네 가지 신호만이 정지 신호이다. 추적자가 다른 것을 본다면, 그것은 그룹 정지일 수 없다. 그렇지 않다면 추적자는 PTRACE_GETSIGINFO를 호출할 필요가 있다. PTRACE_GETSIGINFO가 EINVAL로 실패한다면, 그것은 확실히 그룹 정지이다. (SIGKILL이 피추적자를 죽인 경우 ESRCH("해당 프로세스 없음")와 같은 다른 실패 코드가 가능하다.) 

피추적자가 PTRACE_SEIZE를 사용하여 부착되었다면, 그룹 정지는 PTRACE_EVENT_STOP에 의해 나타난다: status>>16 == PTRACE_EVENT_STOP. 이는 추가적인 PTRACE_GETSIGINFO 호출을 요구하지 않고 그룹 정지의 탐지를 가능하게 한다. 리눅스 2.6.38부터, 추적자가 피추적자의 ptrace-정지를 본 후 이를 재시작하거나 죽일 때까지, 피추적자는 실행되지 않으며 추적자가 다른 waitpid(2) 호출에 진입하더라도 추적자에게 (SIGKILL 죽음 제외) 통지를 보내지 않는다.

이전 단락에서 설명된 커널 동작은 정지 신호의 투명한 처리에 문제를 일으킨다. 추적자가 그룹 정지 후에 피추적자를 재시작하면, 정지 신호는 사실상 무시된다—피추적자는 정지 상태로 남아 있지 않고 실행된다. 추적자가 다음 waitpid(2)에 진입하기 전에 피추적자를 재시작하지 않으면, 미래의 SIGCONT 신호들이 추적자에게 보고되지 않을 것이다; 이는 SIGCONT 신호들이 피추적자에게 아무런 효과를 미치지 않게 할 것이다. 리눅스 3.4부터 이 문제를 극복할 방법이 있다: PTRACE_CONT 대신, 피추적자가 실행되지는 않지만 waitpid(2)를 통해 보고할 수 있는 새로운 이벤트(예: SIGCONT에 의해 재시작될 때)를 기다리는 방식으로 피추적자를 재시작하는 데 PTRACE_LISTEN 명령이 사용될 수 있다.

**PTRACE_EVENT 정지 (PTRACE_EVENT stops)**
추적자가 PTRACE_O_TRACE_* 옵션을 설정하면, 피추적자는 PTRACE_EVENT 정지라고 불리는 ptrace-정지에 진입할 것이다. PTRACE_EVENT 정지는 추적자에 의해 WIFSTOPPED(status)를 반환하는 waitpid(2)로 관찰되며, WSTOPSIG(status)는 SIGTRAP을 반환한다 (또는 PTRACE_EVENT_STOP의 경우 피추적자가 그룹 정지 상태이면 정지 신호를 반환함). 상태 워드의 상위 바이트에 추가적인 비트가 설정된다: status>>8 값은 다음과 같을 것이다:

`((PTRACE_EVENT_foo<<8) | SIGTRAP)` 

다음과 같은 이벤트들이 존재한다: 

- **PTRACE_EVENT_VFORK**
vfork(2) 또는 CLONE_VFORK 플래그를 가진 clone(2)으로부터 반환되기 전에 정지한다. 피추적자가 이 정지 후 계속되면, 실행을 계속하기 전에 자식이 종료/exec하기를 기다릴 것이다 (다시 말해, vfork(2)에서의 평상시 동작).
- **PTRACE_EVENT_FORK**
fork(2) 또는 종료 신호가 SIGCHLD로 설정된 clone(2)으로부터 반환되기 전에 정지한다.
- **PTRACE_EVENT_CLONE**
clone(2)으로부터 반환되기 전에 정지한다.
- **PTRACE_EVENT_VFORK_DONE**
vfork(2) 또는 CLONE_VFORK 플래그를 가진 clone(2)으로부터 반환되기 전이되, 자식이 종료 또는 exec함으로써 이 피추적자의 차단을 해제한 후에 정지한다.

위에서 설명된 네 가지 정지 모두에 대해, 정지는 새로 생성된 스레드가 아니라 부모(즉, 피추적자)에서 발생한다. PTRACE_GETEVENTMSG를 사용하여 새 스레드의 ID를 가져올 수 있다.

- **PTRACE_EVENT_EXEC**
execve(2)로부터 반환되기 전에 정지한다. 리눅스 3.0부터 PTRACE_GETEVENTMSG는 이전 스레드 ID를 반환한다.
- **PTRACE_EVENT_EXIT**
종료(exit_group(2)에 의한 죽음 포함), 신호에 의한 죽음, 또는 다중 스레드 프로세스에서 execve(2)에 의해 유발된 종료 이전에 정지한다. PTRACE_GETEVENTMSG는 종료 상태를 반환한다. ("진짜" 종료가 일어날 때와 달리) 레지스터를 조사할 수 있다. 피추적자는 여전히 살아있다; 종료를 마치려면 PTRACE_CONT 또는 PTRACE_DETACH되어야 한다.
- **PTRACE_EVENT_STOP**
PTRACE_INTERRUPT 명령에 의해 유도된 정지, 또는 그룹 정지, 또는 새로운 자식이 부착될 때의 초기 ptrace-정지(PTRACE_SEIZE를 사용하여 부착된 경우에만)이다.
- **PTRACE_EVENT_SECCOMP**
추적자에 의해 PTRACE_O_TRACESECCOMP가 설정되었을 때 피추적자의 시스템 호출 진입 시 seccomp(2) 규칙에 의해 트리거된 정지이다 . seccomp 이벤트 메시지 데이터(seccomp 필터 규칙의 SECCOMP_RET_DATA 부분으로부터)는 PTRACE_GETEVENTMSG로 가져올 수 있다. 이 정지의 의미론(semantics)은 아래 별도 섹션에서 자세히 설명된다.

PTRACE_EVENT 정지에서의 PTRACE_GETSIGINFO는 si_signo에 SIGTRAP을 반환하며, si_code는 (event<<8) | SIGTRAP으로 설정된다.

**시스템 호출 정지 (Syscall-stops)**
피추적자가 PTRACE_SYSCALL 또는 PTRACE_SYSEMU에 의해 재시작되었다면, 피추적자는 임의의 시스템 호출에 진입하기 직전에 syscall-enter-stop에 진입한다 (만약 PTRACE_SYSEMU를 사용하여 재시작했다면 그 시스템 호출은 실행되지 않을 것이며, 이는 이 시점에서 레지스터에 가해진 변경이나 이 정지 후 피추적자가 어떻게 재시작되는지에 관계없다) . syscall-entry-stop을 유발한 방법이 무엇이든, 추적자가 PTRACE_SYSCALL로 피추적자를 재시작하면, 시스템 호출이 끝났을 때 또는 신호에 의해 중단되었을 때 피추적자는 syscall-exit-stop에 진입한다. (즉, syscall-enter-stop과 syscall-exit-stop 사이에는 signal-delivery-stop이 절대 발생하지 않는다; 그것은 syscall-exit-stop 이후에 발생한다.)  피추적자가 다른 방법(PTRACE_SYSEMU 포함)을 사용하여 계속된다면, syscall-exit-stop은 발생하지 않는다. PTRACE_SYSEMU에 대한 모든 언급은 PTRACE_SYSEMU_SINGLESTEP에도 동일하게 적용됨에 유의하라.

그러나 피추적자가 PTRACE_SYSCALL을 사용하여 계속되었더라도, 다음 정지가 syscall-exit-stop일 것이라는 보장은 없다. 다른 가능성은 피추적자가 PTRACE_EVENT 정지(seccomp 정지 포함)에서 멈추거나, 종료하거나(_exit(2) 또는 exit_group(2)에 진입한 경우), SIGKILL에 의해 살해되거나, 조용히 죽는 것(스레드 그룹 리더이고, 다른 스레드에서 execve(2)가 발생했으며, 그 스레드가 동일한 추적자에 의해 추적되지 않는 경우; 이 상황은 나중에 논의됨)이다.

syscall-enter-stop 및 syscall-exit-stop은 추적자에 의해 WIFSTOPPED(status)가 참이고 WSTOPSIG(status)가 SIGTRAP을 주는 waitpid(2) 반환으로 관찰된다. 추적자에 의해 PTRACE_O_TRACESYSGOOD 옵션이 설정되었다면, WSTOPSIG(status)는 (SIGTRAP | 0x80) 값을 줄 것이다.

syscall-stop은 다음 경우들에 대해 PTRACE_GETSIGINFO를 쿼리함으로써 SIGTRAP을 동반한 signal-delivery-stop과 구별될 수 있다: 

- **si_code <= 0**
사용자 공간 동작의 결과로 SIGTRAP이 전달되었다. 예를 들어, 시스템 호출(tgkill(2), kill(2), sigqueue(3) 등), POSIX 타이머의 만료, POSIX 메시지 큐의 상태 변경, 또는 비동기 I/O 요청의 완료 등이다.
- **si_code == SI_KERNEL (0x80)**
SIGTRAP이 커널에 의해 전송되었다.
- **si_code == SIGTRAP 또는 si_code == (SIGTRAP|0x80)**
이것은 syscall-stop이다.

그러나 syscall-stop은 매우 자주 발생하며(시스템 호출당 두 번), 모든 syscall-stop에 대해 PTRACE_GETSIGINFO를 수행하는 것은 다소 비용이 많이 들 수 있다. 일부 아키텍처는 레지스터를 조사함으로써 이 경우들을 구별할 수 있게 해준다. 예를 들어 x86에서, syscall-enter-stop일 때 rax == -ENOSYS이다. SIGTRAP(다른 신호와 마찬가지로)은 항상 syscall-exit-stop 이후에 발생하고, 이 시점에서 rax는 거의 절대 -ENOSYS를 포함하지 않으므로, SIGTRAP은 "syscall-enter-stop이 아닌 syscall-stop"처럼 보인다; 다시 말해, 그것은 "길 잃은(stray) syscall-exit-stop"처럼 보이며 이런 방식으로 감지될 수 있다. 하지만 그러한 탐지는 취약하며 피하는 것이 최선이다.

PTRACE_O_TRACESYSGOOD 옵션을 사용하는 것이 신뢰할 수 있고 성능 저하를 초래하지 않으므로 syscall-stop을 다른 종류의 ptrace-정지와 구별하는 권장되는 방법이다.

syscall-enter-stop과 syscall-exit-stop은 추적자에 의해 서로 구별 불가능하다. 추적자는 syscall-enter-stop을 syscall-exit-stop으로 또는 그 반대로 오해하지 않기 위해 ptrace-정지의 순서를 추적해야 한다. 일반적으로, syscall-enter-stop은 항상 syscall-exit-stop, PTRACE_EVENT 정지, 또는 피추적자의 죽음이 뒤따른다; 그 사이에는 다른 종류의 ptrace-정지가 발생할 수 없다. 그러나 seccomp 정지(아래 참조)는 선행하는 syscall-entry-stop 없이 syscall-exit-stop을 유발할 수 있음에 유의하라 . seccomp가 사용 중이라면, 그러한 정지를 syscall-entry-stop으로 오해하지 않도록 주의가 필요하다 . syscall-enter-stop 이후에 추적자가 PTRACE_SYSCALL 이외의 재시작 명령을 사용하면, syscall-exit-stop은 생성되지 않는다 . syscall-stop에서의 PTRACE_GETSIGINFO는 si_signo에 SIGTRAP을 반환하며, si_code는 SIGTRAP 또는 (SIGTRAP|0x80)으로 설정된다.

**PTRACE_EVENT_SECCOMP 정지 (리눅스 3.5에서 4.7)**
PTRACE_EVENT_SECCOMP 정지의 동작과 다른 종류의 ptrace 정지와의 상호작용은 커널 버전 간에 변경되었다. 이것은 그것들이 도입된 때부터 리눅스 4.7(포함)까지의 동작을 문서화한다. 이후 커널 버전의 동작은 다음 섹션에 문서화되어 있다.

PTRACE_EVENT_SECCOMP 정지는 SECCOMP_RET_TRACE 규칙이 트리거될 때마다 발생한다. 이는 시스템 호출을 재시작하는 데 어떤 방법이 사용되었는지와 무관하다. 특히, 피추적자가 PTRACE_SYSEMU를 사용하여 재시작되었고 이 시스템 호출이 무조건 건너뛰어지더라도 seccomp는 여전히 실행된다. 이 정지로부터의 재시작은 해당 시스템 호출 바로 직전에 정지가 발생했던 것처럼 동작할 것이다. 특히, PTRACE_SYSCALL과 PTRACE_SYSEMU 모두 보통 후속 syscall-entry-stop을 유발할 것이다. 그러나 PTRACE_EVENT_SECCOMP 이후에 시스템 호출 번호가 음수이면, syscall-entry-stop과 시스템 호출 자체 모두 건너뛰어질 것이다. 이는 PTRACE_EVENT_SECCOMP 이후 시스템 호출 번호가 음수이고 피추적자가 PTRACE_SYSCALL을 사용하여 재시작된다면, 기대되었을 수도 있는 syscall-entry-stop 대신 다음에 관찰되는 정지는 syscall-exit-stop이 될 것임을 의미한다.

**PTRACE_EVENT_SECCOMP 정지 (리눅스 4.8부터)**
리눅스 4.8부터, PTRACE_EVENT_SECCOMP 정지는 syscall-entry-stop과 syscall-exit-stop 사이에서 발생하도록 재배치되었다. 시스템 호출이 PTRACE_SYSEMU로 인해 건너뛰어지면 seccomp는 더 이상 실행되지 않음(그리고 PTRACE_EVENT_SECCOMP도 보고되지 않음)에 유의하라. 기능적으로, PTRACE_EVENT_SECCOMP 정지는 syscall-entry-stop과 비교 가능하게 작동한다(즉, PTRACE_SYSCALL을 사용한 계속은 syscall-exit-stop을 유발할 것이며, 시스템 호출 번호가 변경될 수 있고 다른 수정된 레지스터들도 실행될 시스템 호출에 그대로 보임). 선행하는 syscall-entry-stop이 있었을 수도 있지만, 반드시 있어야 했던 것은 아님에 유의하라. PTRACE_EVENT_SECCOMP 정지 이후에 seccomp가 재실행될 것이며, 이때 SECCOMP_RET_TRACE 규칙은 이제 SECCOMP_RET_ALLOW와 동일하게 작동한다. 구체적으로, 이는 PTRACE_EVENT_SECCOMP 정지 동안 레지스터가 수정되지 않는다면, 시스템 호출이 허용될 것임을 의미한다.

**PTRACE_SINGLESTEP 정지**
[이러한 종류의 정지에 대한 세부 사항은 아직 문서화되지 않음.] 

**정보 제공 및 재시작 ptrace 명령 (Informational and restarting ptrace commands)**
대부분의 ptrace 명령(PTRACE_ATTACH, PTRACE_SEIZE, PTRACE_TRACEME, PTRACE_INTERRUPT, PTRACE_KILL 제외 전부)은 피추적자가 ptrace-정지 상태에 있을 것을 요구하며, 그렇지 않으면 ESRCH로 실패한다. 피추적자가 ptrace-정지 상태일 때, 추적자는 정보 제공 명령을 사용하여 피추적자에게 데이터를 읽고 쓸 수 있다. 이 명령들은 피추적자를 ptrace-정지 상태로 남겨둔다: 

```c
ptrace(PTRACE_PEEKTEXT/PEEKDATA/PEEKUSER, pid, addr, 0);
ptrace(PTRACE_POKETEXT/POKEDATA/POKEUSER, pid, addr, long_val);
ptrace(PTRACE_GETREGS/GETFPREGS, pid, 0, &struct);
ptrace(PTRACE_SETREGS/SETFPREGS, pid, 0, &struct);
ptrace(PTRACE_GETREGSET, pid, NT_foo, &iov);
ptrace(PTRACE_SETREGSET, pid, NT_foo, &iov);
ptrace(PTRACE_GETSIGINFO, pid, 0, &siginfo);
ptrace(PTRACE_SETSIGINFO, pid, 0, &siginfo);
ptrace(PTRACE_GETEVENTMSG, pid, 0, &long_var);
ptrace(PTRACE_SETOPTIONS, pid, 0, PTRACE_O_flags);
```

일부 오류는 보고되지 않음에 유의하라. 예를 들어, 신호 정보(siginfo)를 설정하는 것이 일부 ptrace-정지에서는 아무런 효과가 없을 수 있지만, 호출은 성공할 수 있다(0을 반환하고 errno를 설정하지 않음); 현재 ptrace-정지가 의미 있는 이벤트 메시지를 반환하는 것으로 문서화되어 있지 않더라도 PTRACE_GETEVENTMSG를 쿼리하는 것이 성공하고 어떤 임의의 값을 반환할 수 있다.

`ptrace(PTRACE_SETOPTIONS, pid, 0, PTRACE_O_flags);` 호출은 하나의 피추적자에게 영향을 미친다. 피추적자의 현재 플래그가 대체된다. 플래그는 활성화된 PTRACE_O_TRACEFORK, PTRACE_O_TRACEVFORK, 또는 PTRACE_O_TRACECLONE 옵션을 통해 생성되고 "자동 부착"된 새로운 피추적자들에게 상속된다.

또 다른 명령 그룹은 ptrace-정지된 피추적자를 실행하게 한다. 그것들은 다음과 같은 형태를 가진다: 

`ptrace(cmd, pid, 0, sig);` 

여기서 cmd는 PTRACE_CONT, PTRACE_LISTEN, PTRACE_DETACH, PTRACE_SYSCALL, PTRACE_SINGLESTEP, PTRACE_SYSEMU, 또는 PTRACE_SYSEMU_SINGLESTEP이다. 피추적자가 signal-delivery-stop 상태이면, sig는 주입될 신호이다 (0이 아니라면). 그렇지 않으면 sig는 무시될 수 있다. (signal-delivery-stop 이외의 ptrace-정지에서 피추적자를 재시작할 때 권장되는 관행은 항상 sig에 0을 전달하는 것이다.) 

**부착 및 탈착 (Attaching and detaching)**
스레드는 다음 호출을 사용하여 추적자에게 부착될 수 있다:

`ptrace(PTRACE_ATTACH, pid, 0, 0);` 
또는
`ptrace(PTRACE_SEIZE, pid, 0, PTRACE_O_flags);` 

PTRACE_ATTACH는 이 스레드에 SIGSTOP을 보낸다. 추적자가 이 SIGSTOP이 아무런 효과가 없기를 원한다면, 그것을 억제해야 한다. 부착 중에 다른 신호들이 이 스레드에 동시에 전송된다면, 추적자는 피추적자가 다른 신호(들)와 함께 먼저 signal-delivery-stop에 진입하는 것을 볼 수 있음에 유의하라!  통상적인 관행은 SIGSTOP이 보일 때까지 이러한 신호들을 재주입한 다음, SIGSTOP 주입을 억제하는 것이다. 여기서 설계상의 버그는 ptrace 부착과 동시에 전달된 SIGSTOP이 경쟁(race)할 수 있고 동시의 SIGSTOP이 유실될 수 있다는 점이다. 부착이 SIGSTOP을 전송하고 추적자가 보통 이를 억제하므로, 이는 "신호 주입 및 억제" 섹션에서 설명한 것처럼 피추적자에서 현재 실행 중인 시스템 호출로부터 길 잃은(stray) EINTR 반환을 유발할 수 있다.

리눅스 3.4부터 PTRACE_ATTACH 대신 PTRACE_SEIZE가 사용될 수 있다. PTRACE_SEIZE는 부착된 프로세스를 정지시키지 않는다. 부착 후(또는 다른 어느 때든) 신호를 보내지 않고 프로세스를 정지시켜야 한다면, PTRACE_INTERRUPT 명령을 사용하라.

`ptrace(PTRACE_TRACEME, 0, 0, 0);` 요청은 호출하는 스레드를 피추적자로 전환한다. 스레드는 계속 실행된다 (ptrace-정지에 진입하지 않음). 일반적인 관행은 PTRACE_TRACEME 뒤에 `raise(SIGSTOP);`을 따르게 하여 부모(이제 우리의 추적자인)가 우리의 signal-delivery-stop을 관찰할 수 있게 하는 것이다.

PTRACE_O_TRACEFORK, PTRACE_O_TRACEVFORK, 또는 PTRACE_O_TRACECLONE 옵션이 효력 중이면, 각각 vfork(2) 또는 CLONE_VFORK 플래그를 가진 clone(2), fork(2) 또는 종료 신호가 SIGCHLD로 설정된 clone(2), 그리고 다른 종류의 clone(2)에 의해 생성된 자식들은 부모를 추적했던 동일한 추적자에게 자동으로 부착된다. 자식들에게 SIGSTOP이 전달되어, 그들이 자신을 생성한 시스템 호출을 벗어난 후에 signal-delivery-stop에 진입하게 한다.

피추적자의 탈착은 다음에 의해 수행된다: 

`ptrace(PTRACE_DETACH, pid, 0, sig);` 

PTRACE_DETACH는 재시작 작업이다; 그러므로 피추적자가 ptrace-정지 상태에 있을 것을 요구한다. 피추적자가 signal-delivery-stop 상태이면, 신호를 주입할 수 있다. 그렇지 않으면 sig 매개변수는 조용히 무시될 수 있다.

추적자가 피추적자를 탈착하고 싶을 때 피추적자가 실행 중이라면, 일반적인 해결책은 (올바른 스레드로 가도록 보장하기 위해 tgkill(2)을 사용하여) SIGSTOP을 보내고, 피추적자가 SIGSTOP에 대한 signal-delivery-stop에서 멈추기를 기다린 다음 탈착하는 것(SIGSTOP 주입을 억제하며)이다. 설계상의 버그는 이것이 동시의 SIGSTOP들과 경쟁할 수 있다는 점이다. 또 다른 복잡함은 피추적자가 다른 ptrace-정지에 진입할 수 있으며 SIGSTOP이 보일 때까지 다시 시작하고 기다려야 할 필요가 있다는 점이다. 또 다른 복잡함은 피추적자가 이미 ptrace-정지 상태가 아님을 확인하는 것인데, 정지 상태인 동안에는 어떤 신호 전달도—SIGSTOP조차도—발생하지 않기 때문이다.

추적자가 죽으면, 모든 피추적자는 그룹 정지 상태가 아니었다면 자동으로 탈착되고 재시작된다. 그룹 정지로부터의 재시작 처리는 현재 버그가 있지만, "계획된" 동작은 피추적자를 정지된 상태로 두고 SIGCONT를 기다리게 하는 것이다. 피추적자가 signal-delivery-stop으로부터 재시작되면, 펜딩 중인 신호가 주입된다.

**ptrace 하에서의 execve(2) (execve(2) under ptrace)**
다중 스레드 프로세스의 한 스레드가 execve(2)를 호출하면, 커널은 프로세스 내의 다른 모든 스레드를 파괴하고, exec를 수행하는 스레드의 스레드 ID를 스레드 그룹 ID(프로세스 ID)로 재설정한다. (또는 사물을 다르게 표현하자면, 다중 스레드 프로세스가 execve(2)를 할 때, 호출 완료 시점에 어느 스레드가 execve(2)를 했는지에 관계없이 execve(2)가 스레드 그룹 리더에서 발생한 것처럼 보인다.) 이러한 스레드 ID의 재설정은 추적자들에게 매우 혼란스럽게 보인다: 

- PTRACE_O_TRACEEXIT 옵션이 켜져 있었다면, 다른 모든 스레드는 PTRACE_EVENT_EXIT 정지에서 멈춘다. 그 후 스레드 그룹 리더를 제외한 다른 모든 스레드는 마치 종료 코드 0으로 _exit(2)를 통해 종료한 것처럼 죽음을 보고한다.
- exec를 수행하는 피추적자는 execve(2) 중에 자신의 스레드 ID를 변경한다. (ptrace 하에서 waitpid(2)로부터 반환되거나 ptrace 호출에 공급되는 "pid"는 피추적자의 스레드 ID임을 기억하라.) 즉, 피추적자의 스레드 ID는 자신의 프로세스 ID와 동일하게 재설정되며, 이는 스레드 그룹 리더의 스레드 ID와 동일하다.
- 그 후 PTRACE_O_TRACEEXEC 옵션이 켜져 있었다면 PTRACE_EVENT_EXEC 정지가 발생한다.
- 만약 스레드 그룹 리더가 이 시점까지 자신의 PTRACE_EVENT_EXIT 정지를 보고했다면, 추적자에게는 죽은 스레드 리더가 "난데없이 다시 나타나는" 것처럼 보인다. (참고: 스레드 그룹 리더는 적어도 하나의 다른 살아있는 스레드가 있을 때까지 WIFEXITED(status)를 통한 죽음을 보고하지 않는다. 이는 추적자가 그것이 죽는 것을 본 후 다시 나타나는 것을 볼 가능성을 제거한다.) 스레드 그룹 리더가 여전히 살아있었다면, 추적자에게 이는 스레드 그룹 리더가 진입했던 것과 다른 시스템 호출로부터 반환하거나, 심지어 "어떤 시스템 호출 상태도 아니었음에도 시스템 호출로부터 반환한" 것처럼 보일 수 있다.
- 스레드 그룹 리더가 추적되지 않았거나(또는 다른 추적자에 의해 추적되었다면), execve(2) 중에 그것은 exec를 수행하는 피추적자의 추적자의 피추적자가 된 것처럼 보일 것이다.

위의 모든 효과들은 피추적자의 스레드 ID 변경으로 인한 가공물(artifacts)이다. PTRACE_O_TRACEEXEC 옵션은 이 상황을 처리하기 위해 권장되는 도구이다. 첫째, 이는 execve(2)가 반환되기 전에 발생하는 PTRACE_EVENT_EXEC 정지를 가능하게 한다. 이 정지에서 추적자는 PTRACE_GETEVENTMSG를 사용하여 피추적자의 이전 스레드 ID를 가져올 수 있다. (이 기능은 리눅스 3.0에서 도입되었다.) 둘째, PTRACE_O_TRACEEXEC 옵션은 execve(2)에서의 레거시 SIGTRAP 생성을 비활성화한다.

추적자가 PTRACE_EVENT_EXEC 정지 통지를 받았을 때, 이 피추적자와 스레드 그룹 리더를 제외하고는 프로세스의 다른 어떤 스레드도 살아있지 않음이 보장된다. PTRACE_EVENT_EXEC 정지 통지를 받으면, 추적자는 이 프로세스의 스레드들을 기술하는 자신의 모든 내부 데이터 구조를 정리해야 하며, 오직 하나의 데이터 구조—다음과 같은, 여전히 실행 중인 단일 피추적자를 기술하는 구조—만을 보유해야 한다: 

`스레드 ID == 스레드 그룹 ID == 프로세스 ID` 

예시: 두 스레드가 동시에 execve(2)를 호출함: 

*** 스레드 1에서 syscall-enter-stop 발생: ***
PID1 execve("/bin/foo", "foo" <미완료 ...>
*** 스레드 1에 대해 PTRACE_SYSCALL 발행 ***
*** 스레드 2에서 syscall-enter-stop 발생: ***
PID2 execve("/bin/bar", "bar" <미완료 ...>
*** 스레드 2에 대해 PTRACE_SYSCALL 발행 ***
*** PID0에 대해 PTRACE_EVENT_EXEC 발생, PTRACE_SYSCALL 발행 ***
*** PID0에 대해 syscall-exit-stop 발생: ***
PID0 <... execve 재개> ) = 0 

exec를 수행하는 피추적자에게 PTRACE_O_TRACEEXEC 옵션이 효력 중이지 않고, 피추적자가 PTRACE_SEIZE가 아니라 PTRACE_ATTACH되었다면, 커널은 execve(2)가 반환된 후 피추적자에게 추가적인 SIGTRAP을 전달한다. 이것은 특별한 종류의 ptrace-정지가 아니라 일반적인 신호(kill -TRAP에 의해 생성될 수 있는 것과 유사함)이다. 이 신호에 대해 PTRACE_GETSIGINFO를 사용하면 si_code가 0(SI_USER)으로 설정되어 반환된다. 이 신호는 신호 마스크에 의해 차단될 수 있으며, 따라서 (훨씬) 나중에 전달될 수도 있다.

보통 추적자(예: strace(1))는 이 추가적인 execve 이후 SIGTRAP 신호를 사용자에게 보여주고 싶어 하지 않을 것이며, 피추적자에게의 전달을 억제할 것이다 (SIGTRAP이 SIG_DFL로 설정되어 있으면 살해 신호임). 그러나 어떤 SIGTRAP을 억제할지 결정하는 것은 쉽지 않다. PTRACE_O_TRACEEXEC 옵션을 설정하거나 PTRACE_SEIZE를 사용하여 이 추가적인 SIGTRAP을 억제하는 것이 권장되는 접근 방식이다.

**실제 부모 (Real parent)**
ptrace API는 waitpid(2)를 통한 표준 UNIX 부모/자식 신호 전달을 남용(abuses)한다. 이는 자식 프로세스가 다른 프로세스에 의해 추적될 때 프로세스의 실제 부모가 여러 종류의 waitpid(2) 통지를 받는 것을 중단하게 하곤 했다. 이러한 버그들 중 많은 것들이 수정되었지만, 리눅스 2.6.38 현재 여러 개가 여전히 존재한다; 아래 결함(BUGS)을 참조하라.

리눅스 2.6.38 현재, 다음은 올바르게 작동하는 것으로 믿어진다: 

- 신호에 의한 종료/죽음은 먼저 추적자에게 보고되고, 그 후 추적자가 waitpid(2) 결과를 소비했을 때 실제 부모에게 보고된다 (다중 스레드 프로세스 전체가 종료될 때만 실제 부모에게 보고됨). 추적자와 실제 부모가 동일한 프로세스라면, 보고는 단 한 번만 전송된다.

### 반환 값 (RETURN VALUE)

성공 시, PTRACE_PEEK* 요청은 요청된 데이터를 반환하고(하지만 비고(NOTES) 참조), PTRACE_SECCOMP_GET_FILTER 요청은 BPF 프로그램의 명령어 수를 반환하며, 다른 요청들은 0을 반환한다. 오류 시, 모든 요청은 -1을 반환하고 errno가 적절히 설정된다. 성공적인 PTRACE_PEEK* 요청에 의해 반환된 값이 -1일 수 있으므로, 호출자는 호출 전에 errno를 지워야 하며, 그 후 오류가 발생했는지 여부를 확인하기 위해 이를 검사해야 한다.

### 오류 (ERRORS)

- **EBUSY** (i386 전용) 디버그 레지스터를 할당하거나 해제하는 데 오류가 있었다.
- **EFAULT** 추적자 또는 피추적자의 메모리 내 잘못된 영역을 읽거나 쓰려는 시도가 있었다. 아마도 해당 영역이 매핑되지 않았거나 접근 가능하지 않았기 때문일 것이다. 불행히도 리눅스 하에서, 이 결함의 다른 변형들은 다소 임의적으로 EIO 또는 EFAULT를 반환할 것이다.
- **EINVAL** 잘못된 옵션을 설정하려는 시도가 있었다.
- **EIO** 요청이 유효하지 않거나, 추적자 또는 피추적자의 메모리 내 잘못된 영역을 읽거나 쓰려는 시도가 있었거나, 워드 정렬 위반이 있었거나, 재시작 요청 중에 잘못된 신호가 지정되었다.
- **EPERM** 지정된 프로세스를 추적할 수 없다. 이는 추적자가 불충분한 특권(필요한 역량은 CAP_SYS_PTRACE임)을 가졌기 때문일 수 있다; 명백한 이유로, 특권이 없는 프로세스는 자신이 신호를 보낼 수 없는 프로세스나 set-user-ID/set-group-ID 프로그램을 실행 중인 프로세스를 추적할 수 없다. 대안적으로, 프로세스가 이미 추적되고 있거나, (2.6.26 이전 커널에서) init(1)(PID 1)일 수 있다.
- **ESRCH** 지정된 프로세스가 존재하지 않거나, 호출자에 의해 현재 추적되고 있지 않거나, 정지되어 있지 않다(정지된 피추적자를 요구하는 요청의 경우).

### 준수 (CONFORMING TO)

SVr4, 4.3BSD.

### 비고 (NOTES)

ptrace()의 인수들이 주어진 프로토타입에 따라 해석되지만, glibc는 현재 ptrace()를 요청(request) 인수만 고정된 가변 인수 함수로 선언한다. 요청된 작업이 그것들을 사용하지 않더라도 항상 네 개의 인수를 공급하고, 사용되지 않거나 무시되는 인수는 0L 또는 (void *) 0으로 설정하는 것이 권장된다.

리눅스 2.6.26 이전 커널에서, PID 1인 프로세스인 init(1)은 추적되지 않을 수 있다. 피추적자의 부모는 해당 추적자가 execve(2)를 호출하더라도 계속해서 추적자이다.

메모리 내용 및 USER 영역의 레이아웃은 운영 체제 및 아키텍처에 상당히 의존적이다. 공급된 오프셋과 반환된 데이터는 struct user의 정의와 완전히 일치하지 않을 수 있다. "워드(word)"의 크기는 운영 체제 변형에 의해 결정된다(예: 32비트 리눅스의 경우 32비트임).

이 페이지는 ptrace() 호출이 현재 리눅스에서 작동하는 방식을 문서화한다. 그 동작은 다른 풍미의 UNIX에서 상당히 다르다. 어떤 경우이든, ptrace()의 사용은 운영 체제와 아키텍처에 매우 특화되어 있다.

**Ptrace 액세스 모드 검사 (Ptrace access mode checking)**
커널-사용자 공간 API의 다양한 부분(ptrace() 작업뿐만 아니라)은 이른바 "ptrace 액세스 모드" 검사를 요구하며, 그 결과에 따라 작업의 허용 여부가 결정된다 (또는 몇몇 경우 "읽기" 작업이 위생화된 데이터를 반환하게 함). 이러한 검사는 한 프로세스가 다른 프로세스에 관한 민감한 정보를 조사하거나, 어떤 경우 상태를 수정할 수 있는 상황에서 수행된다. 검사는 두 프로세스의 자격 증명(credentials) 및 역량(capabilities), "대상" 프로세스가 덤프 가능한지 여부, 그리고 활성화된 리눅스 보안 모듈(LSM)—예를 들어 SELinux, Yama, Smack—및 (항상 호출되는) commoncap LSM에 의해 수행된 검사 결과와 같은 요인들에 기반한다.

리눅스 2.6.27 이전에는 모든 액세스 검사가 단일 유형이었다. 리눅스 2.6.27부터 두 가지 액세스 모드 수준이 구별된다: 

- **PTRACE_MODE_READ**
"읽기" 작업 또는 덜 위험한 기타 작업들. 예: get_robust_list(2), kcmp(2), /proc/[pid]/auxv, /proc/[pid]/environ, /proc/[pid]/stat 읽기, 또는 /proc/[pid]/ns/* 파일의 readlink(2).
- **PTRACE_MODE_ATTACH**
"쓰기" 작업 또는 더 위험한 기타 작업들. 예: 다른 프로세스에 ptrace 부착(PTRACE_ATTACH) 또는 process_vm_writev(2) 호출. (PTRACE_MODE_ATTACH는 사실상 리눅스 2.6.27 이전의 기본값이었음)

리눅스 4.5부터 위의 액세스 모드 검사는 다음 수정자 중 하나와 결합(OR)된다: 

- **PTRACE_MODE_FSCREDS**
LSM 검사를 위해 호출자의 파일 시스템 UID 및 GID(credentials(7) 참조) 또는 실효 역량(effective capabilities)을 사용한다.
- **PTRACE_MODE_REALCREDS**
LSM 검사를 위해 호출자의 실제(real) UID 및 GID 또는 허용된 역량(permitted capabilities)을 사용한다. 이것은 사실상 리눅스 4.5 이전의 기본값이다.

자격 증명 수정자 중 하나를 앞서 언급한 액세스 모드 중 하나와 결합하는 것이 일반적이므로, 커널 소스에는 조합을 위한 몇 가지 매크로가 정의되어 있다: 

- **PTRACE_MODE_READ_FSCREDS**: PTRACE_MODE_READ | PTRACE_MODE_FSCREDS로 정의됨.
- **PTRACE_MODE_READ_REALCREDS**: PTRACE_MODE_READ | PTRACE_MODE_REALCREDS로 정의됨.
- **PTRACE_MODE_ATTACH_FSCREDS**: PTRACE_MODE_ATTACH | PTRACE_MODE_FSCREDS로 정의됨.
- **PTRACE_MODE_ATTACH_REALCREDS**: PTRACE_MODE_ATTACH | PTRACE_MODE_REALCREDS로 정의됨.

한 가지 추가 수정자가 액세스 모드와 OR될 수 있다: 

- **PTRACE_MODE_NOAUDIT (리눅스 3.3부터)**
이 액세스 모드 검사를 감사(audit)하지 마라. 이 수정자는 호출자에게 오류가 반환되게 하기보다 단순히 출력이 필터링되거나 위생화되게 하는 ptrace 액세스 모드 검사(예: /proc/[pid]/stat을 읽을 때의 검사)에 고용된다. 이러한 경우 파일에 접근하는 것은 보안 위반이 아니며 보안 감사 기록을 생성할 이유가 없다. 이 수정자는 특정 액세스 검사에 대한 그러한 감사 기록의 생성을 억제한다.

이 소절에서 설명된 모든 PTRACE_MODE_* 상수는 커널 내부용이며 사용자 공간에는 보이지 않음에 유의하라. 상수 이름들은 다양한 시스템 호출 및 다양한 의사 파일(예: /proc 하의 파일)에 대한 접근 시 수행되는 다양한 종류의 ptrace 액세스 모드 검사를 라벨링하기 위해 여기서 언급된다. 이 이름들은 다른 매뉴얼 페이지에서 서로 다른 커널 검사를 라벨링하기 위한 간단한 약어로 사용된다.

ptrace 액세스 모드 검사에 사용되는 알고리즘은 호출 프로세스가 대상 프로세스에 대해 해당 동작을 수행하도록 허용되는지 여부를 결정한다. (/proc/[pid] 파일을 여는 경우, "호출 프로세스"는 파일을 여는 프로세스이고, 해당 PID를 가진 프로세스가 "대상 프로세스"이다.) 알고리즘은 다음과 같다: 

1. 호출 스레드와 대상 스레드가 동일한 스레드 그룹에 있다면, 액세스는 항상 허용된다.
2. 액세스 모드가 PTRACE_MODE_FSCREDS를 지정하면, 다음 단계의 검사를 위해 호출자의 파일 시스템 UID 및 GID를 고용한다. (credentials(7)에서 언급된 바와 같이, 파일 시스템 UID 및 GID는 거의 항상 해당 실효 ID와 동일한 값을 가짐). 그렇지 않으면 액세스 모드는 PTRACE_MODE_REALCREDS를 지정하므로, 다음 단계의 검사를 위해 호출자의 실제 UID 및 GID를 사용한다. (호출자의 UID 및 GID를 확인하는 대부분의 API는 실효 ID를 사용함. 역사적인 이유로 PTRACE_MODE_REALCREDS 검사는 대신 실제 ID를 사용함) .
3. 다음 중 어느 것도 참이 아니면 액세스를 거부한다:
  - 대상의 실제, 실효, 저장된 설정 사용자 ID가 호출자의 사용자 ID와 일치하고, 대상의 실제, 실효, 저장된 설정 그룹 ID가 호출자의 그룹 ID와 일치함.
  - 호출자가 대상의 사용자 네임스페이스에서 CAP_SYS_PTRACE 역량을 가짐.
4. 대상 프로세스의 "dumpable" 속성이 1(SUID_DUMP_USER; prctl(2)의 PR_SET_DUMPABLE 논의 참조) 이외의 값을 가지고, 호출자가 대상 프로세스의 사용자 네임스페이스에서 CAP_SYS_PTRACE 역량을 가지지 않는다면 액세스를 거부한다.
5. 커널 LSM security_ptrace_access_check() 인터페이스가 호출되어 ptrace 액세스가 허용되는지 확인한다. 결과는 LSM(들)에 따라 다르다. commoncap LSM에서의 이 인터페이스 구현은 다음 단계들을 수행한다:
  a) 액세스 모드에 PTRACE_MODE_FSCREDS가 포함되면 다음 검사에서 호출자의 실효 역량 세트를 사용한다; 그렇지 않으면 (액세스 모드가 PTRACE_MODE_REALCREDS를 지정하므로) 호출자의 허용된 역량 세트를 사용한다.
   b) 다음 중 어느 것도 참이 아니면 액세스를 거부한다:
      * 호출자와 대상 프로세스가 동일한 사용자 네임스페이스에 있고, 호출자의 역량이 대상 프로세스의 허용된 역량의 슈퍼셋임.
      * 호출자가 대상 프로세스의 사용자 네임스페이스에서 CAP_SYS_PTRACE 역량을 가짐.
   commoncap LSM은 PTRACE_MODE_READ와 PTRACE_MODE_ATTACH를 구별하지 않음에 유의하라.
6. 선행하는 어느 단계에서도 액세스가 거부되지 않았다면, 액세스가 허용된다.

**/proc/sys/kernel/yama/ptrace_scope**
Yama 리눅스 보안 모듈(LSM)이 설치된 시스템에서(즉, 커널이 CONFIG_SECURITY_YAMA와 함께 구성됨), /proc/sys/kernel/yama/ptrace_scope 파일(리눅스 3.4부터 사용 가능)은 ptrace()로 프로세스를 추적하는 능력(따라서 strace(1) 및 gdb(1)와 같은 도구를 사용하는 능력)을 제한하는 데 사용될 수 있다. 그러한 제한의 목적은 손상된 프로세스가 메모리에 존재할 수 있는 추가 자격 증명을 얻어 공격 범위를 확장하기 위해 사용자가 소유한 다른 민감한 프로세스(예: GPG 에이전트 또는 SSH 세션)에 ptrace-attach할 수 있는 공격 단계 상승을 방지하는 것이다. 더 정확하게는, Yama LSM은 두 가지 유형의 작업을 제한한다: 

- ptrace 액세스 모드 PTRACE_MODE_ATTACH 검사를 수행하는 모든 작업—예를 들어 ptrace() PTRACE_ATTACH. (위의 "Ptrace 액세스 모드 검사" 논의 참조) .
- ptrace() PTRACE_TRACEME.

CAP_SYS_PTRACE 역량을 가진 프로세스는 /proc/sys/kernel/yama/ptrace_scope 파일을 다음 값 중 하나로 업데이트할 수 있다: 

- **0 ("클래식 ptrace 권한")**
PTRACE_MODE_ATTACH 검사를 수행하는 작업에 대한 추가적인 제한 없음 (commoncap 및 기타 LSM에 의해 부과된 제한 이상은 없음). PTRACE_TRACEME의 사용은 변경되지 않음.
- **1 ("제한된 ptrace") [기본값]**
PTRACE_MODE_ATTACH 검사를 요구하는 작업을 수행할 때, 호출 프로세스는 대상 프로세스의 사용자 네임스페이스에서 CAP_SYS_PTRACE 역량을 가졌거나 대상 프로세스와 미리 정의된 관계를 가져야 한다. 기본적으로 미리 정의된 관계는 대상 프로세스가 호출자의 자손이어야 한다는 것이다. 대상 프로세스는 대상에 대해 PTRACE_MODE_ATTACH 작업을 수행하도록 허용된 추가적인 PID를 선언하기 위해 prctl(2) PR_SET_PTRACER 작업을 고용할 수 있다. 자세한 내용은 커널 소스 파일 Documentation/admin-guide/LSM/Yama.rst (또는 리눅스 4.13 이전의 Documentation/security/Yama.txt)를 참조하라. PTRACE_TRACEME의 사용은 변경되지 않음.
- **2 ("관리자 전용 부착")**
대상 프로세스의 사용자 네임스페이스에서 CAP_SYS_PTRACE 역량을 가진 프로세스만이 PTRACE_MODE_ATTACH 작업을 수행하거나 PTRACE_TRACEME를 사용하는 자식을 추적할 수 있다.
- **3 ("부착 불가")**
어떤 프로세스도 PTRACE_MODE_ATTACH 작업을 수행하거나 PTRACE_TRACEME를 사용하는 자식을 추적할 수 없다. 이 값이 파일에 한 번 쓰여지면 변경할 수 없다.

값 1과 2에 관하여, 새로운 사용자 네임스페이스를 생성하는 것이 Yama가 제공하는 보호를 사실상 제거함에 유의하라. 이는 자식 네임스페이스 생성자의 UID와 실효 UID가 일치하는 부모 사용자 네임스페이스의 프로세스가 자식 사용자 네임스페이스(및 해당 네임스페이스의 더 먼 자손) 내에서 작업을 수행할 때 모든 역량(CAP_SYS_PTRACE 포함)을 갖기 때문이다. 결과적으로 프로세스가 자신을 샌드박스화하기 위해 사용자 네임스페이스를 사용하려고 시도할 때, 의도치 않게 Yama LSM이 제공하는 보호를 약화시킨다.

**C 라이브러리/커널 차이 (C library/kernel differences)**
시스템 호출 수준에서 PTRACE_PEEKTEXT, PTRACE_PEEKDATA, PTRACE_PEEKUSER 요청은 다른 API를 가진다: 그것들은 data 매개변수에 의해 지정된 주소에 결과를 저장하고, 반환 값은 오류 플래그이다 . glibc 래퍼 함수는 위의 설명(DESCRIPTION)에 주어진 API를 제공하며, 결과는 함수의 반환 값을 통해 반환된다.

### 결함 (BUGS)

2.6 커널 헤더가 있는 호스트에서 PTRACE_SETOPTIONS는 2.4용과는 다른 값으로 선언되어 있다. 이는 2.6 커널 헤더로 컴파일된 애플리케이션들이 2.4 커널에서 실행될 때 실패하게 만든다. 이는 PTRACE_SETOPTIONS를 PTRACE_OLDSETOPTIONS(정의되어 있다면)로 재정의함으로써 해결될 수 있다.

그룹 정지 통지는 추적자에게 전송되지만 실제 부모에게는 전송되지 않는다. 2.6.38.6에서 마지막으로 확인됨.

스레드 그룹 리더가 추적 중이고 _exit(2)를 호출하여 종료한다면, 그에 대해 PTRACE_EVENT_EXIT 정지가 (요청된 경우) 발생할 것이지만, 후속 WIFEXITED 통지는 다른 모든 스레드가 종료할 때까지 전달되지 않을 것이다. 위에서 설명한 바와 같이, 다른 스레드 중 하나가 execve(2)를 호출하면 스레드 그룹 리더의 죽음은 절대 보고되지 않을 것이다 . exec를 수행한 스레드가 이 추적자에 의해 추적되지 않는다면, 추적자는 execve(2)가 발생했음을 절대 알 수 없을 것이다. 한 가지 가능한 우회책은 이 경우 스레드 그룹 리더를 재시작하는 대신 PTRACE_DETACH하는 것이다. 2.6.38.6에서 마지막으로 확인됨.

SIGKILL 신호는 실제 신호 죽음 이전에 여전히 PTRACE_EVENT_EXIT 정지를 유발할 수 있다. 이는 미래에 변경될 수 있다; SIGKILL은 ptrace 하에서도 항상 즉시 태스크를 죽이도록 되어 있다. 리눅스 3.13에서 마지막으로 확인됨.

피추적자에게 신호가 전송되었지만 추적자에 의해 전달이 억제된 경우 일부 시스템 호출이 EINTR과 함께 반환된다. (이는 매우 전형적인 작업이다: 잘못된 SIGSTOP을 도입하지 않기 위해 보통 모든 부착 시 디버거에 의해 수행됨) . 리눅스 3.2.9 현재 다음 시스템 호출들이 영향을 받는다 (이 목록은 불완전할 가능성이 높음): epoll_wait(2), 그리고 inotify(7) 파일 기술자로부터의 read(2).

이 버그의 전형적인 증상은 다음과 같은 명령으로 정지 상태의 프로세스에 부착할 때이다:

`strace -p <process-ID>`

그러면 다음과 같은 일반적이고 기대되는 한 줄 출력 대신: 

`restart_syscall(<... 중단된 호출 재개 중 ...>`_
또는
`select(6, [5], NULL, [5], NULL_`

('_'는 커서 위치를 나타냄), 당신은 한 줄 이상의 출력을 관찰하게 된다. 예: 

`clock_gettime(CLOCK_MONOTONIC, {15370, 690928118}) = 0`
`epoll_wait(4,`_

여기서 보이지 않는 것은 strace(1)이 부착하기 전에 프로세스가 epoll_wait(2)에서 차단되어 있었다는 점이다. 부착은 epoll_wait(2)가 오류 EINTR과 함께 사용자 공간으로 반환되게 했다. 이 특정한 사례에서, 프로그램은 현재 시간을 확인한 후 다시 epoll_wait(2)를 실행함으로써 EINTR에 반응했다. (그러한 "길 잃은" EINTR 오류를 예상하지 않는 프로그램들은 strace(1) 부착 시 의도치 않은 방식으로 동작할 수 있다.) 

정상적인 규칙과 달리, ptrace()를 위한 glibc 래퍼는 errno를 0으로 설정할 수 있다.

### 참고 (SEE ALSO)

gdb(1), ltrace(1), strace(1), clone(2), execve(2), fork(2), gettid(2), prctl(2), seccomp(2), sigaction(2), tgkill(2), vfork(2), waitpid(2), exec(3), capabilities(7), signal(7)

### 대조 정보 (COLOPHON)

이 페이지는 리눅스 man-pages 프로젝트의 5.10 릴리스 일부이다. 프로젝트에 대한 설명, 버그 보고에 관한 정보, 그리고 이 페이지의 최신 버전은 [https://www.kernel.org/doc/man-pages/](https://www.kernel.org/doc/man-pages/) 에서 찾을 수 있다.

리눅스 2020-06-09 PTRACE(2) 

---

