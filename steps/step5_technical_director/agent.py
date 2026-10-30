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

# ✏️ BLANK 5a · in the guide under "Step 5 · Technical Director": paste its code over these two lines
raise NotImplementedError("BLANK 5a is still empty. Paste its code from the guide (Step 5 · Technical Director).")


def build_technical_director(name: str = "technical_director") -> LlmAgent:
    # ✏️ BLANK 5b · in the guide under "Step 5 · Technical Director": paste its code over these two lines
    raise NotImplementedError("BLANK 5b is still empty. Paste its code from the guide (Step 5 · Technical Director).")
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
