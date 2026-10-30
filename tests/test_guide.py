"""The written guide must stay true to the repo, on both branches.

Every fenced block after a `<!-- source: path -->` comment must appear verbatim in that file.
Blocks marked `<!-- source: path blank: ID -->` are the code participants paste over a ✏️ BLANK
on the main branch, so they are checked against the file with its blanks filled from the guide
(on the demo branch the file already has them). The filled code must compile, build all six
agents, and match the demo branch when it is available. Linked images must exist.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import blanks  # noqa: E402

GUIDE = ROOT / "guide" / "match-day-agents.md"
BLOCK = re.compile(r"(?:<!-- source: (?P<src>\S+)(?: blank: (?P<blank>\w+))? -->\n)?```(?P<lang>\w*)\n(?P<code>.*?)\n```", re.S)
BLOCKS = list(BLOCK.finditer(GUIDE.read_text(encoding="utf-8")))
SOURCED = [m for m in BLOCKS if m["src"]]
BLANKS = blanks.guide_blanks()
STEP_FILES = sorted((ROOT / "steps").glob("*/agent.py"))


def filled(path: str) -> str:
    return blanks.fill((ROOT / path).read_text(encoding="utf-8"), BLANKS)


def test_guide_has_code_from_the_repo_and_blanks_for_every_step():
    assert len(SOURCED) >= 8
    assert {b["path"] for b in BLANKS.values()} == {f"steps/step{n}_{s}/agent.py" for n, s in (
        (1, "scout"), (2, "match_prep"), (3, "scouting_dept"), (4, "tribun"), (5, "technical_director"))}


@pytest.mark.parametrize("block", SOURCED, ids=lambda m: f"{m['src']}:{m['blank'] or m['code'].splitlines()[0][:40]}")
def test_snippet_matches_its_source_file(block):
    assert block["code"] in filled(block["src"]), f"guide snippet drifted from {block['src']}"


def test_every_python_snippet_names_its_source():
    unsourced = [m["code"][:80] for m in BLOCKS if m["lang"] == "python" and not m["src"]]
    assert not unsourced, f"python snippets without <!-- source: ... -->: {unsourced}"


@pytest.mark.parametrize("blank_id", sorted(BLANKS))
def test_each_blank_is_either_empty_or_filled_with_the_guide_code(blank_id):
    blank = BLANKS[blank_id]
    text = (ROOT / blank["path"]).read_text(encoding="utf-8")
    is_empty, is_filled = blank_id in blanks.empty(text), blank["code"] + "\n" in text
    assert is_empty != is_filled, f"BLANK {blank_id} in {blank['path']}: empty={is_empty} filled={is_filled}"


def test_every_marker_in_the_code_has_its_code_in_the_guide():
    orphans = [(f.name, i) for f in STEP_FILES for i in blanks.empty(f.read_text(encoding="utf-8")) if i not in BLANKS]
    assert not orphans


def test_making_and_filling_blanks_round_trips():
    for blank in BLANKS.values():
        full = filled(blank["path"])
        assert blanks.fill(blanks.make(full, blank["path"], BLANKS), BLANKS) == full


def test_filled_code_compiles_and_builds_every_agent(tmp_path):
    """Paste every blank from the guide into a copy of steps/, then import all six apps."""
    for f in (ROOT / "steps").rglob("*.py"):
        target = tmp_path / f.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(blanks.fill(f.read_text(encoding="utf-8"), BLANKS), encoding="utf-8")
        compile(target.read_text(encoding="utf-8"), str(target), "exec")
    check = ("import importlib\n"
             "for app in ('step1_scout','step2_match_prep','step3_scouting_dept','step4_tribun',"
             "'step5_technical_director','bonus_live_mcp'):\n"
             "    agent = importlib.import_module(f'steps.{app}.agent').root_agent\n"
             "    print(app, type(agent).__name__, agent.name)\n")
    run = subprocess.run([sys.executable, "-c", check], cwd=tmp_path, capture_output=True, text=True,
                         env={"PYTHONPATH": str(tmp_path), "PATH": "", "GOOGLE_API_KEY": "test", "HOME": str(tmp_path)})
    assert run.returncode == 0, run.stderr[-2000:]
    assert run.stdout.count("\n") == 6


def _demo_ref():
    for ref in ("demo", "origin/demo"):
        if subprocess.run(["git", "rev-parse", "--verify", "-q", ref], cwd=ROOT, capture_output=True).returncode == 0:
            return ref
    return None


@pytest.mark.skipif(_demo_ref() is None, reason="the demo branch is not available in this clone")
@pytest.mark.parametrize("path", sorted({b["path"] for b in BLANKS.values()}))
def test_filling_the_blanks_gives_the_demo_branch_code(path):
    demo = subprocess.run(["git", "show", f"{_demo_ref()}:{path}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert filled(path) == demo


@pytest.mark.parametrize("doc", [GUIDE, ROOT / "README.md"], ids=["guide", "readme"])
def test_linked_images_exist(doc):
    links = re.findall(r"\]\(([^)\s]+\.(?:svg|png))", doc.read_text(encoding="utf-8"))
    assert links
    missing = [link for link in links if not (doc.parent / link).exists()]
    assert not missing, missing
