# ft_strace Evidence Index

이 디렉터리는 기존 ft_strace source를 수정하지 않고 commit `5a59c386c69332bd2dacc5824bf2a8958c9d9037`의 구현 범위와 정확성을 측정한 결과다.

## 빠른 결과

| 항목 | 결과 |
|---|---:|
| x86-64 populated metadata rows | 365 / 470 slots |
| i386 populated metadata rows | 426 / 470 slots |
| 전체 ABI rows | 791 |
| 두 ABI의 unique printed names | 421 |
| Fully decoded syscalls | 확인 불가 |
| Regression cases | 15 |
| PASS / PARTIAL / FAIL / CRASH | 5 / 3 / 7 / 0 |

table row 존재는 syscall 이름과 generic metadata를 lookup할 수 있다는 뜻이며 완전 지원을 뜻하지 않는다.

## 질문별 진입점

| 질문 | 문서 |
|---|---|
| 무엇을 만들었고 어떻게 동작하는가? | [`architecture.md`](architecture.md) |
| 어디까지 구현됐는가? | [`feature_inventory.md`](feature_inventory.md), [`syscall_matrix.md`](syscall_matrix.md) |
| 무엇을 어떻게 시험했는가? | [`test_plan.md`](test_plan.md), [`test_results.md`](test_results.md), [`test_results.json`](test_results.json) |
| 어디에서 왜 실패하는가? | [`failures.md`](failures.md) |
| 숫자와 환경의 기준은 무엇인가? | [`baseline.md`](baseline.md) |
| 구현자의 의도와 확인된 사실은 어떻게 구분되는가? | [`design_rationale.md`](design_rationale.md) |
| 포트폴리오에 사용할 최종 설명은 무엇인가? | [`portfolio_project.md`](portfolio_project.md) |
| 원본 실행 증거는 어디에 있는가? | [`raw/`](raw/) |

## 재현

```text
python3 portfolio_audit/tools/generate_syscall_matrix.py
python3 portfolio_audit/tools/run_baseline.py
python3 portfolio_audit/tools/run_i386_smoke.py
python3 portfolio_audit/tools/analyze_results.py
```

ptrace 실행기는 local ptrace가 허용되는 환경이 필요하다. 각 명령과 실행 metadata는 `raw/` index와 result JSON에 보존돼 있다.
