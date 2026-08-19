#!/usr/bin/env python3
"""Generate the source-derived syscall inventory for the ft_strace audit.

This script intentionally parses the X-macro rows in include/strace_data.h.
It does not import or execute the tracer, and it does not treat a table row as
proof that a syscall is semantically or fully decoded.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = REPO_ROOT / "include" / "strace_data.h"
OUTPUT_PATH = REPO_ROOT / "portfolio_audit" / "syscall_matrix.md"

ENTRY_RE = re.compile(
    r'^\s*X(?P<abi>64|32)\('
    r'\s*(?P<identifier>[^,]+),'
    r'\s*(?P<number>0x[0-9a-fA-F]+)\s*,'
    r'\s*(?P<arg_count>\d+)\s*,'
    r'\s*"(?P<name>[^"]+)"\s*,'
    r'\s*(?P<args>.*?)\s*\)\s*$'
)
SIZE_RE = re.compile(r"^\s*#\s*define\s+SYS(?P<abi>64|32)_TABLE_SIZE\s+(?P<size>0x[0-9a-fA-F]+)\s*$")

ABI_LABELS = {"64": "x86_64", "32": "i386"}

# Baseline invariants. Rows themselves always come from strace_data.h.
EXPECTED = {
    "x86_64": {
        "rows": 365,
        "slots": 470,
        "unique_names": 365,
        "zero_args": 20,
        "declared_arg_slots": 1058,
        "vstr": 2,
        "str_next_size": 11,
    },
    "i386": {
        "rows": 426,
        "slots": 470,
        "unique_names": 405,
        "zero_args": 25,
        "declared_arg_slots": 1203,
        "vstr": 2,
        "str_next_size": 9,
    },
}
EXPECTED_TOTAL_ABI_ROWS = 791
EXPECTED_UNIQUE_PRINTED_NAMES = 421


@dataclass(frozen=True)
class SyscallRow:
    abi: str
    identifier: str
    number: int
    name: str
    arg_count: int
    arg_types: tuple[str, ...]
    source_line: int

    @property
    def has_vstr(self) -> bool:
        return "ARG_VSTR" in self.arg_types

    @property
    def has_str_next_size(self) -> bool:
        return any(
            left == "ARG_STR" and right == "ARG_SIZE"
            for left, right in zip(self.arg_types, self.arg_types[1:])
        )

    @property
    def special(self) -> str:
        labels: list[str] = []
        if self.has_vstr:
            labels.append("VSTR")
        if self.has_str_next_size:
            labels.append("STR+NEXT_SIZE")
        return " + ".join(labels) if labels else "NONE"


def parse_source() -> tuple[dict[str, list[SyscallRow]], dict[str, int]]:
    rows: dict[str, list[SyscallRow]] = {"x86_64": [], "i386": []}
    sizes: dict[str, int] = {}

    for line_number, line in enumerate(SOURCE_PATH.read_text(encoding="utf-8").splitlines(), 1):
        size_match = SIZE_RE.match(line)
        if size_match:
            sizes[ABI_LABELS[size_match.group("abi")]] = int(size_match.group("size"), 16)
            continue

        entry_candidate = line.rstrip()
        if entry_candidate.endswith("\\"):
            entry_candidate = entry_candidate[:-1].rstrip()
        entry_match = ENTRY_RE.match(entry_candidate)
        if not entry_match:
            continue

        abi = ABI_LABELS[entry_match.group("abi")]
        arg_count = int(entry_match.group("arg_count"))
        all_arg_fields = tuple(part.strip() for part in entry_match.group("args").split(","))
        if len(all_arg_fields) != 6:
            raise ValueError(
                f"{SOURCE_PATH}:{line_number}: expected six argument fields, got {len(all_arg_fields)}"
            )
        if not 0 <= arg_count <= 6:
            raise ValueError(f"{SOURCE_PATH}:{line_number}: invalid arg count {arg_count}")

        declared_types = all_arg_fields[:arg_count]
        if any(arg in {"0", "ARG_NONE"} for arg in declared_types):
            raise ValueError(
                f"{SOURCE_PATH}:{line_number}: padding/ARG_NONE occurs inside declared arguments"
            )

        rows[abi].append(
            SyscallRow(
                abi=abi,
                identifier=entry_match.group("identifier").strip(),
                number=int(entry_match.group("number"), 16),
                name=entry_match.group("name"),
                arg_count=arg_count,
                arg_types=declared_types,
                source_line=line_number,
            )
        )

    for abi in rows:
        rows[abi].sort(key=lambda row: row.number)
    return rows, sizes


def compress_ranges(numbers: list[int]) -> str:
    if not numbers:
        return "NONE"

    ranges: list[tuple[int, int]] = []
    start = previous = numbers[0]
    for number in numbers[1:]:
        if number == previous + 1:
            previous = number
            continue
        ranges.append((start, previous))
        start = previous = number
    ranges.append((start, previous))

    return ", ".join(
        f"0x{start:x}" if start == end else f"0x{start:x}–0x{end:x}"
        for start, end in ranges
    )


def calculate(rows: dict[str, list[SyscallRow]], sizes: dict[str, int]) -> dict[str, dict[str, object]]:
    metrics: dict[str, dict[str, object]] = {}
    for abi, abi_rows in rows.items():
        if abi not in sizes:
            raise ValueError(f"missing table-size macro for {abi}")

        numbers = [row.number for row in abi_rows]
        if len(numbers) != len(set(numbers)):
            raise ValueError(f"duplicate syscall number in {abi} table")
        if any(number < 0 or number >= sizes[abi] for number in numbers):
            raise ValueError(f"out-of-range syscall number in {abi} table")

        populated = set(numbers)
        gaps = [number for number in range(sizes[abi]) if number not in populated]
        metrics[abi] = {
            "rows": len(abi_rows),
            "slots": sizes[abi],
            "unique_names": len({row.name for row in abi_rows}),
            "zero_args": sum(row.arg_count == 0 for row in abi_rows),
            "declared_arg_slots": sum(row.arg_count for row in abi_rows),
            "vstr": sum(row.has_vstr for row in abi_rows),
            "str_next_size": sum(row.has_str_next_size for row in abi_rows),
            "gaps": gaps,
            "gap_ranges": compress_ranges(gaps),
        }
    return metrics


def verify_invariants(
    rows: dict[str, list[SyscallRow]],
    metrics: dict[str, dict[str, object]],
) -> None:
    for abi, expected in EXPECTED.items():
        for key, expected_value in expected.items():
            actual_value = metrics[abi][key]
            if actual_value != expected_value:
                raise RuntimeError(
                    f"baseline invariant changed: {abi} {key} expected {expected_value}, got {actual_value}"
                )

    total_rows = sum(len(abi_rows) for abi_rows in rows.values())
    if total_rows != EXPECTED_TOTAL_ABI_ROWS:
        raise RuntimeError(
            f"baseline invariant changed: total ABI rows expected {EXPECTED_TOTAL_ABI_ROWS}, got {total_rows}"
        )

    unique_names = len({row.name for abi_rows in rows.values() for row in abi_rows})
    if unique_names != EXPECTED_UNIQUE_PRINTED_NAMES:
        raise RuntimeError(
            "baseline invariant changed: unique printed names expected "
            f"{EXPECTED_UNIQUE_PRINTED_NAMES}, got {unique_names}"
        )


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|")


def render_markdown(
    rows: dict[str, list[SyscallRow]],
    metrics: dict[str, dict[str, object]],
) -> str:
    total_rows = sum(len(abi_rows) for abi_rows in rows.values())
    unique_names = len({row.name for abi_rows in rows.values() for row in abi_rows})
    x64 = metrics["x86_64"]
    i386 = metrics["i386"]

    lines = [
        "# Syscall Matrix",
        "",
        "> Generated by `portfolio_audit/tools/generate_syscall_matrix.py` from "
        "`include/strace_data.h`. Do not edit this file by hand.",
        "",
        "## Definitions",
        "",
        "- **ABI row:** one populated `X64(...)` or `X32(...)` X-macro entry. Rows from different ABIs are counted separately.",
        "- **Recognized = YES:** the ABI table contains a populated row with a non-null printed name. This matches the runtime bounds/name lookup in `ft_strace.c:293-306`.",
        "- **Arguments = N/A:** the table declares zero arguments.",
        "- **Arguments = GENERIC/PARTIAL:** one or more argument slots are routed through the generic type formatter table (`ft_strace.c:187-207, 311-338`). This records rendering coverage, not proof of correct syscall-specific semantic decoding.",
        "- **Return = GENERIC/PARTIAL:** all syscall exits share the same errno-or-hex rendering branch (`ft_strace.c:341-350`); there is no syscall-specific return decoder.",
        "- **Special = VSTR:** the declared argument types contain `ARG_VSTR`.",
        "- **Special = STR+NEXT_SIZE:** an `ARG_STR` is immediately followed by `ARG_SIZE`, activating the adjacent-size behavior in `fmt_str` (`ft_strace.c:95-133`).",
        "- **Special = NONE:** neither source-derived condition is present. There are no syscall-number/name-specific decoder branches in `ft_strace.c`.",
        "",
        "A populated table row is therefore **recognition metadata**, not evidence that the syscall is fully decoded. The fully decoded count remains unknown until semantic tests are run.",
        "",
        "## Calculations",
        "",
        "| Metric | x64 | i386 | Calculation |",
        "|---|---:|---:|---|",
        f"| Declared table slots | {x64['slots']} | {i386['slots']} | `0x1d6` for each ABI (`include/strace_data.h:799-800`) |",
        f"| Populated / recognized ABI rows | {x64['rows']} / {x64['slots']} | {i386['rows']} / {i386['slots']} | Count of parsed `X64(...)` / `X32(...)` rows |",
        f"| Unpopulated slots | {len(x64['gaps'])} | {len(i386['gaps'])} | declared slots minus populated rows |",
        f"| Unique printed names within ABI | {x64['unique_names']} | {i386['unique_names']} | distinct parsed name strings |",
        f"| Zero-argument rows | {x64['zero_args']} | {i386['zero_args']} | parsed `argCount == 0` |",
        f"| Nonzero-argument generic rows | {x64['rows'] - x64['zero_args']} | {i386['rows'] - i386['zero_args']} | populated rows minus zero-argument rows |",
        f"| Declared argument slots | {x64['declared_arg_slots']} | {i386['declared_arg_slots']} | sum of parsed argument counts |",
        f"| `VSTR` rows | {x64['vstr']} | {i386['vstr']} | rows containing `ARG_VSTR` |",
        f"| `STR+NEXT_SIZE` rows | {x64['str_next_size']} | {i386['str_next_size']} | rows containing adjacent `ARG_STR, ARG_SIZE` |",
        "",
        f"Total populated ABI rows: **{total_rows}** = {x64['rows']} x64 + {i386['rows']} i386.",
        "",
        f"Unique printed names across both ABIs: **{unique_names}**. This is lower than the ABI-row total because ABIs share names and the i386 table also has multiple number-specific rows with the same printed name.",
        "",
        "## Unpopulated table slots",
        "",
        f"- x64 ({len(x64['gaps'])}): {x64['gap_ranges']}",
        f"- i386 ({len(i386['gaps'])}): {i386['gap_ranges']}",
        "",
        "These are gaps in the project's fixed table index space, **not necessarily missing Linux kernel syscalls**; reserved or unassigned numbers can also appear as gaps. Because the runtime rejects numbers outside the declared size before lookup, every number **>= `0x1d6` (470)** is rendered as unknown (`ft_strace.c:296-306`).",
        "",
        "## Populated entries",
        "",
        "| ABI | Decimal | Hex | Printed name | Arg count | Arg types | Recognized | Arguments | Return | Special | Source evidence |",
        "|---|---:|---:|---|---:|---|---|---|---|---|---|",
    ]

    for abi in ("x86_64", "i386"):
        for row in rows[abi]:
            arg_types = ", ".join(row.arg_types) if row.arg_types else "—"
            argument_status = "N/A" if row.arg_count == 0 else "GENERIC/PARTIAL"
            lines.append(
                "| "
                + " | ".join(
                    [
                        row.abi,
                        str(row.number),
                        f"0x{row.number:x}",
                        escape_cell(row.name),
                        str(row.arg_count),
                        escape_cell(arg_types),
                        "YES",
                        argument_status,
                        "GENERIC/PARTIAL",
                        row.special,
                        f"`include/strace_data.h:{row.source_line}`",
                    ]
                )
                + " |"
            )

    lines.append("")
    rendered = "\n".join(lines)
    matrix_rows = sum(
        line.startswith("| x86_64 |") or line.startswith("| i386 |")
        for line in lines
    )
    if matrix_rows != EXPECTED_TOTAL_ABI_ROWS:
        raise RuntimeError(
            f"render invariant changed: expected {EXPECTED_TOTAL_ABI_ROWS} matrix rows, got {matrix_rows}"
        )
    return rendered


def main() -> None:
    rows, sizes = parse_source()
    metrics = calculate(rows, sizes)
    verify_invariants(rows, metrics)
    OUTPUT_PATH.write_text(render_markdown(rows, metrics), encoding="utf-8")
    print(
        f"generated {OUTPUT_PATH}: "
        f"{len(rows['x86_64'])} x64 rows, {len(rows['i386'])} i386 rows, "
        f"{EXPECTED_TOTAL_ABI_ROWS} total ABI rows, {EXPECTED_UNIQUE_PRINTED_NAMES} unique names"
    )


if __name__ == "__main__":
    main()
