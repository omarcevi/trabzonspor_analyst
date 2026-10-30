"""The Cloud Shell tutorial (tutorial.md) must match its generator, the guide and the blanks."""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import blanks  # noqa: E402
import build_tutorial  # noqa: E402
import smoke  # noqa: E402

TUTORIAL = (ROOT / "tutorial.md").read_text(encoding="utf-8")
BLANKS = blanks.guide_blanks()
SELECTS = re.findall(r'<walkthrough-editor-select-regex filePath="([^"]+)" regex="([^"]+)">BLANK (\w+) ', TUTORIAL)


def test_tutorial_is_up_to_date():
    assert TUTORIAL == build_tutorial.build(), "run: uv run python scripts/build_tutorial.py"


def test_every_file_link_opens_a_file_in_the_repo():
    paths = re.findall(r'<walkthrough-editor-open-file filePath="([^"]+)">', TUTORIAL)
    assert paths
    missing = [p for p in paths if p != ".env" and not (ROOT / p).exists()]   # cp .env.example .env makes .env
    assert not missing


def test_every_blank_has_a_select_link_and_its_code():
    assert sorted(b for _, _, b in SELECTS) == sorted(BLANKS)
    for blank_id, blank in BLANKS.items():
        assert f"```python\n{blank['code']}\n```" in TUTORIAL, f"BLANK {blank_id}: code differs from the guide"


@pytest.mark.parametrize("path, regex, blank_id", SELECTS, ids=[s[2] for s in SELECTS])
def test_select_link_selects_exactly_the_blank_line(path, regex, blank_id):
    """Run the link's regex on the file as it is on the main branch, with the blanks before it filled."""
    text = blanks.fill((ROOT / path).read_text(encoding="utf-8"), BLANKS)
    order = list(BLANKS)
    earlier = {i for i in order[: order.index(blank_id)]}
    main_text = blanks.make(text, path, BLANKS, ids={i for i in BLANKS if i not in earlier})
    matches = list(re.finditer(regex, main_text))
    assert len(matches) == 1, f"{len(matches)} matches"
    m = matches[0]
    line_start = main_text.rfind("\n", 0, m.start()) + 1
    line_end = main_text.find("\n", m.end())
    assert (m.start(), m.end()) == (line_start, line_end), "the selection must cover the whole line"
    assert blanks.empty(main_text[line_start:line_end + 1]) == [blank_id]


def test_prompts_are_the_smoke_test_prompts():
    """Participants send the same questions that scripts/smoke.py checks."""
    prompts = re.findall(r"```text\n(.*?)\n```", TUTORIAL)
    assert prompts == [p for app, demos in smoke.DEMOS.items() if app != "bonus_live_mcp" for p in demos]


def test_open_in_cloud_shell_links_open_this_tutorial():
    for doc in ("README.md", "guide/match-day-agents.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        link = re.search(r"https://shell\.cloud\.google\.com/cloudshell/editor\?[^)\s]+", text)
        assert link, doc
        assert "cloudshell_git_repo=https://github.com/omarcevi/trabzonspor_analyst.git" in link.group()
        assert "cloudshell_git_branch=main" in link.group() and "cloudshell_tutorial=tutorial.md" in link.group()
