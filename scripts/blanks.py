"""The workshop's blanks. On the main branch each step's key code is missing: a two-line
✏️ BLANK marker sits in its place, and the guide shows the code to paste over it.
The demo branch has every blank filled.

    uv run python scripts/blanks.py list               # which blanks are still empty
    uv run python scripts/blanks.py fill 2a 2b         # fell behind? paste the guide's code for you
    uv run python scripts/blanks.py fill all           # everything (the same code as the demo branch)
    uv run python scripts/blanks.py make all           # maintainers: turn the guide's code back into blanks

The guide marks each pasteable block with <!-- source: path blank: ID --> right above it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "guide" / "match-day-agents.md"
BLOCK = re.compile(r"<!-- source: (?P<path>\S+) blank: (?P<id>\w+) -->\n```\w*\n(?P<code>.*?)\n```", re.S)
MARKER = re.compile(r"^(?P<indent>[ ]*)# ✏️ BLANK (?P<id>\w+) · .*\n(?P=indent)raise NotImplementedError\(.*\)\n", re.M)


def guide_blanks(guide: str | None = None) -> dict[str, dict]:
    """Every blank in the guide: its file, the code to paste, and the guide section it is in."""
    text = guide if guide is not None else GUIDE.read_text(encoding="utf-8")
    blanks = {}
    for m in BLOCK.finditer(text):
        section = re.findall(r"^## (.+)$", text[: m.start()], re.M)[-1]
        blanks[m["id"]] = {"path": m["path"], "code": m["code"], "section": section}
    return blanks


def marker(blank_id: str, blank: dict) -> str:
    indent = re.match(r"[ ]*", blank["code"]).group()
    where = f"the guide, {blank['section']}"
    return (f"{indent}# ✏️ BLANK {blank_id} · paste the code from {where} over these two lines\n"
            f'{indent}raise NotImplementedError("BLANK {blank_id} is still empty: paste the code from {where}")\n')


def fill(text: str, blanks: dict[str, dict], ids: set[str] | None = None) -> str:
    """Replace BLANK markers with the guide's code."""
    def put(m):
        if m["id"] not in blanks or (ids is not None and m["id"] not in ids):
            return m.group()
        return blanks[m["id"]]["code"] + "\n"
    return MARKER.sub(put, text)


def make(text: str, path: str, blanks: dict[str, dict], ids: set[str] | None = None) -> str:
    """Replace the guide's code with BLANK markers."""
    for blank_id, blank in blanks.items():
        if blank["path"] == path and (ids is None or blank_id in ids) and blank["code"] + "\n" in text:
            text = text.replace(blank["code"] + "\n", marker(blank_id, blank), 1)
    return text


def empty(text: str) -> list[str]:
    return [m["id"] for m in MARKER.finditer(text)]


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("list", "fill", "make"):
        print(__doc__)
        return 2
    command, wanted = argv[0], argv[1:]
    blanks = guide_blanks()
    ids = None if not wanted or "all" in wanted else set(wanted)
    if ids and (unknown := ids - set(blanks)):
        print(f"unknown blank(s): {', '.join(sorted(unknown))}. Blanks in the guide: {', '.join(blanks)}")
        return 2
    for path in sorted({b["path"] for b in blanks.values()}):
        file = ROOT / path
        text = file.read_text(encoding="utf-8")
        if command == "list":
            print(f"{path}: {', '.join(empty(text)) or 'all filled'}")
            continue
        new = fill(text, blanks, ids) if command == "fill" else make(text, path, blanks, ids)
        if new != text:
            file.write_text(new, encoding="utf-8")
            print(f"{command}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
