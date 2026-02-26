PROCESS_VM_READV(2) Linux 프로그래머 매뉴얼 PROCESS_VM_READV(2) 

---

### 이름 (NAME)

process_vm_readv, process_vm_writev - 프로세스 주소 공간 사이에서 데이터를 전송한다 (transfer data between process address spaces) 

---

### 시놉시스 (SYNOPSIS)

```c
#include <sys/uio.h>

ssize_t process_vm_readv(pid_t pid,
                         const struct iovec *local_iov,
                         unsigned long liovcnt,
                         const struct iovec *remote_iov,
                         unsigned long riovcnt,
                         unsigned long flags);

ssize_t process_vm_writev(pid_t pid,
                          const struct iovec *local_iov,
                          unsigned long liovcnt,
                          const struct iovec *remote_iov,
                          unsigned long riovcnt,
                          unsigned long flags);

```

---

glibc를 위한 기능 테스트 매크로 요구 사항 (Feature Test Macro Requirements for glibc):

process_vm_readv(), process_vm_writev():

- `_GNU_SOURCE`

---

### 설명 (DESCRIPTION)

이 시스템 호출들은 호출하는 프로세스("로컬 프로세스")와 pid에 의해 식별되는 프로세스("원격 프로세스")의 주소 공간 사이에서 데이터를 전송한다. 데이터는 커널 공간을 거치지 않고 두 프로세스의 주소 공간 사이에서 직접 이동한다. 

`process_vm_readv()` 시스템 호출은 원격 프로세스에서 로컬 프로세스로 데이터를 전송한다. 전송될 데이터는 `remote_iov`와 `riovcnt`에 의해 식별된다: `remote_iov`는 프로세스 pid 내의 주소 범위를 기술하는 배열에 대한 포인터이고, `riovcnt`는 `remote_iov` 내 요소의 개수를 지정한다. 데이터는 `local_iov`와 `liovcnt`에 의해 지정된 위치로 전송된다: `local_iov`는 호출하는 프로세스 내의 주소 범위를 기술하는 배열에 대한 포인터이고, `liovcnt`는 `local_iov` 내 요소의 개수를 지정한다. 

`process_vm_writev()` 시스템 호출은 `process_vm_readv()`의 반대이다—이것은 로컬 프로세스에서 원격 프로세스로 데이터를 전송한다. 전송 방향을 제외하고, 인자 `liovcnt`, `local_iov`, `riovcnt`, 그리고 `remote_iov`는 `process_vm_readv()`와 동일한 의미를 갖는다. 

`local_iov`와 `remote_iov` 인자는 `<sys/uio.h>`에 다음과 같이 정의된 `iovec` 구조체의 배열을 가리킨다: 

```c
struct iovec {
    void  *iov_base;    /* 시작 주소 (Starting address) */
    size_t iov_len;     /* 전송할 바이트 수 (Number of bytes to transfer) */
};

```

버퍼들은 배열 순서대로 처리된다. 이것은 `process_vm_readv()`가 `local_iov[1]`로 넘어가기 전에 `local_iov[0]`을 완전히 채우고, 나머지도 이와 같음을 의미한다. 마찬가지로, `remote_iov[1]`로 넘어가기 전에 `remote_iov[0]`을 완전히 읽고, 나머지도 이와 같다. 

유사하게, `process_vm_writev()`는 `local_iov[1]`로 넘어가기 전에 `local_iov[0]`의 전체 내용을 써내려가며, `remote_iov[1]`로 넘어가기 전에 `remote_iov[0]`을 완전히 채운다. 

`remote_iov[i].iov_len`과 `local_iov[i].iov_len`의 길이는 동일할 필요가 없다. 따라서 단일 로컬 버퍼를 여러 원격 버퍼로 분할하거나 그 반대로 분할하는 것이 가능하다. 

`flags` 인자는 현재 사용되지 않으며 0으로 설정되어야 한다. 

`liovcnt`와 `riovcnt` 인자에 지정된 값은 `IOV_MAX`( `<limits.h>`에 정의되어 있거나 `sysconf(_SC_IOV_MAX)` 호출을 통해 접근 가능함)보다 작거나 같아야 한다. 

개수 인자들과 `local_iov`는 어떠한 전송을 수행하기 전에 검사된다. 만약 개수가 너무 크거나, `local_iov`가 유효하지 않거나, 주소가 로컬 프로세스가 접근할 수 없는 영역을 참조하는 경우, 벡터 중 어느 것도 처리되지 않으며 즉시 오류가 반환된다. 

그러나 이 시스템 호출들은 읽기/쓰기를 수행하기 직전까지 원격 프로세스의 메모리 영역을 검사하지 않는다는 점에 유의하라. 결과적으로, 만약 `remote_iov` 요소 중 하나가 원격 프로세스의 유효하지 않은 메모리 영역을 가리킨다면 부분적인 읽기/쓰기(반환 값 섹션 참조)가 발생할 수 있다. 그 지점 이후로는 더 이상의 읽기/쓰기가 시도되지 않는다. 원격 프로세스로부터 알 수 없는 길이의 데이터(널로 종료되는 C 문자열과 같은)를 읽으려고 시도할 때, 단일 원격 `iovec` 요소가 메모리 페이지(일반적으로 4 KiB)를 가로지르는 것(spanning memory pages)을 피함으로써 이를 염두에 두어야 한다. (대신, 원격 읽기를 두 개의 `remote_iov` 요소로 분할하고 단일 쓰기 `local_iov` 항목으로 다시 병합되도록 하라. 첫 번째 읽기 항목은 페이지 경계까지 가고, 두 번째 항목은 다음 페이지 경계에서 시작한다.) 

다른 프로세스에 읽거나 쓸 수 있는 권한은 `ptrace` 액세스 모드 `PTRACE_MODE_ATTACH_REALCREDS` 검사에 의해 제어된다; `ptrace(2)`를 참조하라. 

---

### 반환 값 (RETURN VALUE)

성공 시, `process_vm_readv()`는 읽은 바이트 수를 반환하고 `process_vm_writev()`는 쓴 바이트 수를 반환한다. 부분적인 읽기/쓰기가 발생한 경우, 이 반환 값은 요청된 총 바이트 수보다 적을 수 있다.  (부분 전송은 `iovec` 요소의 단위(granularity)로 적용된다. 이 시스템 호출들은 단일 `iovec` 요소를 분할하는 부분 전송을 수행하지 않는다.) 호출자는 부분적인 읽기/쓰기가 발생했는지 확인하기 위해 반환 값을 검사해야 한다. 오류 시 -1이 반환되고 `errno`가 적절하게 설정된다. 

---

### 오류 (ERRORS)

- **EFAULT**: `local_iov`에 의해 기술된 메모리가 호출자의 접근 가능한 주소 공간 밖에 있다. 
- **EFAULT**: `remote_iov`에 의해 기술된 메모리가 프로세스 pid의 접근 가능한 주소 공간 밖에 있다. 
- **EINVAL**: `local_iov` 또는 `remote_iov` 중 하나의 `iov_len` 값의 합이 `ssize_t` 값을 초과(overflows)한다. 
- **EINVAL**: `flags`가 0이 아니다. 
- **EINVAL**: `liovcnt` 또는 `riovcnt`가 너무 크다. 
- **ENOMEM**: `iovec` 구조체의 내부 복사본을 위한 메모리를 할당할 수 없다. 
- **EPERM**: 호출자가 프로세스 pid의 주소 공간에 접근할 권한이 없다. 
- **ESRCH**: ID가 pid인 프로세스가 존재하지 않는다.

---

### 버전 (VERSIONS)

이 시스템 호출들은 Linux 3.2에서 추가되었다. 지원은 버전 2.15부터 glibc에서 제공된다. 

---

### 준수 (CONFORMING TO)

이 시스템 호출들은 비표준 Linux 확장이다. 

---

### 참고 (NOTES)

`process_vm_readv()`와 `process_vm_writev()`에 의해 수행되는 데이터 전송은 어떠한 방식으로도 원자적(atomic)임이 보장되지 않는다. 이 시스템 호출들은 (예를 들어 공유 메모리나 파이프를 사용할 때 요구되는 이중 복사(double copy)보다는) 단일 복사 작업으로 메시지를 교환할 수 있게 함으로써 빠른 메시지 전달을 허용하도록 설계되었다. 

---

### 예제 (EXAMPLES)

다음 코드 샘플은 `process_vm_readv()`의 사용을 보여준다. 이것은 PID가 10인 프로세스로부터 주소 0x10000에 있는 20바이트를 읽어 처음 10바이트는 `buf1`에, 두 번째 10바이트는 `buf2`에 쓴다. 

```c
#include <sys/uio.h>

int
main(void)
{
    struct iovec local[2];
    struct iovec remote[1];
    char buf1[10];
    char buf2[10];
    ssize_t nread;
    pid_t pid = 10; 
    /* 원격 프로세스의 PID (PID of remote process) */

    local[0].iov_base = buf1;
    local[0].iov_len = 10; 
    local[1].iov_base = buf2;
    local[1].iov_len = 10;
    remote[0].iov_base = (void *) 0x10000;
    remote[0].iov_len = 20; 
    nread = process_vm_readv(pid, local, 2, remote, 1, 0);
    if (nread != 20)
        return 1;
    else
        return 0;
} 

```

---

### 관련 항목 (SEE ALSO)

`readv(2)`, `writev(2)` 

---

### 콜로폰 (COLOPHON)

이 페이지는 Linux 매뉴얼 페이지(man-pages) 프로젝트의 5.10 릴리스의 일부이다. 프로젝트에 대한 설명, 버그 보고에 대한 정보, 그리고 이 페이지의 최신 버전은 [https://www.kernel.org/doc/man-pages/](https://www.kernel.org/doc/man-pages/) 에서 찾을 수 있다. 

Linux 2020-06-09 PROCESS_VM_READV(2) 

이 문서에 대해 더 궁금한 점이 있으신가요? 원하신다면 특정 시스템 호출의 오류 코드(ERRORS)에 대해 더 자세히 설명해 드릴 수 있습니다.