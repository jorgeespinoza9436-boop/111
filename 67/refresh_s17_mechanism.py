#!/usr/bin/env python3
"""Replace the s17 mechanism suffix in already-transformed agent files."""
from __future__ import annotations

import py_compile
import re
from pathlib import Path

MECHANISM_MARKER = "# =====================================================================\n# submittion17 MECHANISM"
MECHANISM_PATH = Path("/root/turtle/111/67/_s17_mechanism_block.py")


def refresh_file(agent_path: Path, mechanism: str) -> None:
    text = agent_path.read_text(encoding="utf-8")
    idx = text.find(MECHANISM_MARKER)
    if idx < 0:
        raise ValueError(f"no mechanism marker in {agent_path}")
    base = text[:idx].rstrip() + "\n"
    agent_path.write_text(base + mechanism, encoding="utf-8")


def main() -> None:
    mechanism = MECHANISM_PATH.read_text(encoding="utf-8")
    targets = [
        Path("/root/turtle/111/67/sub17-unsubmitted"),
        Path("/root/turtle/111/67/submittion17"),
    ]
    ok = 0
    for root in targets:
        if not root.is_dir():
            continue
        for agent in sorted(root.glob("uid_*.py")):
            try:
                refresh_file(agent, mechanism)
                py_compile.compile(str(agent), doraise=True)
                ok += 1
                print(f"OK {agent}")
            except Exception as exc:
                print(f"FAIL {agent}: {exc}")
    print(f"refreshed {ok} agents")


if __name__ == "__main__":
    main()
