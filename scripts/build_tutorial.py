"""Build tutorial.md, the Cloud Shell tutorial that opens next to the editor.

    uv run python scripts/build_tutorial.py

Open in Cloud Shell (the link in the README and the guide) clones the main branch and opens this
tutorial in a side panel. Its links open files, and for each ✏️ BLANK a link selects the BLANK line,
so participants paste the code over it. The code for each blank comes from the guide, so the
tutorial, the guide and the blanks stay the same (tests/test_tutorial.py checks it).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blanks  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tutorial.md"
SITE = "https://omarcevi.dev/workshops/match-day-agents/"
DIAGRAMS = SITE + "diagrams/"


def open_file(path: str, text: str | None = None) -> str:
    return f'<walkthrough-editor-open-file filePath="{path}">{text or path}</walkthrough-editor-open-file>'


def diagram(name: str, alt: str) -> str:
    return f"![{alt}]({DIAGRAMS}{name}.svg)\n\n[Open the diagram full size]({DIAGRAMS}{name}.svg)\n"


def fill_blank(blank_id: str, where: str) -> str:
    """Copy the code, select the BLANK line, paste, save.

    Copy comes first: the copy button takes the focus away from the editor, and the select link gives it back.
    """
    b = blanks.guide_blanks()[blank_id]
    step = b["path"].split("/")[1].split("_")[0].removeprefix("step")
    select = (f'<walkthrough-editor-select-regex filePath="{b["path"]}" regex="{blanks.select_regex(blank_id)}">'
              f'BLANK {blank_id} in {b["path"]}</walkthrough-editor-select-regex>')
    return f"""### ✏️ BLANK {blank_id} · {where}

**Copy the code.** Click the copy button at the top right of the code below. The
[guide]({SITE}step-{step}/#blank-{blank_id}) explains each line.

```python
{b["code"]}
```

**Select the blank.** Click {select}. The editor opens the file and selects the BLANK line.

**Paste and save.** Press Ctrl+V (⌘V on a Mac) to replace the BLANK line. Then press Ctrl+S (⌘S) to save.
"""


def ask(app: str, *prompts: str) -> str:
    """Each prompt in its own block: the tutorial panel gives a block a copy button."""
    what = "this question" if len(prompts) == 1 else "these three questions, one at a time"
    blocks = "\n".join(f"```text\n{p}\n```\n" for p in prompts)
    return f"In the dev UI, select `{app}`. Then send {what}:\n\n{blocks}"


def late(ids: str) -> str:
    return (f"**Late?** In your second terminal tab, run this command. It pastes the code for you:\n\n"
            f"```bash\nuv run python scripts/blanks.py fill {ids}\n```\n")


PAGES = [
    f"""## Welcome

It is Saturday night. Tomorrow, Trabzonspor play Gaziantep FK at home. You are the new AI analysis
staff of the club. The coaches want a match briefing by the morning.

In this tutorial, you build the staff from agents with Google's **Agent Development Kit (ADK)**.
Each step adds one staff member, and each staff member is one agent pattern. All agents use real
data from the last ten matches of both teams.

{diagram("overview", "The whole staff")}
| Step | Pattern | Staff member |
|---|---|---|
| 1 | `LlmAgent` with tools | The Scout |
| 2 | `SequentialAgent` | Match Prep |
| 3 | `ParallelAgent` in a `SequentialAgent` | Scouting Department |
| 4 | `LoopAgent` | Tribün |
| 5 | Orchestrator with `AgentTool` | Technical Director |

In each step, the key code is missing. A one-line ✏️ BLANK marker is in its place. The tutorial
selects the BLANK line for you. You paste the code over it, save, and run the step.

You need a free Gemini API key. You do not need a Google Cloud project or billing. The guide has
the full explanations and the diagrams: [omarcevi.dev/workshops/match-day-agents]({SITE}).

<walkthrough-tutorial-duration duration="60"></walkthrough-tutorial-duration>
""",
    f"""## Set up

1. Install the Python packages (about 1 minute):
   ```bash
   uv sync
   ```
   If the terminal shows `uv: command not found`, install uv with this command. Then
   run `uv sync` again:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh && source $HOME/.local/bin/env
   ```
2. Get a free Gemini API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
3. Make your `.env` file:
   ```bash
   cp .env.example .env
   ```
4. Save your key in it. This command asks for the key and does not show it:
   ```bash
   read -s -p "Gemini API key: " KEY && sed -i "s|^GOOGLE_API_KEY=.*|GOOGLE_API_KEY=$KEY|" .env && unset KEY && echo " saved"
   ```
   You can also paste the key into {open_file(".env")} in the editor.
5. Start the ADK dev UI:
   ```bash
   uv run adk web --reload_agents --port 8080 --allow_origins "*" steps
   ```
   With `--reload_agents`, the dev UI loads a file again when you save it. With
   `--allow_origins "*"`, the Web Preview page can connect to the dev UI.
6. Click <walkthrough-web-preview-icon></walkthrough-web-preview-icon> **Web preview**. Then
   click **Preview on port 8080**. The dev UI opens in a new tab.
7. Click **+** in the terminal to open a second tab. Use it for all other commands. The dev UI
   continues to run in the first tab.

✅ **Check:** the dropdown at the top left of the dev UI shows six apps, from `bonus_live_mcp` to
`step5_technical_director`. Until you fill a step, the terminal shows `✏️ BLANK ... paste its code
over this line` when you select it.
""",
    f"""## The data and the tools

All agents use a snapshot from FotMob, ESPN and Turkish match reports (30 October 2026):

- {open_file("data/README.md")}: what each file contains, and the stories in the data.
- {open_file("data/squad.json")} and {open_file("data/opponent.json")}: the two squads, with the
  availability of each player for Sunday and the statistics of the last ten matches.
- {open_file("data/match.json")}: the fixture, the referee, the coaches and the head-to-head.

The agents never read these files. They call tools:

- {open_file("matchday/tools.py")}: the 11 tools. Python does all the calculations: **LLMs
  interpret, tools count.** `null` in the data becomes `"not available"`, never zero.
- {open_file("matchday/config.py")}: the model and the house rules. Every agent answers in the
  language of the user. Write in Turkish, and the agents answer in Turkish.
""",
    f"""## Step 1 · The Scout

One `LlmAgent` has an instruction and tools. The instruction tells the agent who it is and how to
work. The tools are Python functions that the agent can call.

{diagram("step1-scout", "Step 1: the scout")}
{fill_blank("1", "the whole agent")}
### Run it

{ask("step1_scout", "Who's in form for us, and who can't play Sunday?")}
✅ **Check:** the events panel shows calls to `get_top_players` and `get_availability`. The answer
gives 8 goals and 5 assists for Salah, and the players who are out or doubtful.

{late("1")}
More about this step: [Step 1 · The Scout]({SITE}step-1/).
""",
    f"""## Step 2 · Match Prep

A `SequentialAgent` runs its sub-agents in a fixed order. Each sub-agent saves its answer with
`output_key`. The next sub-agent reads it with a `{{placeholder}}` in its instruction. Open
{open_file("steps/step2_match_prep/agent.py")}: the opponent analyst and the lineup picker are
already there. You add the tactician and the line that connects the three agents.

{diagram("step2-match-prep", "Step 2: match prep")}
{fill_blank("2a", "the tactician")}
{fill_blank("2b", "the SequentialAgent")}
### Run it

{ask("step2_match_prep", "Prepare Sunday's game plan.")}
✅ **Check:** three agents answer in order (about two minutes). The **State** tab shows
`opponent_report`, `game_plan` and `lineup`. The XI has no player who is out or doubtful.

{late("2a 2b")}
More about this step: [Step 2 · Match Prep]({SITE}step-2/).
""",
    f"""## Step 3 · Scouting Department

A `ParallelAgent` starts three scouts at the same time. Each scout writes its own state key. Then
a report writer merges the three reports. Open
{open_file("steps/step3_scouting_dept/agent.py")}: the three scouts are already there.

{diagram("step3-scouting-dept", "Step 3: scouting department")}
{fill_blank("3", "the report writer")}
### Run it

{ask("step3_scouting_dept", "Scout Gaziantep for us.")}
✅ **Check:** the three scouts call their tools at the same time. The brief has four sections and
says that Gaziantep conceded 10 of 15 goals (67%) in the second half.

{late("3")}
More about this step: [Step 3 · Scouting Department]({SITE}step-3/).
""",
    f"""## Step 4 · Tribün

A `LoopAgent` runs a lineup picker and a critic again and again. The critic is the Tribün, the home
crowd. When it agrees with the lineup, it calls `exit_loop`. `max_iterations=3` is the safety
limit. Open {open_file("steps/step4_tribun/agent.py")}: the lineup picker is already there. Its
instruction reads `{{tribun_feedback?}}`. With the `?`, round one can start without feedback.

{diagram("step4-tribun", "Step 4: the Tribün loop")}
{fill_blank("4", "the Tribün")}
### Run it

{ask("step4_tribun", "Pick the XI for Sunday.")}
✅ **Check:** the Tribün objects in round one, with numbers from its tools. The lineup picker fixes
the XI. Then the Tribün calls `exit_loop` and cheers. The tool `exit_loop` is in
{open_file("matchday/tools.py", "matchday/tools.py")}.

{late("4")}
More about this step: [Step 4 · Tribün]({SITE}step-4/).
""",
    f"""## Step 5 · Technical Director

An orchestrator is an `LlmAgent` that has other agents as tools. Each team from steps 1 to 4 is in
an `AgentTool`. The director selects a team by its **description**. Open
{open_file("steps/step5_technical_director/agent.py")}.

{diagram("step5-technical-director", "Step 5: the technical director")}
{fill_blank("5a", "the descriptions")}
{fill_blank("5b", "the teams")}
### Run it

{ask("step5_technical_director", "Should we rest Salah for Freiburg on Thursday?",
    "If we win 2-0, where do we stand?", "Bizi pazara hazırla")}
✅ **Check:** the first answer uses the scout and `get_fixtures`. The second uses only
`project_table`: Trabzonspor go from 3rd to 1st. The third calls the scouting department and match
prep, and answers in Turkish (about 4 minutes).

Try this: in the file, remove the `#` from the two vague descriptions. Ask the same questions
again. The director selects the wrong team.

{late("5a 5b")}
More about this step: [Step 5 · Technical Director]({SITE}step-5/).
""",
    f"""## Bonus · Live data over MCP

Open {open_file("steps/bonus_live_mcp/agent.py")}. It is the scout from step 1 with one change: its
tools come from a live football server over MCP, not from the JSON files. The agent code does not
change.

{diagram("bonus-live-mcp", "Bonus: live data over MCP")}
The server is free, but it accepts only 30 requests per minute from each IP address. In the
workshop, only the speaker runs this step.
""",
    f"""## Well done

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

You built Trabzonspor's AI analysis room: one agent, a sequential team, a parallel team, a review
loop and an orchestrator.

- The cheat sheet tells you which pattern to use when: [Which recipe when]({SITE}cheat-sheet/).
- The `demo` branch has the full agent team. To see it, run `git switch demo` in the second
  terminal tab.
- Try a change: add a `compare_players` tool to the scout, or make the Tribün stricter. The
  {open_file("README.md")} has one challenge for each step.
""",
]


def build() -> str:
    head = """<walkthrough-metadata>
  <meta name="title" content="Building Trabzonspor's AI Analysis Room" />
  <meta name="description" content="DevFest Trabzon 2026 workshop: five agent patterns with Google's Agent Development Kit on real Trabzonspor data. Fill in each blank, then run the step." />
  <meta name="keywords" content="ADK, agents, Gemini, SequentialAgent, ParallelAgent, LoopAgent, AgentTool, DevFest Trabzon" />
</walkthrough-metadata>

<!-- Generated by scripts/build_tutorial.py: edit the script, not this file. -->

# Building Trabzonspor's AI Analysis Room

"""
    return head + "\n".join(PAGES)


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
