#!/usr/bin/env python3
"""Build and capture the freestanding i386 compatibility smoke case."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve()
AUDIT_ROOT = SCRIPT.parent.parent
REPO_ROOT = AUDIT_ROOT.parent
BASELINE_RUNNER = SCRIPT.parent / "run_baseline.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("baseline_capture", BASELINE_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load run_baseline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    runner = load_runner()
    environment = runner.command_environment()
    run_id = "i386-" + runner.utc_now().replace(":", "").replace("-", "")
    raw_root = AUDIT_ROOT / "raw"
    case_root = raw_root / "cases" / "t15_i386_smoke"
    object_path = AUDIT_ROOT / "bin" / "t15_i386_smoke.o"
    binary_path = AUDIT_ROOT / "bin" / "t15_i386_smoke"
    source_rel = "portfolio_audit/tests/t15_i386_smoke.S"
    object_rel = "portfolio_audit/bin/t15_i386_smoke.o"
    binary_rel = "portfolio_audit/bin/t15_i386_smoke"

    object_path.unlink(missing_ok=True)
    binary_path.unlink(missing_ok=True)
    assemble = runner.capture_process(
        raw_root / "compile" / "t15_i386_smoke_as",
        ["as", "--32", source_rel, "-o", object_rel],
        cwd=REPO_ROOT,
        timeout_seconds=30,
        environment=environment,
        run_id=run_id,
        context={"stage": "i386_assemble"},
    )
    link = runner.capture_process(
        raw_root / "compile" / "t15_i386_smoke_ld",
        ["ld", "-m", "elf_i386", object_rel, "-o", binary_rel],
        cwd=REPO_ROOT,
        timeout_seconds=30,
        environment=environment,
        run_id=run_id,
        context={"stage": "i386_link"},
    )

    engines = []
    if assemble["result"]["returncode"] == 0 and link["result"]["returncode"] == 0:
        for name, prefix in (("ft_strace", ["./ft_strace"]), ("gnu", ["strace"])):
            record = runner.capture_process(
                case_root / name,
                [*prefix, binary_rel],
                cwd=REPO_ROOT,
                timeout_seconds=5,
                environment=environment,
                run_id=run_id,
                context={
                    "stage": "i386_baseline_case",
                    "case_id": "t15_i386_smoke",
                    "engine": name,
                    "target_argv": [binary_rel],
                },
            )
            engines.append({"name": name, **record})

    record = {
        "schema_version": 1,
        "run_id": run_id,
        "source": source_rel,
        "object": object_rel,
        "binary": binary_rel,
        "assemble": assemble,
        "link": link,
        "engines": engines,
    }
    runner.atomic_write_json(raw_root / "i386_run_index.json", record)
    print(json.dumps({
        "assemble_returncode": assemble["result"]["returncode"],
        "link_returncode": link["result"]["returncode"],
        "engines": [
            {
                "name": item["name"],
                "returncode": item["result"]["returncode"],
                "timed_out": item["result"]["timed_out"],
            }
            for item in engines
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

