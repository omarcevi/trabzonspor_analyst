"""Step 1 · The Scout: a single LlmAgent.

An agent is an instruction (who you are, how you work) plus tools (what you can look up).
The model picks the tools; the tools read the data and do the counting.
"""

from google.adk.agents import LlmAgent

from matchday.config import HOUSE_RULES, MODEL
from matchday.tools import get_availability, get_matches, get_player, get_team_trends, get_top_players

SCOUT_TOOLS = [get_player, get_availability, get_team_trends, get_top_players, get_matches]


def build_scout(
    name: str = "scout",
    description: str = "Looks up players and team form: stats, availability, top performers, recent results.",
    tools: list | None = None,
) -> LlmAgent:
    return LlmAgent(
        name=name,
        model=MODEL,
        description=description,
        instruction="""
You are the scout on Trabzonspor's analysis staff. "We" and "us" always mean Trabzonspor.
Answer questions about players and teams.

How you work:
1. Look everything up with your tools before you answer. Never answer from memory.
2. "In form" means recent output and ratings: check top players by goals, assists and avg_rating.
3. "Who can't play" means the availability list: out and doubtful players with the reason.
4. Name the player, then the numbers that back up your point.
""" + HOUSE_RULES,
        tools=tools or SCOUT_TOOLS,
    )


root_agent = build_scout()
