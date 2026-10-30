"""Run every step once with its demo prompt and show what each agent said and which tools it called.

    uv run python scripts/smoke.py                      # every step
    uv run python scripts/smoke.py step1_scout step4_tribun

Needs GOOGLE_API_KEY (in .env or the environment). Each transcript is also saved to
scripts/smoke_output/<step>.md. After each answer the script lists any number in the agents'
text that appears in no tool result: a quick way to spot invented numbers (review them by hand;
formations and list counts show up there too).
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import re
import sys
import time
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

from matchday.config import MODEL_NAME

DEMOS = {
    "step1_scout": ["Who's in form for us, and who can't play Sunday?"],
    "step2_match_prep": ["Prepare Sunday's game plan."],
    "step3_scouting_dept": ["Scout Gaziantep for us."],
    "step4_tribun": ["Pick the XI for Sunday."],
    "step5_technical_director": [
        "Should we rest Salah for Freiburg on Thursday?",
        "If we win 2-0, where do we stand?",
        "Bizi pazara hazırla",
    ],
    "bonus_live_mcp": ["What were Trabzonspor's last three results, and who scored?"],
}
OUT = Path(__file__).resolve().parent / "smoke_output"
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def numbers(text: str) -> set[str]:
    """Numbers in a text, normalised so '8,03' (Turkish) equals 8.03 and '3.0' equals 3."""
    found = set()
    for raw in NUMBER.findall(text):
        value = float(raw.replace(",", "."))
        found.add(str(int(value)) if value.is_integer() else f"{value:g}")
    return found


async def run_prompt(runner: InMemoryRunner, app: str, prompt: str, log: list[str]) -> None:
    session = await runner.session_service.create_session(app_name=app, user_id="staff")
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    seen, said = numbers(prompt), []
    log.append(f"\n### Prompt: {prompt}\n")
    started = time.monotonic()
    async for event in runner.run_async(user_id="staff", session_id=session.id, new_message=message):
        for part in (event.content.parts if event.content else []) or []:
            if part.function_call:
                args = json.dumps(part.function_call.args or {}, ensure_ascii=False)
                log.append(f"- `{event.author}` → **{part.function_call.name}**({args})")
            elif part.function_response:
                payload = json.dumps(part.function_response.response, ensure_ascii=False)
                seen |= numbers(payload)
                log.append(f"- `{part.function_response.name}` ← {payload[:160]}{'…' if len(payload) > 160 else ''}")
            elif part.text and not part.thought:
                said.append(part.text)
                log.append(f"\n**[{event.author}]**\n\n{part.text.strip()}\n")
    unverified = sorted(numbers("\n".join(said)) - seen, key=lambda n: float(n))
    log.append(f"\n_{time.monotonic() - started:.0f}s · numbers not found in any tool result: "
               f"{', '.join(unverified) or 'none'}_\n")


async def run_step(app: str) -> str:
    agent = importlib.import_module(f"steps.{app}.agent").root_agent
    runner = InMemoryRunner(agent=agent, app_name=app)
    log = [f"## {app} · model {MODEL_NAME}"]
    try:
        for prompt in DEMOS[app]:
            await run_prompt(runner, app, prompt, log)
    except Exception as exc:  # keep going: one failing step should not hide the others
        log.append(f"\n**FAILED:** {type(exc).__name__}: {exc}\n")
    finally:
        await runner.close()
    return "\n".join(log)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("steps", nargs="*", help=f"steps to run (default: all): {', '.join(DEMOS)}")
    apps = parser.parse_args().steps or list(DEMOS)
    if unknown := [a for a in apps if a not in DEMOS]:
        parser.error(f"unknown step(s): {', '.join(unknown)}")
    if not os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() not in ("true", "1"):
        print("GOOGLE_API_KEY is not set. Copy .env.example to .env and paste your key.", file=sys.stderr)
        return 1
    OUT.mkdir(exist_ok=True)
    failed = False
    for app in apps:
        transcript = await run_step(app)
        (OUT / f"{app}.md").write_text(transcript + "\n", encoding="utf-8")
        print(transcript, flush=True)
        failed |= "**FAILED:**" in transcript
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
