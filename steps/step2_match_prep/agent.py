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

    tactician = LlmAgent(
        name="tactician",
        model=MODEL,
        instruction="""
You are Trabzonspor's tactician. Opponent report from the analyst:
{opponent_report}

Check our own form with get_team_trends("Trabzonspor"), then write a game plan:
formation, how we attack, how we defend, and what to do in each phase of the match.
""" + HOUSE_RULES,
        tools=[get_team_trends, get_match_info],
        output_key="game_plan",
    )
    
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
    
    return SequentialAgent(name=name, description=description, sub_agents=[opponent_analyst, tactician, lineup_picker])


root_agent = build_match_prep()
