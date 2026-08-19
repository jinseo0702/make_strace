#!/usr/bin/env python3
"""Verify raw baseline evidence and generate classified result artifacts.

Classifications are explicit policy decisions, but every decision is guarded by
case-specific assertions against the captured ft_strace and GNU strace output.
If an expected observation changes, generation stops rather than silently
reusing a stale classification.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
AUDIT_ROOT = SCRIPT.parent.parent
REPO_ROOT = AUDIT_ROOT.parent
RAW_ROOT = AUDIT_ROOT / "raw"


CASE_SPECS: list[dict[str, Any]] = [
    {
        "id": "t01_write_binary",
        "title": "binary write escaping",
        "category": "File I/O",
        "syscalls": ["write"],
        "classification": "PASS",
        "expected": "write fd 1 with bytes 41 00 42 0a, length 4, return 4",
        "actual": "The same four bytes and return value are recoverable; ft_strace uses decimal backslash escapes (`\\0`, `\\10`).",
        "reason": "The byte payload, length, return, tracee stdout, and sequence match after the documented escape normalization.",
        "ft_lines": [["write(1, \"A\\0B\\10\", 4)", "= 0x4"]],
        "ref_lines": [["write(1, \"A\\0B\\n\", 4)", "= 4"]],
        "stdout": "4100420a",
    },
    {
        "id": "t02_write_efault",
        "title": "invalid write pointer",
        "category": "File I/O / error",
        "syscalls": ["write"],
        "classification": "FAIL",
        "expected": "display pointer 0x1 and return EFAULT",
        "actual": "ft_strace displays a fabricated 16-byte zero buffer, then reports Bad address.",
        "reason": "Ignoring the failed process_vm_readv changes a core argument from pointer 0x1 to data that was never read.",
        "ft_lines": [["write(1, \"\\0\\0", "16) = -1 Bad address"]],
        "ref_lines": [["write(1, 0x1, 16)", "EFAULT"]],
        "stdout": "",
    },
    {
        "id": "t03_read_pipe",
        "title": "read output buffer timing",
        "category": "File I/O",
        "syscalls": ["read", "write"],
        "classification": "FAIL",
        "expected": "read(fd, \"READ\", 4) = 4 after the kernel fills the buffer",
        "actual": "ft_strace prints the pre-syscall sentinel `XXXX` instead of the returned bytes `READ`.",
        "reason": "A core output argument is wrong because all arguments are formatted at syscall entry.",
        "ft_lines": [["read(3, \"XXXX\", 4) = 0x4"]],
        "ref_lines": [["read(3, \"READ\", 4)", "= 4"]],
        "stdout": "",
    },
    {
        "id": "t04_open_close",
        "title": "openat/close success and ENOENT",
        "category": "Filesystem",
        "syscalls": ["openat", "close"],
        "classification": "PASS",
        "expected": "open /dev/null, close fd 3, then receive ENOENT for a nonexistent path",
        "actual": "Names, numeric dirfd/flags, paths, fd, success returns, and errno meaning match; only symbolic formatting differs.",
        "reason": "AT_FDCWD=-100, O_RDONLY=0, hexadecimal success values, and strerror text are semantically equivalent.",
        "ft_lines": [
            ["openat(-100, \"/dev/null\", 0x0, 0) = 0x3"],
            ["close(3) = 0x0"],
            ["openat(-100, \"/proc/self/fd/2147483647\", 0x0, 0)", "No such file or directory"],
        ],
        "ref_lines": [
            ["openat(AT_FDCWD, \"/dev/null\", O_RDONLY)", "= 3"],
            ["close(3)", "= 0"],
            ["openat(AT_FDCWD, \"/proc/self/fd/2147483647\", O_RDONLY)", "ENOENT"],
        ],
        "stdout": "",
    },
    {
        "id": "t05_lseek64",
        "title": "64-bit lseek offset",
        "category": "File I/O",
        "syscalls": ["lseek"],
        "classification": "FAIL",
        "expected": "lseek offset 4294967298 with the same return value",
        "actual": "ft_strace prints the argument as 2 while the kernel returns 0x100000002.",
        "reason": "The high 32 bits of a core argument are lost by the int formatter.",
        "ft_lines": [["lseek(3, 2, 0) = 0x100000002"]],
        "ref_lines": [["lseek(3, 4294967298, SEEK_SET)", "= 4294967298"]],
        "stdout": "",
    },
    {
        "id": "t06_newfstatat",
        "title": "newfstatat output structure",
        "category": "Filesystem",
        "syscalls": ["newfstatat"],
        "classification": "PARTIAL",
        "expected": "path and successful stat result including the kernel-produced stat structure",
        "actual": "ft_strace recognizes the syscall/path and return 0 but prints only the structure address.",
        "reason": "The syscall is traced correctly while a significant output structure is omitted rather than misreported.",
        "ft_lines": [["newfstatat(-100, \"/dev/null\", 0x", ", 0x0) = 0x0"]],
        "ref_lines": [["newfstatat(AT_FDCWD, \"/dev/null\", {st_mode=S_IFCHR", "= 0"]],
        "stdout": "",
    },
    {
        "id": "t07_memory",
        "title": "mmap/mprotect/munmap sequence",
        "category": "Memory",
        "syscalls": ["mmap", "mprotect", "munmap"],
        "classification": "PASS",
        "expected": "map one 4096-byte RW anonymous page, protect it read-only, then unmap it",
        "actual": "All numeric arguments, success returns, and sequence match after address and symbolic-flag normalization.",
        "reason": "Raw numeric protection/map flags retain the same semantic values as GNU's symbolic rendering.",
        "ft_lines": [
            ["mmap(0x0, 0x1000, 0x3, 0x22, -1, 0x0) = 0x"],
            ["mprotect(0x", ", 4096, 0x1) = 0x0"],
            ["munmap(0x", ", 4096) = 0x0"],
        ],
        "ref_lines": [
            ["mmap(NULL, 4096, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0)", "= 0x"],
            ["mprotect(0x", ", 4096, PROT_READ) = 0"],
            ["munmap(0x", ", 4096)", "= 0"],
        ],
        "stdout": "",
    },
    {
        "id": "t08_getpid",
        "title": "zero-argument getpid",
        "category": "Process",
        "syscalls": ["getpid"],
        "classification": "PASS",
        "expected": "getpid() with a positive PID return",
        "actual": "ft_strace reports a positive hexadecimal PID; GNU reports a different positive decimal PID from its separate run.",
        "reason": "PID is a documented dynamic value and the syscall name, arity, and return semantics match.",
        "ft_lines": [["getpid() = 0x"]],
        "ref_lines": [["getpid()", "= 2"]],
        "stdout": "",
    },
    {
        "id": "t09_execve",
        "title": "execve process-image replacement and exit status",
        "category": "Process",
        "syscalls": ["execve"],
        "classification": "FAIL",
        "expected": "decode helper path/argv, continue after exec, report exit 23, and return status 23 from the tracer",
        "actual": "The exec path, argv, continued tracing after process-image replacement, and `exited with 23` line are correct, but ft_strace itself returns 0 while GNU strace returns 23.",
        "reason": "Tracee exit-status propagation is declared core behavior for this case and is wrong.",
        "ft_lines": [
            ["execve(\"portfolio_audit/bin/exec_target\"", "\"alpha\", \"beta\""],
            ["+++ exited with 23 +++"],
        ],
        "ref_lines": [
            ["execve(\"portfolio_audit/bin/exec_target\"", "\"alpha\", \"beta\"", "0 vars"],
            ["+++ exited with 23 +++"],
        ],
        "stdout": "",
        "expected_ft_return": 0,
        "expected_ref_return": 23,
    },
    {
        "id": "t10_signal",
        "title": "signal installation and reinjection",
        "category": "Signal",
        "syscalls": ["rt_sigaction", "kill"],
        "classification": "PARTIAL",
        "expected": "install SIGUSR1 handler, send SIGUSR1 to self, deliver it, and exit 0",
        "actual": "ft_strace preserves delivery and execution but prints numeric/raw action fields and abbreviated siginfo.",
        "reason": "Core signal behavior works; symbolic signal/action structure detail is omitted.",
        "ft_lines": [
            ["rt_sigaction(0xa, 0x", ", 0x0, 8) = 0x0"],
            ["kill(", ", 0xa) = 0x0"],
            ["--- USR1 {si_signo=USR1"],
        ],
        "ref_lines": [
            ["rt_sigaction(SIGUSR1, {sa_handler=", "= 0"],
            ["kill(", ", SIGUSR1)", "= 0"],
            ["--- SIGUSR1 {si_signo=SIGUSR1"],
        ],
        "stdout": "",
    },
    {
        "id": "t11_clone_descendant",
        "title": "clone descendant tracing",
        "category": "Process",
        "syscalls": ["clone"],
        "classification": "FAIL",
        "expected": "observe clone plus the child's write and exit when measured against GNU strace -f",
        "actual": "ft_strace observes parent clone/wait and the program succeeds, but no child syscall appears in its trace.",
        "reason": "A central descendant-tracing behavior is absent; GNU's follow run records the child write and exit.",
        "reference": "gnu_follow",
        "ft_lines": [["clone(0x11, 0x0, 0x0, 0x0, 0x0) = 0x"]],
        "ref_lines": [
            ["clone(child_stack=NULL, flags=SIGCHLD"],
            ["write(1, \"clone-child\\n\", 12) = 12"],
            ["+++ exited with 42 +++"],
        ],
        "ft_absent": ["write(1, \"clone-child"],
        "stdout": "636c6f6e652d6368696c640a",
    },
    {
        "id": "t12_socketpair",
        "title": "socketpair output descriptors",
        "category": "Network",
        "syscalls": ["socketpair"],
        "classification": "PARTIAL",
        "expected": "AF_UNIX/SOCK_STREAM success with returned descriptors [3, 4]",
        "actual": "ft_strace records numeric domain/type/protocol and success but leaves the fd array as an address.",
        "reason": "The syscall completes correctly while kernel-produced output detail is omitted.",
        "ft_lines": [["socketpair(1, 1, 0, 0x", ") = 0x0"]],
        "ref_lines": [["socketpair(AF_UNIX, SOCK_STREAM, 0, [3, 4]) = 0"]],
        "stdout": "",
    },
    {
        "id": "t13_unknown",
        "title": "unknown syscall fallback",
        "category": "Control",
        "syscalls": [],
        "classification": "PASS",
        "expected": "identify syscall number 999 as unknown and report ENOSYS",
        "actual": "ft_strace prints decimal 999 with `Function not implemented`; GNU prints hexadecimal 0x3e7 with ENOSYS.",
        "reason": "The syscall number and errno meaning match after numeric and errno-text normalization.",
        "ft_lines": [["syscall_999(/* unknown */) = -1 Function not implemented"]],
        "ref_lines": [["syscall_0x3e7(", "ENOSYS (Function not implemented)"]],
        "stdout": "",
    },
    {
        "id": "t14_exit_status",
        "title": "tracee exit-status propagation",
        "category": "Control",
        "syscalls": [],
        "classification": "FAIL",
        "expected": "report tracee exit 7 and return 7 from the tracer",
        "actual": "ft_strace reports `exited with 7` but returns 0; GNU strace returns 7.",
        "reason": "The observable wrapper exit status is wrong.",
        "ft_lines": [["+++ exited with 7 +++"]],
        "ref_lines": [["+++ exited with 7 +++"]],
        "stdout": "",
        "expected_ft_return": 0,
        "expected_ref_return": 7,
    },
    {
        "id": "t15_i386_smoke",
        "title": "i386 errno compatibility",
        "category": "ABI compatibility",
        "syscalls": ["getpid", "write"],
        "classification": "FAIL",
        "expected": "recognize 32-bit mode, getpid, and render write(0x1,16) as -1 EFAULT",
        "actual": "32-bit mode and getpid work, but ft_strace prints a zero-filled buffer and treats -14 as successful hex `0xfffffff2`.",
        "reason": "Unsigned i386 eax handling loses negative errno semantics, and failed memory reading also changes the argument.",
        "ft_lines": [
            ["runs in 32 bit mode"],
            ["getpid() = 0x"],
            ["write(1, \"\\0\\0", "16) = 0xfffffff2"],
        ],
        "ref_lines": [
            ["runs in 32 bit mode"],
            ["getpid()", "= 2"],
            ["write(1, 0x1, 16)", "EFAULT"],
        ],
        "stdout": "",
    },
]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def find_line(text: str, parts: list[str], label: str) -> str:
    for candidate in text.splitlines():
        if all(part in candidate for part in parts):
            return candidate
    raise RuntimeError(f"missing evidence for {label}: {parts!r}")


def engine_result(case_id: str, engine: str) -> dict[str, Any]:
    return read_json(RAW_ROOT / "cases" / case_id / f"{engine}.result.json")


def assert_healthy(result: dict[str, Any], label: str) -> None:
    if result.get("timed_out"):
        raise RuntimeError(f"unexpected timeout: {label}")
    if result.get("spawn_error") is not None:
        raise RuntimeError(f"spawn error: {label}: {result['spawn_error']}")
    if result.get("signal") is not None:
        raise RuntimeError(f"unexpected engine signal: {label}: {result['signal']}")


def source_inventory() -> dict[str, Any]:
    header = read_text(REPO_ROOT / "include" / "strace_data.h")
    x64_names = re.findall(r'^X64\(.*?"([^"]+)"', header, flags=re.MULTILINE)
    x32_names = re.findall(r'^X32\(.*?"([^"]+)"', header, flags=re.MULTILINE)
    size_match = re.search(r'SYS64_TABLE_SIZE\s+0x([0-9a-fA-F]+)', header)
    if size_match is None:
        raise RuntimeError("SYS64_TABLE_SIZE not found")
    slots = int(size_match.group(1), 16)
    observed = (len(x64_names), len(x32_names), slots, len(set(x64_names + x32_names)))
    expected = (365, 426, 470, 421)
    if observed != expected:
        raise RuntimeError(f"source inventory changed: expected {expected}, got {observed}")
    return {
        "x86_64_recognized_rows": len(x64_names),
        "i386_recognized_rows": len(x32_names),
        "table_slots_per_abi": slots,
        "total_abi_rows": len(x64_names) + len(x32_names),
        "unique_printed_names": len(set(x64_names + x32_names)),
        "fully_decoded_entire_table": None,
        "fully_decoded_note": "확인 불가: 15 focused cases do not prove semantic completeness for all populated table rows.",
    }


def verify_builds() -> dict[str, Any]:
    build = read_json(RAW_ROOT / "build" / "make.result.json")
    assert_healthy(build, "default make")
    if build.get("returncode") != 0:
        raise RuntimeError("default make did not succeed")
    main_compiles = sorted((RAW_ROOT / "compile").glob("*.result.json"))
    main_compiles = [p for p in main_compiles if "t15_i386" not in p.name]
    if len(main_compiles) != 15:
        raise RuntimeError(f"expected 15 gcc compile records, found {len(main_compiles)}")
    for path in main_compiles:
        result = read_json(path)
        assert_healthy(result, path.name)
        if result.get("returncode") != 0:
            raise RuntimeError(f"test compilation failed: {path.name}")
    i386 = read_json(RAW_ROOT / "i386_run_index.json")
    for stage in ("assemble", "link"):
        result = i386[stage]["result"]
        assert_healthy(result, f"i386 {stage}")
        if result.get("returncode") != 0:
            raise RuntimeError(f"i386 {stage} failed")
    return {
        "default_make_returncode": build["returncode"],
        "gcc_compile_records": len(main_compiles),
        "gcc_case_binaries": 14,
        "gcc_helper_binaries": 1,
        "i386_assemble_returncode": i386["assemble"]["result"]["returncode"],
        "i386_link_returncode": i386["link"]["result"]["returncode"],
    }


def analyze_case(spec: dict[str, Any]) -> dict[str, Any]:
    case_id = spec["id"]
    reference = spec.get("reference", "gnu")
    ft_result = engine_result(case_id, "ft_strace")
    ref_result = engine_result(case_id, reference)
    assert_healthy(ft_result, f"{case_id}/ft_strace")
    assert_healthy(ref_result, f"{case_id}/{reference}")
    expected_ft_return = spec.get("expected_ft_return", 0)
    expected_ref_return = spec.get("expected_ref_return", 0)
    if ft_result.get("returncode") != expected_ft_return:
        raise RuntimeError(f"unexpected ft_strace return for {case_id}: {ft_result.get('returncode')}")
    if ref_result.get("returncode") != expected_ref_return:
        raise RuntimeError(f"unexpected reference return for {case_id}: {ref_result.get('returncode')}")

    case_root = RAW_ROOT / "cases" / case_id
    ft_text = read_text(case_root / "ft_strace.stderr")
    ref_text = read_text(case_root / f"{reference}.stderr")
    ft_evidence = [
        find_line(ft_text, parts, f"{case_id}/ft_strace") for parts in spec["ft_lines"]
    ]
    ref_evidence = [
        find_line(ref_text, parts, f"{case_id}/{reference}") for parts in spec["ref_lines"]
    ]
    if case_id == "t07_memory":
        ft_mmap = find_line(
            ft_text,
            ["mmap(0x0, 0x1000, 0x3, 0x22, -1, 0x0) = 0x"],
            "t07_memory target ft mmap",
        )
        ft_match = re.search(r"= (0x[0-9a-f]+)$", ft_mmap)
        if ft_match is None:
            raise RuntimeError("cannot extract t07 ft_strace mmap address")
        ft_address = ft_match.group(1)
        ft_evidence = [
            ft_mmap,
            find_line(ft_text, [f"mprotect({ft_address}, 4096, 0x1) = 0x0"], "t07 target ft mprotect"),
            find_line(ft_text, [f"munmap({ft_address}, 4096) = 0x0"], "t07 target ft munmap"),
        ]

        ref_mmap = find_line(
            ref_text,
            ["mmap(NULL, 4096, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0)", "= 0x"],
            "t07_memory target GNU mmap",
        )
        ref_match = re.search(r"= (0x[0-9a-f]+)$", ref_mmap)
        if ref_match is None:
            raise RuntimeError("cannot extract t07 GNU mmap address")
        ref_address = ref_match.group(1)
        ref_evidence = [
            ref_mmap,
            find_line(ref_text, [f"mprotect({ref_address}, 4096, PROT_READ) = 0"], "t07 target GNU mprotect"),
            find_line(ref_text, [f"munmap({ref_address}, 4096)", "= 0"], "t07 target GNU munmap"),
        ]
    for forbidden in spec.get("ft_absent", []):
        if forbidden in ft_text:
            raise RuntimeError(f"unexpected ft_strace evidence for {case_id}: {forbidden!r}")

    ft_stdout = read_bytes(case_root / "ft_strace.stdout")
    ref_stdout = read_bytes(case_root / f"{reference}.stdout")
    expected_stdout = bytes.fromhex(spec["stdout"])
    if ft_stdout != expected_stdout or ref_stdout != expected_stdout:
        raise RuntimeError(
            f"stdout mismatch for {case_id}: ft={ft_stdout.hex()} ref={ref_stdout.hex()} expected={expected_stdout.hex()}"
        )

    return {
        "id": case_id,
        "title": spec["title"],
        "category": spec["category"],
        "target_syscalls": spec["syscalls"],
        "classification": spec["classification"],
        "expected": spec["expected"],
        "actual": spec["actual"],
        "reason": spec["reason"],
        "normalization_applied": [
            "dynamic PID/address values",
            "equivalent decimal/hex integers",
            "equivalent errno symbol/text",
            "documented equivalent byte escaping",
            "numeric versus symbolic flags with the same value",
        ],
        "reference_engine": reference,
        "engine_results": {
            "ft_strace": {
                "returncode": ft_result["returncode"],
                "timed_out": ft_result["timed_out"],
                "signal": ft_result["signal"],
                "stderr_path": f"raw/cases/{case_id}/ft_strace.stderr",
                "stdout_path": f"raw/cases/{case_id}/ft_strace.stdout",
                "result_path": f"raw/cases/{case_id}/ft_strace.result.json",
                "evidence_lines": ft_evidence,
            },
            reference: {
                "returncode": ref_result["returncode"],
                "timed_out": ref_result["timed_out"],
                "signal": ref_result["signal"],
                "stderr_path": f"raw/cases/{case_id}/{reference}.stderr",
                "stdout_path": f"raw/cases/{case_id}/{reference}.stdout",
                "result_path": f"raw/cases/{case_id}/{reference}.result.json",
                "evidence_lines": ref_evidence,
            },
        },
        "verified_assertions": len(ft_evidence) + len(ref_evidence) + 5,
    }


def markdown(results: dict[str, Any]) -> str:
    summary = results["summary"]
    lines = [
        "# ft_strace Baseline Test Results",
        "",
        f"- Main run ID: `{results['raw_runs']['x86_64']}`",
        f"- i386 run ID: `{results['raw_runs']['i386']}`",
        f"- Generated: `{results['generated_at_utc']}`",
        "- Existing source changes: none (verified separately in `baseline.md`)",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Regression tests | {summary['tests']} |",
        f"| PASS | {summary['PASS']} |",
        f"| PARTIAL | {summary['PARTIAL']} |",
        f"| FAIL | {summary['FAIL']} |",
        f"| CRASH | {summary['CRASH']} |",
        f"| Selected syscall names | {summary['selected_syscall_names']} |",
        "",
        "The full-table `Fully decoded syscalls` count is **확인 불가**. The suite measures 15 focused cases, not every populated ABI row.",
        "",
        "## Classification table",
        "",
        "| Case | Category | Target syscall(s) | Result | Evidence-backed finding |",
        "|---|---|---|---|---|",
    ]
    for item in results["tests"]:
        targets = ", ".join(f"`{name}`" for name in item["target_syscalls"]) or "control"
        actual = item["actual"].replace("|", "\\|")
        lines.append(
            f"| `{item['id']}` | {item['category']} | {targets} | **{item['classification']}** | {actual} |"
        )
    lines += [
        "",
        "## Per-case evidence",
        "",
    ]
    for item in results["tests"]:
        lines += [
            f"### {item['id']} — {item['classification']}",
            "",
            f"- Expected: {item['expected']}",
            f"- Actual: {item['actual']}",
            f"- Decision: {item['reason']}",
            "- ft_strace evidence:",
        ]
        for evidence in item["engine_results"]["ft_strace"]["evidence_lines"]:
            lines.append(f"  - `{evidence}`")
        reference = item["reference_engine"]
        lines.append(f"- {reference} evidence:")
        for evidence in item["engine_results"][reference]["evidence_lines"]:
            lines.append(f"  - `{evidence}`")
        lines.append("")
    lines += [
        "## Reproduction",
        "",
        "```text",
        "python3 portfolio_audit/tools/run_baseline.py",
        "python3 portfolio_audit/tools/run_i386_smoke.py",
        "python3 portfolio_audit/tools/analyze_results.py",
        "```",
        "",
        "The two ptrace runners require an environment that permits local ptrace. Raw commands, outputs, and result metadata are under `raw/`.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    main_index = read_json(RAW_ROOT / "run_index.json")
    i386_index = read_json(RAW_ROOT / "i386_run_index.json")
    if main_index.get("state") != "complete":
        raise RuntimeError("main baseline run is not complete")
    builds = verify_builds()
    tests = [analyze_case(spec) for spec in CASE_SPECS]
    counts = Counter(item["classification"] for item in tests)
    selected = sorted({name for item in tests for name in item["target_syscalls"]})
    expected_selected = sorted([
        "write", "read", "lseek", "openat", "close", "newfstatat",
        "mmap", "mprotect", "munmap", "getpid", "execve", "clone",
        "rt_sigaction", "kill", "socketpair",
    ])
    if selected != expected_selected:
        raise RuntimeError(f"selected syscall set changed: {selected}")
    summary = {
        "tests": len(tests),
        "PASS": counts["PASS"],
        "PARTIAL": counts["PARTIAL"],
        "FAIL": counts["FAIL"],
        "CRASH": counts["CRASH"],
        "selected_syscall_names": len(selected),
    }
    expected_summary = {
        "tests": 15,
        "PASS": 5,
        "PARTIAL": 3,
        "FAIL": 7,
        "CRASH": 0,
        "selected_syscall_names": 15,
    }
    if summary != expected_summary:
        raise RuntimeError(f"unexpected classification totals: {summary}")
    results = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "commit": "5a59c386c69332bd2dacc5824bf2a8958c9d9037",
        "raw_runs": {
            "x86_64": main_index["run_id"],
            "i386": i386_index["run_id"],
        },
        "classification_policy": "test_plan.md",
        "source_inventory": source_inventory(),
        "builds": builds,
        "summary": summary,
        "selected_syscalls": selected,
        "tests": tests,
    }
    (AUDIT_ROOT / "test_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (AUDIT_ROOT / "test_results.md").write_text(markdown(results), encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
