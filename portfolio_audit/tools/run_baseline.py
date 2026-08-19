#!/usr/bin/env python3
"""Build and capture the ft_strace baseline without classifying results.

The harness intentionally uses only the Python standard library.  It preserves
stdout and stderr as raw bytes and writes process metadata separately so that a
later analysis step can compare semantics without losing GNU strace output.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shlex
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


SCRIPT_PATH = Path(__file__).resolve()
AUDIT_ROOT = SCRIPT_PATH.parent.parent
REPO_ROOT = AUDIT_ROOT.parent
MANIFEST_PATH = AUDIT_ROOT / "test_manifest.json"
RAW_ROOT = AUDIT_ROOT / "raw"
BIN_ROOT = AUDIT_ROOT / "bin"

EXPECTED_COMPILE_SOURCES = [
    "t01_write_binary.c",
    "t02_write_efault.c",
    "t03_read_pipe.c",
    "t04_open_close.c",
    "t05_lseek64.c",
    "t06_newfstatat.c",
    "t07_memory.c",
    "t08_getpid.c",
    "t09_execve.c",
    "exec_target.c",
    "t10_signal.c",
    "t11_clone_descendant.c",
    "t12_socketpair.c",
    "t13_unknown.c",
    "t14_exit_status.c",
]

EXPECTED_CASE_IDS = [
    "t01_write_binary",
    "t02_write_efault",
    "t03_read_pipe",
    "t04_open_close",
    "t05_lseek64",
    "t06_newfstatat",
    "t07_memory",
    "t08_getpid",
    "t09_execve",
    "t10_signal",
    "t11_clone_descendant",
    "t12_socketpair",
    "t13_unknown",
    "t14_exit_status",
]

CAPTURE_SUFFIXES = (".command.json", ".stdout", ".stderr", ".result.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def atomic_write_json(path: Path, value: Any) -> None:
    encoded = (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    atomic_write_bytes(path, encoded)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_to_audit(path: Path) -> str:
    return path.resolve().relative_to(AUDIT_ROOT.resolve()).as_posix()


def capture_path(prefix: Path, suffix: str) -> Path:
    return prefix.parent / f"{prefix.name}{suffix}"


def clean_capture_prefix(prefix: Path) -> None:
    for suffix in CAPTURE_SUFFIXES:
        capture_path(prefix, suffix).unlink(missing_ok=True)


def command_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["LC_ALL"] = "C"
    environment["LANG"] = "C"
    return environment


def execute_process(
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: float | None,
    environment: Mapping[str, str],
) -> tuple[dict[str, Any], bytes, bytes]:
    command = [str(item) for item in argv]
    started_at = utc_now()
    started_ns = time.monotonic_ns()
    stdout = b""
    stderr = b""
    returncode: int | None = None
    timed_out = False
    spawn_error: dict[str, Any] | None = None

    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=dict(environment),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
        returncode = process.returncode
    except OSError as error:
        spawn_error = {
            "type": type(error).__name__,
            "errno": error.errno,
            "message": str(error),
        }
        stderr = str(error).encode("utf-8", errors="replace")

    duration_seconds = (time.monotonic_ns() - started_ns) / 1_000_000_000
    termination_signal: dict[str, Any] | None = None
    exit_status: int | None = None
    if returncode is not None:
        if returncode < 0:
            signal_number = -returncode
            try:
                signal_name = signal.Signals(signal_number).name
            except ValueError:
                signal_name = None
            termination_signal = {
                "number": signal_number,
                "name": signal_name,
            }
        else:
            exit_status = returncode

    result = {
        "argv": command,
        "command": shlex.join(command),
        "cwd": str(cwd.resolve()),
        "started_at_utc": started_at,
        "completed_at_utc": utc_now(),
        "duration_seconds": duration_seconds,
        "timeout_seconds": timeout_seconds,
        "timed_out": timed_out,
        "returncode": returncode,
        "exit_status": exit_status,
        "signal": termination_signal,
        "spawn_error": spawn_error,
        "stdout_bytes": len(stdout),
        "stderr_bytes": len(stderr),
    }
    return result, stdout, stderr


def capture_process(
    prefix: Path,
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: float | None,
    environment: Mapping[str, str],
    run_id: str,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    clean_capture_prefix(prefix)
    result, stdout, stderr = execute_process(
        argv,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        environment=environment,
    )
    result["run_id"] = run_id
    if context:
        result["context"] = dict(context)

    command_record: dict[str, Any] = {
        "run_id": run_id,
        "argv": result["argv"],
        "command": result["command"],
        "cwd": result["cwd"],
        "timeout_seconds": timeout_seconds,
        "stdin": "DEVNULL",
        "environment_overrides": {
            "LC_ALL": environment.get("LC_ALL"),
            "LANG": environment.get("LANG"),
        },
    }
    if context:
        command_record["context"] = dict(context)

    stdout_path = capture_path(prefix, ".stdout")
    stderr_path = capture_path(prefix, ".stderr")
    command_path = capture_path(prefix, ".command.json")
    result_path = capture_path(prefix, ".result.json")
    atomic_write_json(command_path, command_record)
    atomic_write_bytes(stdout_path, stdout)
    atomic_write_bytes(stderr_path, stderr)
    atomic_write_json(result_path, result)

    return {
        "record_prefix": relative_to_audit(prefix),
        "command_path": relative_to_audit(command_path),
        "stdout_path": relative_to_audit(stdout_path),
        "stderr_path": relative_to_audit(stderr_path),
        "result_path": relative_to_audit(result_path),
        "result": result,
    }


def probe(
    argv: Sequence[str], environment: Mapping[str, str]
) -> dict[str, Any]:
    result, stdout, stderr = execute_process(
        argv,
        cwd=REPO_ROOT,
        timeout_seconds=10,
        environment=environment,
    )
    return {
        "argv": result["argv"],
        "command": result["command"],
        "returncode": result["returncode"],
        "exit_status": result["exit_status"],
        "signal": result["signal"],
        "timed_out": result["timed_out"],
        "duration_seconds": result["duration_seconds"],
        "spawn_error": result["spawn_error"],
        "stdout": stdout.decode("utf-8", errors="replace"),
        "stderr": stderr.decode("utf-8", errors="replace"),
    }


def read_os_release() -> dict[str, Any]:
    path = Path("/etc/os-release")
    if not path.is_file():
        return {"available": False, "path": str(path)}
    raw = path.read_text(encoding="utf-8", errors="replace")
    fields: dict[str, str] = {}
    for line in raw.splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        try:
            parsed = shlex.split(value, posix=True)
            fields[key] = parsed[0] if parsed else ""
        except ValueError:
            fields[key] = value
    return {
        "available": True,
        "path": str(path),
        "fields": fields,
        "raw": raw,
    }


def record_environment(
    environment: Mapping[str, str], run_id: str
) -> dict[str, Any]:
    git_commit = probe(["git", "rev-parse", "HEAD"], environment)
    git_branch = probe(["git", "branch", "--show-current"], environment)
    git_status = probe(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        environment,
    )
    dirty = None
    if git_status["returncode"] == 0:
        dirty = bool(git_status["stdout"])

    command_paths = {
        name: shutil.which(name, path=environment.get("PATH"))
        for name in ("git", "make", "gcc", "strace")
    }
    uname = platform.uname()
    return {
        "run_id": run_id,
        "recorded_at_utc": utc_now(),
        "repo_root": str(REPO_ROOT.resolve()),
        "audit_root": str(AUDIT_ROOT.resolve()),
        "script": {
            "path": str(SCRIPT_PATH),
            "sha256": sha256_file(SCRIPT_PATH),
        },
        "manifest": {
            "path": str(MANIFEST_PATH),
            "sha256": sha256_file(MANIFEST_PATH),
        },
        "git": {
            "commit": git_commit,
            "branch": git_branch,
            "status_porcelain": git_status,
            "dirty": dirty,
        },
        "os_release": read_os_release(),
        "platform": {
            "system": uname.system,
            "node": uname.node,
            "kernel_release": uname.release,
            "kernel_version": uname.version,
            "machine": uname.machine,
            "processor": uname.processor,
            "platform": platform.platform(),
        },
        "python": {
            "executable": sys.executable,
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "command_paths": command_paths,
        "compiler_version": probe(["gcc", "--version"], environment),
        "gnu_strace_version": probe(["strace", "--version"], environment),
        "make_version": probe(["make", "--version"], environment),
        "locale_overrides": {
            "LC_ALL": environment.get("LC_ALL"),
            "LANG": environment.get("LANG"),
        },
    }


def require_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{label} must be a non-empty list of strings")
    return list(value)


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    compile_targets = manifest.get("compile_targets")
    cases = manifest.get("cases")
    engines = manifest.get("engines")
    if not isinstance(compile_targets, list):
        raise ValueError("compile_targets must be a list")
    if not isinstance(cases, list):
        raise ValueError("cases must be a list")
    if not isinstance(engines, dict):
        raise ValueError("engines must be an object")

    actual_sources = [Path(str(item.get("source", ""))).name for item in compile_targets]
    if actual_sources != EXPECTED_COMPILE_SOURCES:
        raise ValueError(
            "compile_targets must contain the exact required sources in order"
        )
    actual_case_ids = [str(item.get("id", "")) for item in cases]
    if actual_case_ids != EXPECTED_CASE_IDS:
        raise ValueError("cases must contain the exact 14 required case IDs in order")

    if float(manifest.get("case_timeout_seconds", -1)) != 5.0:
        raise ValueError("case_timeout_seconds must be exactly 5 seconds")
    if list(engines) != ["ft_strace", "gnu", "gnu_follow"]:
        raise ValueError("manifest must define ft_strace, gnu, and gnu_follow engines")

    required_flags = ["-Wall", "-Wextra", "-Werror", "-O0", "-g"]
    compiler = manifest.get("test_compiler")
    if not isinstance(compiler, dict):
        raise ValueError("test_compiler must be an object")
    if compiler.get("argv0") != "gcc" or compiler.get("flags") != required_flags:
        raise ValueError("test compiler must be gcc with the exact required flags")

    compiled_outputs = {
        str(item.get("output")) for item in compile_targets if isinstance(item, dict)
    }
    resolved_bin = BIN_ROOT.resolve()
    for item in compile_targets:
        if not isinstance(item, dict):
            raise ValueError("each compile target must be an object")
        source = (REPO_ROOT / str(item.get("source", ""))).resolve()
        output = (REPO_ROOT / str(item.get("output", ""))).resolve()
        if source.parent != (AUDIT_ROOT / "tests").resolve():
            raise ValueError(f"source outside portfolio_audit/tests: {source}")
        if output.parent != resolved_bin:
            raise ValueError(f"output outside portfolio_audit/bin: {output}")

    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("each case must be an object")
        target_argv = require_string_list(case.get("target_argv"), "target_argv")
        case_engines = require_string_list(case.get("engines"), "case engines")
        if target_argv[0] not in compiled_outputs:
            raise ValueError(f"uncompiled case target: {target_argv[0]}")
        if any(engine not in engines for engine in case_engines):
            raise ValueError(f"unknown engine in case {case.get('id')}")
        if case.get("id") == "t09_execve":
            expected = [
                "portfolio_audit/bin/t09_execve",
                "portfolio_audit/bin/exec_target",
            ]
            if target_argv != expected:
                raise ValueError("t09_execve must receive the exec_target path")
        if case.get("id") == "t11_clone_descendant":
            if case_engines != ["ft_strace", "gnu", "gnu_follow"]:
                raise ValueError("t11_clone_descendant must add gnu_follow")
        elif case_engines != ["ft_strace", "gnu"]:
            raise ValueError(f"unexpected engines for case {case.get('id')}")


def load_manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open("r", encoding="utf-8") as source:
        manifest = json.load(source)
    if not isinstance(manifest, dict):
        raise ValueError("manifest root must be an object")
    validate_manifest(manifest)
    return manifest


def checkpoint_index(index: Mapping[str, Any]) -> None:
    atomic_write_json(RAW_ROOT / "run_index.json", index)


def main() -> int:
    manifest = load_manifest()
    environment = command_environment()
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')}-{os.getpid()}"

    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    BIN_ROOT.mkdir(parents=True, exist_ok=True)
    environment_path = RAW_ROOT / "environment.json"
    environment_record = record_environment(environment, run_id)
    atomic_write_json(environment_path, environment_record)

    index: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "state": "running",
        "started_at_utc": utc_now(),
        "completed_at_utc": None,
        "repo_root": str(REPO_ROOT.resolve()),
        "manifest_path": relative_to_audit(MANIFEST_PATH),
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "environment_path": relative_to_audit(environment_path),
        "case_timeout_seconds": float(manifest["case_timeout_seconds"]),
        "build": None,
        "compilations": [],
        "cases": [],
    }
    checkpoint_index(index)

    build_config = manifest["repository_build"]
    build_argv = require_string_list(build_config.get("argv"), "build argv")
    build_timeout = float(build_config["timeout_seconds"])
    index["build"] = capture_process(
        RAW_ROOT / "build" / "make",
        build_argv,
        cwd=REPO_ROOT,
        timeout_seconds=build_timeout,
        environment=environment,
        run_id=run_id,
        context={"stage": "repository_build"},
    )
    checkpoint_index(index)

    compiler_config = manifest["test_compiler"]
    compiler = str(compiler_config["argv0"])
    compiler_flags = require_string_list(compiler_config.get("flags"), "compiler flags")
    compile_timeout = float(compiler_config["timeout_seconds"])
    for target in manifest["compile_targets"]:
        source_rel = str(target["source"])
        output_rel = str(target["output"])
        output_path = REPO_ROOT / output_rel
        output_path.unlink(missing_ok=True)
        compile_argv = [compiler, *compiler_flags, source_rel, "-o", output_rel]
        record = capture_process(
            RAW_ROOT / "compile" / Path(output_rel).name,
            compile_argv,
            cwd=REPO_ROOT,
            timeout_seconds=compile_timeout,
            environment=environment,
            run_id=run_id,
            context={
                "stage": "test_compile",
                "source": source_rel,
                "output": output_rel,
                "role": target["role"],
            },
        )
        index["compilations"].append(record)
        checkpoint_index(index)

    case_timeout = float(manifest["case_timeout_seconds"])
    engines = manifest["engines"]
    for case in manifest["cases"]:
        case_id = str(case["id"])
        target_argv = require_string_list(case.get("target_argv"), "target_argv")
        case_record: dict[str, Any] = {
            "id": case_id,
            "target_argv": target_argv,
            "engines": [],
        }
        index["cases"].append(case_record)
        checkpoint_index(index)

        for engine_name in case["engines"]:
            prefix_argv = require_string_list(
                engines[engine_name].get("prefix_argv"),
                f"{engine_name} prefix_argv",
            )
            command = [*prefix_argv, *target_argv]
            record = capture_process(
                RAW_ROOT / "cases" / case_id / engine_name,
                command,
                cwd=REPO_ROOT,
                timeout_seconds=case_timeout,
                environment=environment,
                run_id=run_id,
                context={
                    "stage": "baseline_case",
                    "case_id": case_id,
                    "engine": engine_name,
                    "engine_prefix_argv": prefix_argv,
                    "target_argv": target_argv,
                },
            )
            case_record["engines"].append(
                {
                    "name": engine_name,
                    **record,
                }
            )
            checkpoint_index(index)

    index["state"] = "complete"
    index["completed_at_utc"] = utc_now()
    checkpoint_index(index)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
