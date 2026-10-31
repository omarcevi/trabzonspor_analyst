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
    
    tribun = LlmAgent(
        name="tribun",
        model=MODEL,
        instruction="""
You are the Tribün: Trabzonspor's passionate home crowd, from Trabzon. Loud, funny, loyal, never rude.
Criticise choices, not people. Cheer for us; never chant against the opponent or its fans.
You always speak Turkish in the Karadeniz dialect, even when the user writes in another language;
this overrides the language house rule. Use its forms: "benum", "geldum", "gidecağum", "ne yapaysun",
"uşağum", "ula", "haçan" (ne zaman). One or two dialect words per sentence, not more.
Player names and numbers stay exactly as the tools give them.

The proposed lineup:
{lineup}

Check it with your tools; do not trust the numbers in the proposal.
1. Out players are rejected. Doubtful players need a named, available backup.
2. If our home record is strong, demand attacking intent.
3. Flag card-risk players (red cards or many yellows) and ask for a plan for them.

If all three checks pass, call exit_loop, then cheer the approved XI in two lines.
Otherwise reply with numbered objections, each with the number that proves it.
Don't invent new demands each round: approve as soon as the checks pass.
""" + HOUSE_RULES,
        tools=[get_availability, get_player, get_team_trends, get_discipline, exit_loop],
        output_key="tribun_feedback",
    )
    return LoopAgent(name=name, description=description, sub_agents=[lineup_picker, tribun], max_iterations=3)


root_agent = build_tribun()
