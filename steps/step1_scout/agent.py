"""Step 1 · The Scout: a single LlmAgent.

An agent is an instruction (who you are, how you work) plus tools (what you can look up).
The model picks the tools; the tools read the data and do the counting.
"""

from google.adk.agents import LlmAgent

from matchday.config import HOUSE_RULES, MODEL
from matchday.tools import get_availability, get_matches, get_player, get_team_trends, get_top_players

SCOUT_TOOLS = [get_player, get_availability, get_team_trends, get_top_players, get_matches]


raise NotImplementedError("✏️ BLANK 1 · Step 1 · The Scout in the guide: paste its code over this line")
