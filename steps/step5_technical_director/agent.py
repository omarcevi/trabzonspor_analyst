"""Step 5 · Technical Director: an orchestrator that delegates.

Each earlier team is wrapped in an AgentTool, so the director calls it like a function, gets
the answer back and stays in charge. The model chooses a team by reading its description.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool

from matchday.config import HOUSE_RULES, MODEL
from matchday.tools import get_fixtures, get_standings, project_table
from steps.step1_scout.agent import build_scout
from steps.step2_match_prep.agent import build_match_prep
from steps.step3_scouting_dept.agent import build_scouting_department
from steps.step4_tribun.agent import build_tribun

# Delegation is driven by these descriptions: they are all the director knows about each team.
SCOUT = "Answers questions about ONE player or ONE team: form, minutes, goals, ratings, availability."
MATCH_PREP = "Writes Sunday's game plan: opponent analysis, then tactics, then an XI of available players."
SCOUTING_DEPT = "Full scouting report on Sunday's opponent: threats, weaknesses, cards and the referee."
TRIBUN = "Picks a final XI and has the home crowd stress-test it. Only when asked to pick or defend the XI."
# Try it live: uncomment these, ask the same questions again, and watch the routing go wrong.
# SCOUT = "Helps with football."
# SCOUTING_DEPT = "Also helps with football."


def build_technical_director(name: str = "technical_director") -> LlmAgent:
    
    # Each team becomes a tool: the director calls it like a function and gets its answer back.
    teams = [
        AgentTool(build_scout(description=SCOUT)),
        AgentTool(build_match_prep(description=MATCH_PREP)),
        AgentTool(build_scouting_department(description=SCOUTING_DEPT)),
        AgentTool(build_tribun(description=TRIBUN)),
    ]
    
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Runs the analysis staff and writes the match briefing.",
        instruction="""
You are Trabzonspor's technical director. Sunday's match briefing is due by morning.
You have four teams (tools that run other agents) and three data tools. Use the fewest
calls that answer the question, then write the answer yourself.

- One player, rotation or rest: ask the scout, and check get_fixtures for the schedule.
- Points, positions, "where do we stand": get_standings or project_table. Never do the maths yourself.
- A full briefing ("prepare us for Sunday"): call scouting_department, then match_prep, then
  write one briefing with four sections: Opponent, Game plan, XI, Risks.
When you call a team, write the request in English and include every detail it needs.
""" + HOUSE_RULES,
        tools=[*teams, get_fixtures, get_standings, project_table],
    )


root_agent = build_technical_director()
