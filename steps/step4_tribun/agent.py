"""Step 4 · Tribün: a LoopAgent.

The lineup picker proposes an XI, the Tribün (the home crowd) criticises it, and the loop
repeats until the Tribün calls exit_loop. max_iterations=3 is the safety net if it never does.
"""

from google.adk.agents import LlmAgent, LoopAgent

from matchday.config import HOUSE_RULES, MODEL
from matchday.tools import exit_loop, get_availability, get_discipline, get_player, get_team_trends, get_top_players


def build_tribun(
    name: str = "tribun_review",
    description: str = "Picks Trabzonspor's XI and has the home crowd challenge it until it is approved.",
) -> LoopAgent:
    lineup_picker = LlmAgent(
        name="lineup_picker",
        model=MODEL,
        instruction="""
You pick Trabzonspor's starting XI for Sunday.
Check availability first. Never pick a player who is out. A doubtful player may start only
if you name an available backup for him.

The Tribün's last verdict (empty on the first round): {tribun_feedback?}
If it lists objections, fix every one and say in one line what you changed.

Reply with the formation, the eleven players by position line, and three substitutes.
""" + HOUSE_RULES,
        tools=[get_availability, get_player, get_top_players],
        output_key="lineup",
    )
    # ✏️ BLANK 4 · in the guide under "Step 4 · Tribün": paste its code over these two lines
    raise NotImplementedError("BLANK 4 is still empty. Paste its code from the guide (Step 4 · Tribün).")


root_agent = build_tribun()
