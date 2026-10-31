"""Step 2 · Match Prep: a SequentialAgent.

Three agents run in a fixed order. Each saves its answer in session state with output_key,
and the next one reads it through a {placeholder} in its instruction.
"""

from google.adk.agents import LlmAgent, SequentialAgent

from matchday.config import HOUSE_RULES, MODEL
from matchday.tools import (
    get_availability, get_match_info, get_matches, get_player, get_team_trends, get_top_players,
)


def build_match_prep(
    name: str = "match_prep",
    description: str = "Prepares Sunday's game plan: opponent analysis, tactics and a starting XI.",
) -> SequentialAgent:
    opponent_analyst = LlmAgent(
        name="opponent_analyst",
        model=MODEL,
        instruction="""
You analyse Sunday's opponent for Trabzonspor. Find out who they are with get_match_info,
then use your tools for their form, home/away record, when they score and concede,
their key players and who is missing. Write a short opponent report.
""" + HOUSE_RULES,
        tools=[get_match_info, get_team_trends, get_top_players, get_availability, get_matches],
        output_key="opponent_report",
    )

    raise NotImplementedError("✏️ BLANK 2a · Step 2 · Match Prep in the guide: paste its code over this line")
    
    lineup_picker = LlmAgent(
        name="lineup_picker",
        model=MODEL,
        instruction="""
You pick Trabzonspor's starting XI. The game plan:
{game_plan}

1. Call get_availability("Trabzonspor") first. Never pick a player who is out or doubtful.
2. Use get_top_players("Trabzonspor", "minutes", 15) to see who usually plays, and get_player to check a position.
3. Reply with the formation, the eleven players by position line, and three substitutes.
""" + HOUSE_RULES,
        tools=[get_availability, get_player, get_top_players],
        output_key="lineup",
    )
    
    raise NotImplementedError("✏️ BLANK 2b · Step 2 · Match Prep in the guide: paste its code over this line")


root_agent = build_match_prep()
