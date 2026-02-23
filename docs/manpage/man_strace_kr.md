STRACE(1) 일반 명령 매뉴얼 STRACE(1) 

## 이름 (NAME)

strace - 시스템 호출과 신호를 추적한다 

## 개요 (SYNOPSIS)

strace [-ACdffhikqqrtttTvVwxxyyzZ] [-I n] [-b execve] [-e expr]... [-O overhead] [-S sortby] [-U columns] [-a column] [-o file] [-s strsize] [-X format] [-P path]... [-p pid]... [--seccomp-bpf] { -p pid | [-DDD] [-E var[=val]]... [-u username] command [args] } 

strace -c [-dfwzZ] [-I n] [-b execve] [-e expr]... [-O overhead] [-S sortby] [-U columns] [-P path]... [-p pid]... [--seccomp-bpf] { -p pid | [-DDD] [-E var[=val]]... [-u username] command [args] } 

---

## 설명 (DESCRIPTION)

가장 단순한 경우에 strace는 지정된 명령이 종료될 때까지 실행한다. 이것은 프로세스에 의해 호출되는 시스템 호출과 프로세스에 의해 수신되는 신호들을 가로채고 기록한다. 각 시스템 호출의 이름, 그것의 인자들(arguments) 그리고 그것의 반환 값은 표준 오류(standard error) 혹은 -o 옵션으로 지정된 파일에 출력된다. 

strace는 유용한 진단, 교육 및 디버깅 도구이다. 시스템 관리자, 진단가 및 트러블슈터들은 소스를 쉽게 사용할 수 없는 프로그램들에 대한 문제를 해결하는 데 있어 이것이 매우 가치 있음을 알게 될 것인데, 왜냐하면 그것들을 추적하기 위해 재컴파일할 필요가 없기 때문이다. 학생들, 해커들 및 과도하게 호기심 많은 사람들은 평범한 프로그램들조차 추적함으로써 시스템과 시스템 호출들에 대해 아주 많은 것을 배울 수 있다는 것을 알게 될 것이다. 그리고 프로그래머들은 시스템 호출과 신호가 사용자/커널 인터페이스에서 발생하는 이벤트들이기 때문에, 이 경계에 대한 면밀한 조사가 버그 격리, 무결성 검사(sanity checking) 및 경쟁 상태(race conditions) 포착 시도에 매우 유용하다는 것을 알게 될 것이다. 

추적의 각 줄은 시스템 호출 이름을 포함하며, 괄호 안의 인자들과 반환 값이 그 뒤를 잇는다. "cat /dev/null" 명령을 strace한 예시는 다음과 같다: 

`open("/dev/null", O_RDONLY) = 3`

오류(전형적으로 -1의 반환 값)는 errno 심볼과 오류 문자열이 추가된다. `open("/foo/bar", O_RDONLY) = -1 ENOENT (No such file or directory)` 

신호들은 신호 심볼과 디코딩된 siginfo 구조체로 출력된다. "sleep 666" 명령을 strace하고 중단(interrupting)했을 때의 발췌본은 다음과 같다: 

```
sigsuspend([] <unfinished ...>
--- SIGINT {si_signo=SIGINT, si_code=SI_USER, si_pid=...} ---
+++ killed by SIGINT +++

```

만약 시스템 호출이 실행 중이고 그동안 다른 스레드/프로세스에서 또 다른 호출이 불린다면, strace는 해당 이벤트들의 순서를 보존하려고 시도하며 진행 중인 호출을 미완료(unfinished)로 표시한다. 호출이 반환될 때 그것은 재개됨(resumed)으로 표시될 것이다. 

```
[pid 28772] select(4, [3], NULL, NULL, NULL <unfinished ...>
[pid 28779] clock_gettime(CLOCK_REALTIME, {1130322148, 939977000}) = 0
[pid 28772] <... select resumed> )      = 1 (in [3])

```

신호 전달에 의한 (재시작 가능한) 시스템 호출의 중단은 커널이 시스템 호출을 종료하고 신호 처리기(signal handler)가 완료된 후 즉시 재실행을 준비하기 때문에 다르게 처리된다. 

```
read(0, 0x7ffff72cf5cf, 1)              = ?
ERESTARTSYS (To be restarted)
--- SIGALRM ... ---
rt_sigreturn(0xe)                       = 0
read(0, "", 1)                          = 0
``` 

인자들은 열정적으로 심볼릭 형식(symbolic form)으로 출력된다.  이 예시는 셸이 ">>xyzzy" 출력 리다이렉션을 수행하는 것을 보여준다: 

`open("xyzzy", O_WRONLY|O_APPEND|O_CREAT, 0666) = 3`

여기서 open(2)의 두 번째와 세 번째 인자는 플래그 인자를 세 개의 비트별 OR 구성 요소로 분해하고 전통에 따라 모드 값을 8진수(octal)로 출력함으로써 디코딩된다.  전통적이거나 고유한(native) 용법이 ANSI 혹은 POSIX와 다른 경우, 후자의 형식이 선호된다.  어떤 경우에는 strace 출력이 소스보다 더 읽기 쉬운 것으로 증명되기도 한다.  구조체 포인터는 역참조(dereferenced)되고 멤버들은 적절하게 표시된다.  대부분의 경우, 인자들은 가능한 한 C 언어와 유사한 방식으로 형식화된다.  예를 들어, "ls -l /dev/null" 명령의 본질은 다음과 같이 캡처된다: 

`lstat("/dev/null", {st_mode=S_IFCHR|0666, st_rdev=makedev(0x1, 0x3), ...}) = 0`

'struct stat' 인자가 어떻게 역참조되는지 그리고 각 멤버가 어떻게 심볼릭하게 표시되는지 주목하라.  특히, st_mode 멤버가 심볼릭 값과 숫자 값의 비트별 OR로 어떻게 신중하게 디코딩되는지 관찰하라.  또한 이 예시에서 lstat(2)에 대한 첫 번째 인자는 시스템 호출에 대한 입력이고 두 번째 인자는 출력임에 주목하라.  시스템 호출이 실패할 경우 출력 인자들은 수정되지 않으므로, 인자들이 항상 역참조되지는 않을 수 있다.  예를 들어, 존재하지 않는 파일로 "ls -l" 예시를 재시도하면 다음과 같은 줄이 생성된다: 

`lstat("/foo/bar", 0xb004) = -1 ENOENT (No such file or directory)`

이 경우 현관 불은 켜져 있지만 집에는 아무도 없다. (the porch light is on but nobody is home) 

strace에게 알려지지 않은 시스템 호출들은 원시(raw) 형태로 출력되며, 알려지지 않은 시스템 호출 번호는 16진수 형식으로 출력되고 "syscall_" 접두사가 붙는다: 

`syscall_0xbad(0x1, 0x2, 0x3, 0x4, 0x5, 0x6) = -1 ENOSYS (Function not implemented)`

문자 포인터는 역참조되어 C 문자열로 출력된다.  문자열 내의 비출력 문자들은 일반적으로 평범한 C 이스케이프 코드로 표현된다.  문자열의 처음 strsize(기본값 32) 바이트만 출력된다;  더 긴 문자열은 닫는 따옴표 뒤에 생략 부호(ellipsis)가 추가된다.  다음은 getpwuid(3) 라이브러리 루틴이 패스워드 파일을 읽고 있는 "ls -l"의 한 줄이다: 

`read(3, "root::0:0:System Administrator:/"..., 1024) = 422`

구조체는 중괄호를 사용하여 주석 처리되는 반면, 단순 포인터와 배열은 대괄호를 사용하고 요소를 쉼표로 구분하여 출력된다.  다음은 보조 그룹 ID를 가진 시스템에서 id(1) 명령을 실행한 예시이다: 

`getgroups(32, [100, 0]) = 2`

반면에, 비트 세트(bit-sets) 또한 대괄호를 사용하여 표시되지만, 세트 요소들은 공백으로만 구분된다.  다음은 외부 명령 실행을 준비하는 셸이다: 

`sigprocmask(SIG_BLOCK, [CHLD TTOU], []) = 0`

여기서 두 번째 인자는 두 개의 신호 SIGCHLD와 SIGTTOU의 비트 세트이다.  어떤 경우에는 비트 세트가 너무 가득 차서 설정되지 않은 요소들을 출력하는 것이 더 가치 있다.  그 경우, 비트 세트 앞에는 다음과 같이 틸데(tilde)가 붙는다: 

`sigprocmask(SIG_UNBLOCK, ~[], NULL) = 0`

여기서 두 번째 인자는 모든 신호의 전체 세트를 나타낸다. 

---

## 옵션 (OPTIONS)

### 일반 (General)
* **-e expr**: 추적할 이벤트 또는 추적 방법을 수정하는 한정 표현식(qualifying expression).  표현식의 형식은 다음과 같다: `[qualifier=][!]value[,value]...`  여기서 한정자(qualifier)는 trace (또는 t), abbrev (또는 a), verbose (또는 v), raw (또는 x), signal (또는 signals 또는 s), read (또는 reads 또는 r), write (또는 writes 또는 w), fault, inject, status, quiet (또는 silent 또는 silence 또는 q), decode-fds (또는 decode-fd), decode-pids (또는 decode-pid), 또는 kvm 중 하나이며, value는 한정자 의존적인 심볼 혹은 숫자이다.  기본 한정자는 trace이다. 느낌표를 사용하는 것은 값의 집합을 부정한다.  예를 들어, -e open은 문자 그대로 -e trace=open을 의미하며 이는 오직 open 시스템 호출만 추적함을 의미한다.  대조적으로, -e trace=!open은 open을 제외한 모든 시스템 호출을 추적함을 의미한다.  추가적으로, 특수 값 all과 none은 명백한 의미를 가진다.  일부 셸은 따옴표로 묶인 인자 내부에서도 느낌표를 히스토리 확장(history expansion)으로 사용함에 주의하라.  그렇다면 느낌표를 백슬래시로 이스케이프해야 한다. 

### 시작 (Startup)
* **-E var=val / --env=var=val**: 환경 변수 목록에 var=val을 포함하여 명령을 실행한다. 
* **-E var / --env=var**: 명령에 전달하기 전에 상속된 환경 변수 목록에서 var를 제거한다. 
* **-p pid / --attach=pid**: 프로세스 ID가 pid인 프로세스에 연결(attach)하여 추적을 시작한다.  추적은 키보드 인터럽트 신호(CTRL-C)에 의해 언제든지 종료될 수 있다.  strace는 추적 중인 프로세스(들)로부터 자신을 분리(detaching)하여 그것들이 계속 실행되도록 남겨둠으로써 응답할 것이다.  여러 개의 -p 옵션을 사용하여 명령(적어도 하나의 -p 옵션이 주어지면 선택 사항임) 외에도 많은 프로세스에 연결할 수 있다.  쉼표(“,”), 공백(“ ”), 탭 또는 줄바꿈 문자로 구분된 다중 프로세스 ID를 단일 -p 옵션의 인자로 제공할 수 있으므로, 예를 들어 -p "$(pidof PROG)" 및 -p "$(pgrep PROG)" 구문이 지원된다. 
* **-u username / --user=username**: username의 사용자 ID, 그룹 ID 및 보조 그룹으로 명령을 실행한다.  이 옵션은 루트로 실행할 때만 유용하며 setuid 및/또는 setgid 바이너리의 올바른 실행을 가능하게 한다.  이 옵션이 사용되지 않는 한 setuid 및 setgid 프로그램은 실효 권한(effective privileges) 없이 실행된다. 

### 추적 (Tracing)
* **-b syscall / --detach-on=syscall**: 지정된 syscall에 도달하면 추적 중인 프로세스에서 분리한다.  현재 execve(2) syscall만 지원된다.  이 옵션은 다중 스레드 프로세스를 추적하고 싶어서 -f가 필요하지만, 그것의 (잠재적으로 매우 복잡한) 자식들은 추적하고 싶지 않을 때 유용하다. 
* **-D / --daemonize / --daemonize=grandchild**: 추적기(tracer) 프로세스를 피추적자(tracee)의 부모가 아닌 손주(grandchild)로 실행한다.  이것은 피추적자를 호출 프로세스의 직계 자식으로 유지함으로써 strace의 가시적 효과를 줄인다. 
* **-DD / --daemonize=pgroup / --daemonize=pgrp**: 추적기 프로세스를 별도의 프로세스 그룹에 있는 피추적자의 손주로 실행한다.  strace의 가시적 효과 감소 외에도, 전체 프로세스 그룹에 발행된 kill(2)로 인해 strace가 죽는 것을 방지한다. 
* **-DDD / --daemonize=session**: 추적기 프로세스를 별도의 세션에 있는 피추적자의 손주로 실행한다("진정한 데몬화").  strace의 가시적 효과 감소 외에도, 세션 종료 시 strace가 죽는 것을 방지한다. 
* **-f / --follow-forks**: fork(2), vfork(2) 및 clone(2) 시스템 호출의 결과로 현재 추적 중인 프로세스에 의해 생성된 자식 프로세스들을 추적한다.  다중 스레드인 경우 -p PID -f는 thread_id = PID인 스레드뿐만 아니라 프로세스 PID의 모든 스레드에 연결됨에 주의하라. 
* **--output-separately**: --output=filename 옵션이 유효한 경우, 각 프로세스의 추적은 filename.pid에 기록되며 여기서 pid는 각 프로세스의 숫자 프로세스 ID이다. 
* **-ff / --follow-forks --output-separately**: --follow-forks와 --output-separately 옵션의 효과를 결합한다.  프로세스별 카운트가 유지되지 않으므로 -c와 호환되지 않는다.  결합된 strace 로그 뷰를 얻기 위해 strace-log-merge(1) 사용을 고려할 수 있다. 
* **-I interruptible / --interruptible=interruptible**: strace가 신호(CTRL-C 누르기 등)에 의해 중단될 수 있는 시점. 
    * 1, anywhere: 어떠한 신호도 차단되지 않음; 
    * 2, waiting: syscall 디코딩 중 치명적 신호가 차단됨(기본값); 
    * 3, never: 치명적 신호가 항상 차단됨(-o FILE PROG인 경우 기본값); 
    * 4, never_tstp: 치명적 신호와 SIGTSTP (CTRL-Z)가 항상 차단됨 (strace -o FILE PROG가 CTRL-Z에서 멈추지 않게 하는 데 유용함, -D인 경우 기본값). 

### 필터링 (Filtering)
* **-e trace=syscall_set / --trace=syscall_set**: 지정된 시스템 호출 세트만 추적한다.  syscall_set은 [!]value[,value]로 정의되며, value는 다음 중 하나일 수 있다: 
    * syscall: 이름으로 지정된 특정 syscall을 추적한다(단, NOTES 참조). 
    * ?value: syscall 한정자 앞의 물음표는 제공된 한정자와 일치하는 syscall이 없는 경우 오류 억제를 허용한다. 
    * /regex: 정규식과 일치하는 시스템 호출만 추적한다.  POSIX 확장 정규식 구문을 사용할 수 있다(regex(7) 참조). 
    * syscall@64: 64비트 퍼스낼리티에 대해서만 syscall을 추적한다. 
    * syscall@32: 32비트 퍼스낼리티에 대해서만 syscall을 추적한다. 
    * syscall@x32: 64비트 위 32비트(32-on-64-bit) 퍼스낼리티에 대해서만 syscall을 추적한다. 
    * %file / file: 파일 이름을 인자로 받는 모든 시스템 호출을 추적한다.  이것은 프로세스가 어떤 파일을 참조하는지 확인하는 데 유용한 -e trace=open,stat,chmod,unlink,... 의 약어로 생각할 수 있다.  또한 약어를 사용하면 목록에 lstat(2)과 같은 호출을 포함하는 것을 실수로 잊지 않도록 보장한다.  퍼센트 기호가 없는 구문("-e trace=file")은 더 이상 권장되지 않는다(deprecated). 
    * %process / process: 프로세스 생명 주기(생성, 실행, 종료)와 관련된 시스템 호출을 추적한다.  (퍼센트 없는 구문은 권장되지 않음). 
    * %network / %net / network: 모든 네트워크 관련 시스템 호출을 추적한다.  (퍼센트 없는 구문은 권장되지 않음). 
    * %signal / signal: 모든 신호 관련 시스템 호출을 추적한다.  (퍼센트 없는 구문은 권장되지 않음). 
    * %ipc / ipc: 모든 IPC 관련 시스템 호출을 추적한다.  (퍼센트 없는 구문은 권장되지 않음). 
    * %desc / desc: 모든 파일 서술자(file descriptor) 관련 시스템 호출을 추적한다.  (퍼센트 없는 구문은 권장되지 않음). 
    * %memory / memory: 모든 메모리 매핑 관련 시스템 호출을 추적한다.  (퍼센트 없는 구문은 권장되지 않음). 
    * %creds: 사용자 및 그룹 식별자 또는 기능 세트(capability sets)를 읽거나 수정하는 시스템 호출을 추적한다. 
    * %stat / %lstat / %fstat: 각각 stat, lstat, fstat(및 관련 변종) syscall을 추적한다. 
    * %%stat: 파일 상태 요청에 사용되는 모든 syscall을 추적한다. 
    * %statfs: statfs 관련 시스템 호출을 추적한다.  -e trace=/^(.*_)?statv?fs 정규식으로 동일한 효과를 낼 수 있다. 
    * %fstatfs: fstatfs 관련 시스템 호출을 추적한다.  -e trace=/fstatv?fs 정규식으로 동일한 효과를 낼 수 있다. 
    * %%statfs: 파일 시스템 통계와 관련된 syscall을 추적한다.  -e trace=/statv?fs|fsstat|ustat 정규식으로 동일한 효과를 낼 수 있다. 
    * %clock: 시스템 클럭을 읽거나 수정하는 시스템 호출을 추적한다. 
    * %pure: 항상 성공하고 인자가 없는 syscall을 추적한다. 

-c 옵션은 어떤 시스템 호출을 추적하는 것이 유용할지 결정하는 데 도움이 된다.  예를 들어, trace=open,close,read,write는 오직 그 네 개의 시스템 호출만 추적함을 의미한다.  시스템 호출의 하위 집합만 모니터링할 경우 사용자/커널 경계에 대한 추론을 내릴 때 주의하라.  기본값은 trace=all이다. 

* **-e signal=set / --signal=set**: 지정된 신호의 하위 집합만 추적한다.  기본값은 signal=all이다. 
* **-e status=set / --status=set**: 지정된 반환 상태를 가진 시스템 호출만 출력한다.  기본값은 status=all이다.  status 한정자를 사용할 때 strace는 시스템 호출이 반환될 때까지 기다렸다가 출력 여부를 결정하므로 전통적인 이벤트 순서가 더 이상 보존되지 않을 수 있다.  set은 successful, failed, unfinished, unavailable, detached를 포함할 수 있다. 
* **-P path / --trace-path=path**: path에 액세스하는 시스템 호출만 추적한다.  여러 경로를 지정하기 위해 다중 -P 옵션을 사용할 수 있다. 
* **-z / --successful-only**: 오류 코드 없이 반환된 syscall만 출력한다. 
* **-Z / --failed-only**: 오류 코드와 함께 반환된 syscall만 출력한다. 

### 출력 형식 (Output format)
* **-a column / --columns=column**: 반환 값을 특정 열에 맞춘다(기본값 40). 
* **-e abbrev=syscall_set**: 큰 구조체의 각 멤버를 출력하는 것을 축약한다.  기본값은 abbrev=all이며, -v 옵션은 abbrev=none의 효과를 갖는다. 
* **-e verbose=syscall_set**: 지정된 시스템 호출 세트에 대해 구조체를 역참조한다.  기본값은 verbose=all이다. 
* **-e raw=syscall_set**: 지정된 시스템 호출 세트에 대해 디코딩되지 않은 원시 인자를 출력한다.  모든 인자가 16진수로 출력되게 한다. 
* **-e read=set / --read=set**: 지정된 세트에 나열된 파일 서술자로부터 읽은 모든 데이터의 전체 16진수 및 ASCII 덤프를 수행한다. 
* **-e write=set / --write=set**: 지정된 세트에 나열된 파일 서술자에 기록된 모든 데이터의 전체 16진수 및 ASCII 덤프를 수행한다. 
* **-e quiet=set / --quiet=set**: 다양한 정보 메시지를 억제한다.  set은 attach, exit, path-resolution, personality, thread-execve 등을 포함할 수 있다. 
* **-e decode-fds=set**: 파일 서술자와 관련된 다양한 정보를 디코딩한다.  set은 path, socket, dev, pidfd를 포함할 수 있다. 
* **-e decode-pids=set**: 프로세스 ID와 관련된 다양한 정보를 디코딩한다.  set은 comm, pidns를 포함할 수 있다. 
* **-e kvm=vcpu**: kvm vcpu의 종료 이유를 출력한다. 
* **-i / --instruction-pointer**: 시스템 호출 시점의 명령 포인터(instruction pointer)를 출력한다. 
* **-n / --syscall-number**: syscall 번호를 출력한다. 
* **-k / --stack-traces**: 각 시스템 호출 후 추적된 프로세스의 실행 스택 추적을 출력한다. 
* **-o filename / --output=filename**: 추적 출력을 stderr 대신 filename 파일에 기록한다.  인자가 '|' 또는 '!'로 시작하면 나머지 인자는 명령으로 간주되어 모든 출력이 그 명령으로 파이프된다. 
* **-A / --output-append-mode**: -o 옵션에 제공된 파일을 추가(append) 모드로 연다. 
* **-q / --quiet**: 연결, 분리 및 퍼스낼리티 변경에 대한 메시지를 억제한다. 
* **-qq / -qqq**: 각각 종료 상태를 포함하거나 모든 억제 가능한 메시지를 억제한다. 
* **-r / --relative-timestamps**: 각 시스템 호출 진입 시 상대적 타임스탬프를 출력한다.  연속적인 시스템 호출 시작 사이의 시간 차이를 기록한다. 
* **-s strsize / --string-limit=strsize**: 출력할 최대 문자열 크기를 지정한다(기본값 32).  파일 이름은 문자열로 간주되지 않으며 항상 전체가 출력된다. 
* **--absolute-timestamps / -t**: 각 추적 줄 앞에 벽시계 시간(wall clock time)을 접두사로 붙인다.  -tt는 마이크로초를 포함하며, -ttt는 에포크(epoch) 이후 초 수를 포함한다. 
* **-T / --syscall-times**: 시스템 호출에서 보낸 시간을 표시한다. 
* **-v / --no-abbrev**: 환경, stat, termios 등 호출의 축약되지 않은 버전을 출력한다. 
* **--strings-in-hex**: 출력되는 문자열에서 16진수가 포함된 이스케이프 시퀀스의 사용을 제어한다. 
* **-x / -xx**: 각각 비 ASCII 문자열 또는 모든 문자열을 16진수 문자열 형식으로 출력한다. 
* **-X format / --const-print-style=format**: 명명된 상수 및 플래그의 출력 형식을 설정한다(raw, abbrev, verbose). 
* **-y / -yy**: 파일 서술자와 관련된 경로 또는 모든 가용 정보를 출력한다. 
* **-Y**: PID에 대한 명령 이름을 출력한다. 

### 통계 (Statistics)
* **-c / --summary-only**: 각 시스템 호출에 대한 시간, 호출 횟수 및 오류를 계산하고 프로그램 종료 시 요약을 보고하며 일반 출력을 억제한다. 
* **-C / --summary**: -c와 같지만 프로세스가 실행되는 동안 일반 출력도 수행한다. 
* **-O overhead**: 시스템 호출 추적에 대한 오버헤드를 설정한다. 
* **-S sortby**: -c 옵션에 의해 출력되는 히스토그램의 출력을 지정된 기준으로 정렬한다(time, calls, errors, name 등). 
* **-U columns**: 호출 요약에 표시되는 열 세트(및 순서)를 구성한다. 
* **-w / --summary-wall-clock**: 각 시스템 호출의 시작과 끝 사이의 시간 차이를 요약한다. 

### 변조 (Tampering)
* **-e inject=syscall_set[:options]**: 지정된 시스템 호출 세트에 대해 시스템 호출 변조를 수행한다.  error, retval, signal, delay, poke 등을 주입할 수 있다.  :when=expr를 사용하여 주입 시점을 지정할 수 있다. 
* **-e fault=syscall_set[:error=errno][:when=expr]**: 지정된 시스템 호출 세트에 대해 시스템 호출 결함 주입(fault injection)을 수행한다.  이는 errno 기본값이 ENOSYS로 설정된 더 일반적인 -e inject= 표현식과 동일하다. 

### 기타 (Miscellaneous)
* **-d / --debug**: strace 자체의 일부 디버깅 출력을 표준 오류에 표시한다. 
* **-F**: 이 옵션은 권장되지 않는다(deprecated).  하위 호환성을 위해서만 유지된다. 
* **-h / --help**: 도움말 요약을 출력한다. 
* **--seccomp-bpf**: seccomp-bpf를 사용하여 추적 중인 시스템 호출이 발생할 때만 ptrace-stop이 발생하도록 시도를 한다.  -f 옵션이 지정되어야 효과가 있다. 
* **-V / --version**: strace의 버전 번호를 출력한다. 

---

## 시간 사양 형식 설명 (Time specification format description)
시간 값은 십진 부동 소수점 숫자로 지정할 수 있으며, 선택적으로 s (초), ms (밀리초), us (마이크로초) 또는 ns (나노초) 접미사가 붙을 수 있다.  접미사가 없으면 값은 마이크로초로 해석된다.  이 형식은 -O, -e inject=delay_enter 및 -e inject=delay_exit 옵션에 사용된다. 

## 진단 (DIAGNOSTICS)
명령이 종료되면 strace는 동일한 종료 상태로 종료된다.  명령이 신호에 의해 종료되면 strace도 동일한 신호로 자신을 종료하여, strace가 호출 부모 프로세스에 투명한 래퍼 프로세스로 사용될 수 있게 한다.  -D가 사용되지 않는 한 피추적 프로세스와 그 부모 사이의 부모-자식 관계는 유지되지 않음에 주의하라.  명령 없이 -p를 사용할 때, strace의 종료 상태는 프로세스가 연결되지 않았거나 추적 중에 예기치 않은 오류가 발생하지 않는 한 0이다. 

## SETUID 설치 (SETUID INSTALLATION)
strace가 루트에 대해 setuid로 설치되면 호출 사용자는 모든 사용자가 소유한 프로세스에 연결하고 추적할 수 있다.  또한 setuid 및 setgid 프로그램이 올바른 실효 권한으로 실행되고 추적될 것이다.  전체 루트 권한을 가진 신뢰할 수 있는 사용자만 이러한 작업을 수행할 수 있어야 하므로, strace를 루트에 대해 setuid로 설치하는 것은 이를 실행할 수 있는 사용자가 신뢰받는 사용자로 제한될 때만 의미가 있다.  이 기능을 사용한다면 일반 사용자가 사용할 수 있도록 일반적인 비 setuid 버전의 strace도 설치하는 것을 잊지 마라. 

## 다중 퍼스낼리티 지원 (MULTIPLE PERSONALITIES SUPPORT)
일부 아키텍처에서 strace는 strace가 사용하는 것과 다른 ABI를 사용하는 프로세스에 대한 syscall 디코딩을 지원한다.  x86_64는 i386 및 x32를 지원하며, AArch64는 ARM 32-bit EABI를 지원하는 등 다양하다.  사용 가능한 지원 사항을 파악하려면 strace -V 명령의 출력을 참조하라. 

## 참고 (NOTES)
공유 라이브러리를 사용하는 시스템에서 너무 많은 추적 혼란(clutter)이 발생하는 것은 안타까운 일이다.  시스템 호출 입출력을 사용자/커널 경계를 가로지르는 데이터 흐름으로 생각하는 것이 교육적이다.  어떤 경우에는 시스템 호출이 문서화된 동작과 다르거나 다른 이름을 가질 수 있다.  예를 들어 faccessat(2)은 flags 인자가 없으며, setrlimit(2) 라이브러리 함수는 현대 커널에서 prlimit64(2) 시스템 호출을 사용한다.  일부 플랫폼에서 -p 옵션으로 연결된 프로세스는 재시작 불가능한 현재 시스템 호출로부터 가짜(spurious) EINTR 반환을 관찰할 수 있다.  strace는 지정된 명령을 직접 실행하고 셸을 사용하지 않으므로, 셸에서 실행되는 쉬뱅(shebang) 없는 스크립트는 ENOEXEC 오류로 실행에 실패한다. 

## 버그 (BUGS)
setuid 비트를 사용하는 프로그램은 추적되는 동안 실효 사용자 ID 권한을 갖지 못한다.  추적된 프로세스는 느리게 실행된다(하지만 --seccomp-bpf 옵션을 확인하라).  명령의 자손인 추적된 프로세스들은 인터럽트 신호(CTRL-C) 이후에도 계속 실행 중일 수 있다. 

## 역사 (HISTORY)
원래 strace는 Paul Kranenburg가 SunOS용으로 작성했으며 해당 시스템의 trace 유틸리티에서 영감을 받았다.  SunOS 버전의 strace는 Linux로 포팅되었고 Linux 커널 지원을 작성한 Branko Lankester에 의해 강화되었다.  1993년 Rick Sladkey가 통합하였고, 1996년부터 Wichert Akkerman이, 2002년부터 Roland McGrath가 유지보수했다.  2009년부터 strace는 Dmitry Levin에 의해 활발히 유지보수되고 있다. 

## 버그 보고 (REPORTING BUGS)
strace의 문제는 strace 메일링 리스트 ⟨mailto:strace-devel@lists.strace.io⟩로 보고해야 한다. 

## 참고 문헌 (SEE ALSO)
strace-log-merge(1), ltrace(1), perf-trace(1), trace-cmd(1), time(1), ptrace(2), proc(5) 

strace 홈 페이지 ⟨[https://strace.io/](https://strace.io/)⟩

## 저자 (AUTHORS)
strace 기여자들의 전체 목록은 CREDITS 파일에서 찾을 수 있다. 

strace 5.16 2022-01-04 STRACE(1) 

---