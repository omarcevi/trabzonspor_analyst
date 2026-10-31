"""Step 3 · Scouting Department: a ParallelAgent inside a SequentialAgent.

Three scouts work at the same time on independent questions, each writing to its own
output_key. Then a report writer merges the three reports into one brief.
"""

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent

from matchday.config import HOUSE_RULES, MODEL
from matchday.tools import (
    get_availability, get_discipline, get_match_info, get_matches, get_player, get_team_trends, get_top_players,
)

FIND_OPPONENT = "We are Trabzonspor. Find Sunday's opponent with get_match_info (the team that is not us).\n"


def build_scouting_department(
    name: str = "scouting_department",
    description: str = "Scouts Sunday's opponent: threats, weaknesses, discipline and referee risks.",
) -> SequentialAgent:
    
    attack_scout = LlmAgent(
        name="attack_scout",
        model=MODEL,
        instruction=FIND_OPPONENT + """Report their attacking threats: top scorers, top creators (assists),
which of them are available, and in which 15-minute windows they score most.""" + HOUSE_RULES,
        tools=[get_match_info, get_top_players, get_team_trends, get_matches],
        output_key="attack_report",
    )
    
    defense_scout = LlmAgent(
        name="defense_scout",
        model=MODEL,
        instruction=FIND_OPPONENT + """Report their defensive weaknesses: goals conceded per 15-minute window,
home vs away record, and which defenders or goalkeepers are suspended, injured or doubtful.""" + HOUSE_RULES,
        tools=[get_match_info, get_team_trends, get_availability, get_player],
        output_key="defense_report",
    )
    
    discipline_scout = LlmAgent(
        name="discipline_scout",
        model=MODEL,
        instruction=FIND_OPPONENT + """Report discipline for BOTH teams: the referee's averages, card-prone
players on each side, and every red card in the last 10 matches.""" + HOUSE_RULES,
        tools=[get_match_info, get_discipline],
        output_key="discipline_report",
    )
    
    report_writer = LlmAgent(
        name="report_writer",
        model=MODEL,
        instruction="""Merge three scouting reports into one brief for Trabzonspor's coaches.
Attack report: {attack_report}
Defense report: {defense_report}
Discipline report: {discipline_report}
Write four short sections: Threats, Weaknesses to attack, Discipline and referee, Three key takeaways.
Use only facts from the reports; if they disagree, say so.""" + HOUSE_RULES,
        output_key="scouting_brief",
    )
    scouts = ParallelAgent(name="scouts", sub_agents=[attack_scout, defense_scout, discipline_scout])
    return SequentialAgent(name=name, description=description, sub_agents=[scouts, report_writer])


root_agent = build_scouting_department()
