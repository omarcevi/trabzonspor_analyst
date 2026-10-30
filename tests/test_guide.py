"""The written guide must stay true to the repo.

Every fenced block in guide/match-day-agents.md that follows a `<!-- source: path -->` comment must
appear verbatim, as one contiguous piece, in that file. Python blocks need such a marker, and every
image the guide or the README links to must exist.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "guide" / "match-day-agents.md"
BLOCK = re.compile(r"(?:<!-- source: (?P<src>\S+) -->\n)?```(?P<lang>\w*)\n(?P<code>.*?)\n```", re.S)
BLOCKS = list(BLOCK.finditer(GUIDE.read_text(encoding="utf-8")))
SOURCED = [m for m in BLOCKS if m["src"]]


def test_guide_has_code_from_the_repo():
    assert len(SOURCED) >= 8


@pytest.mark.parametrize("block", SOURCED, ids=lambda m: f"{m['src']}:{m['code'].splitlines()[0][:40]}")
def test_snippet_matches_its_source_file(block):
    source = (ROOT / block["src"]).read_text(encoding="utf-8")
    assert block["code"] in source, f"guide snippet drifted from {block['src']}"


def test_every_python_snippet_names_its_source():
    unsourced = [m["code"][:80] for m in BLOCKS if m["lang"] == "python" and not m["src"]]
    assert not unsourced, f"python snippets without <!-- source: ... -->: {unsourced}"


@pytest.mark.parametrize("doc", [GUIDE, ROOT / "README.md"], ids=["guide", "readme"])
def test_linked_images_exist(doc):
    links = re.findall(r"\]\(([^)\s]+\.(?:svg|png))", doc.read_text(encoding="utf-8"))
    assert links
    missing = [link for link in links if not (doc.parent / link).exists()]
    assert not missing, missing
