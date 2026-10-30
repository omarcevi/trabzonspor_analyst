"""Save your Gemini API key in .env. The key does not show on the screen when you paste it.

    uv run python scripts/set_key.py

Makes .env from .env.example if there is no .env yet. The same command works in Cloud Shell,
on macOS, Linux and Windows. Get a free key at https://aistudio.google.com/apikey
"""

from __future__ import annotations

import getpass
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def save(key: str, env: Path = ROOT / ".env", example: Path = ROOT / ".env.example") -> None:
    """Put GOOGLE_API_KEY=<key> in env, in place of the old key line."""
    if not env.exists():
        shutil.copy(example, env)
    line = f"GOOGLE_API_KEY={key}"
    text, found = re.subn(r"^GOOGLE_API_KEY=.*$", lambda _: line, env.read_text(encoding="utf-8"), flags=re.M)
    env.write_text(text if found else f"{line}\n{text}", encoding="utf-8")


def main() -> int:
    key = getpass.getpass("Paste your Gemini API key, then press Enter (the key does not show): ").strip()
    if not key or " " in key:
        print("That is not a key. Get one at https://aistudio.google.com/apikey and run this command again.")
        return 1
    save(key)
    print("✅ Key saved in .env")
    return 0


if __name__ == "__main__":
    sys.exit(main())
