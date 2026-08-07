#!/usr/bin/env python3
"""Inject the s18 requirement-coverage gap-filling mechanism into every
agent in 111/67/18, writing results to 111/67/submittion18.

For each source file:
  1. Locate the single @entrypoint("query") / async def query(query: Query)
     -> Response: block (regex tolerant of extra whitespace / quote style).
  2. Rename that function to `_s18_base_query` and drop the decorator, so
     the original pipeline becomes an internal helper.
  3. Append the s18 mechanism block, which defines a NEW `query` entrypoint
     that calls `_s18_base_query` and then runs the requirement-coverage
     gap-filling pass (text and structured-output modes) on its output.
  4. py_compile the result.
"""
from __future__ import annotations

import py_compile
import re
import sys
from pathlib import Path

SRC_DIR = Path("/root/turtle/111/67/18")
DST_DIR = Path("/root/turtle/111/67/submittion18")
MECHANISM_PATH = Path("/root/turtle/111/67/_s18_mechanism_block.py")

ENTRYPOINT_PATTERN = re.compile(
    r"@entrypoint\s*\(\s*(['\"])query\1\s*\)\s*\n\s*async\s+def\s+query\s*\(\s*(\w+)\s*:\s*Query\s*\)\s*->\s*Response\s*:"
)


def transform(text: str, mechanism: str) -> str:
    matches = list(ENTRYPOINT_PATTERN.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"expected exactly 1 entrypoint match, found {len(matches)}")
    m = matches[0]
    param = m.group(2)
    replacement = f"async def _s18_base_query({param}: Query) -> Response:"
    new_text = text[: m.start()] + replacement + text[m.end():]
    if not new_text.endswith("\n"):
        new_text += "\n"
    new_text += mechanism
    return new_text


def main() -> int:
    DST_DIR.mkdir(parents=True, exist_ok=True)
    mechanism = MECHANISM_PATH.read_text(encoding="utf-8")

    src_files = sorted(SRC_DIR.glob("*.py"))
    print(f"Found {len(src_files)} source agents in {SRC_DIR}")

    failures = []
    ok_count = 0
    for src in src_files:
        text = src.read_text(encoding="utf-8")
        try:
            new_text = transform(text, mechanism)
        except ValueError as exc:
            failures.append((src.name, f"transform: {exc}"))
            continue

        dst = DST_DIR / src.name
        dst.write_text(new_text, encoding="utf-8")

        try:
            py_compile.compile(str(dst), doraise=True)
        except py_compile.PyCompileError as exc:
            failures.append((src.name, f"compile: {exc}"))
            continue

        ok_count += 1

    print(f"\nOK: {ok_count}/{len(src_files)}")
    if failures:
        print(f"FAILURES: {len(failures)}")
        for name, reason in failures:
            print(f"  {name}: {reason}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
