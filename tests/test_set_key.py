"""scripts/set_key.py writes the key into .env and keeps every other line."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import set_key  # noqa: E402


def test_makes_env_from_the_example(tmp_path):
    env = tmp_path / ".env"
    set_key.save("AIza-test-key", env, ROOT / ".env.example")
    text = env.read_text(encoding="utf-8")
    assert "GOOGLE_API_KEY=AIza-test-key\n" in text
    assert "paste-your-key-here" not in text
    assert "MODEL=" in text


def test_replaces_the_old_key_only(tmp_path):
    env = tmp_path / ".env"
    env.write_text("GOOGLE_API_KEY=old\nMODEL=gemini-3.8-flash\n", encoding="utf-8")
    set_key.save(r"new\1key", env)
    assert env.read_text(encoding="utf-8") == "GOOGLE_API_KEY=new\\1key\nMODEL=gemini-3.8-flash\n"


def test_adds_a_key_line_when_there_is_none(tmp_path):
    env = tmp_path / ".env"
    env.write_text("MODEL=gemini-3.8-flash\n", encoding="utf-8")
    set_key.save("k", env)
    assert env.read_text(encoding="utf-8") == "GOOGLE_API_KEY=k\nMODEL=gemini-3.8-flash\n"
