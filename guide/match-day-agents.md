---
title: "Building Trabzonspor's AI Analysis Room"
description: "Agent recipes with Google's Agent Development Kit. You build a football analysis staff from one agent, a sequential team, a parallel team, a review loop and an orchestrator. All of them use real Trabzonspor data."
date: 2026-10-31
tags: [adk, agents, gemini, python, multi-agent, devfest]
repo: "https://github.com/omarcevi/trabzonspor_analyst"
---

# Building Trabzonspor's AI Analysis Room

It is Saturday night. Tomorrow, Sunday 1 November 2026, Trabzonspor play Gaziantep FK at home. Kick-off is at 16:00, Istanbul time, in Round 10 of the Süper Lig. You are the new analysis staff of the club. The coaches want a briefing by the morning. It must tell them who the opponent is, how we play them, who starts, and what can go wrong.

You will build this staff from agents. Each step adds one staff member. Each staff member is an agent pattern that you can use again after this match:

1. **The Scout:** one agent with tools.
2. **Match Prep:** agents that run in a fixed order.
3. **Scouting Department:** agents that run at the same time.
4. **Tribün:** two agents in a loop: one proposes, one criticises.
5. **Technical Director:** an agent that delegates to all the others.

Everything runs on Google's [Agent Development Kit](https://adk.dev) (ADK) for Python and a free Gemini API key. The data comes from the last ten matches of both teams. I gave this workshop at DevFest Trabzon 2026. This guide is for the people who were not in the room.

[![The whole staff: the Technical Director calls four teams as tools; every team calls plain Python tools that read the data](images/overview.svg)](images/overview.svg "Open full size")

*The full staff at the end of the guide. Each box with the ADK logo is an agent. Tap to open full size.*

## Setup

You need Python 3.11 or newer, [uv](https://docs.astral.sh/uv/), and a Gemini API key. You can get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). You do not need a credit card.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # installs uv
git clone https://github.com/omarcevi/trabzonspor_analyst
cd trabzonspor_analyst
cp .env.example .env                                 # paste your key into .env
uv sync
uv run adk web --reload_agents steps
```

Open http://localhost:8000. Select a step in the dropdown and ask it a question. The events panel shows each tool call and each hand-off. With `--reload_agents`, ADK loads a file again when you save it.

<!-- SCREENSHOT: adk web with the app dropdown open, showing the six step folders -->

The `.env` file holds three values: your key, `GOOGLE_GENAI_USE_VERTEXAI=FALSE` and `MODEL=gemini-3.8-flash`. The second value selects the free Gemini API, not Vertex AI. The model name is in one place only, `matchday/config.py`:

<!-- source: matchday/config.py -->
```python
MODEL_NAME = os.getenv("MODEL", "gemini-3.8-flash")

# Free-tier keys hit rate limits when many agents run at once: retry 429s with backoff.
MODEL = Gemini(
    model=MODEL_NAME,
    retry_options=types.HttpRetryOptions(attempts=5, initial_delay=2, max_delay=30),
)
```

The retries are important. One question to step 5 can cause a few dozen model calls. On a free key, this sometimes causes a `429` error. If the setup does not work on your laptop, use `notebook/match_day_agents.ipynb` in Colab. It runs the same files, with one cell for each step.

**How to fill a blank.** On the `main` branch, the key code of each step is missing. A two-line ✏️ BLANK marker is in its place. When the guide shows a code block with a ✏️ BLANK label, do these steps:

1. Copy the code block with its copy button.
2. In the file, select the two marker lines.
3. Paste the code over them.
4. Save the file.
5. Run the step.

If you are late, run `uv run python scripts/blanks.py fill 2a`. This command pastes the code for BLANK 2a. The `demo` branch has the full agent team. To see it, run `git switch demo`.

## The data

The `data/` folder is a snapshot that I made on 30 October 2026. The sources are FotMob, ESPN and Turkish match reports. `match.json` has the fixture and the referee. `squad.json` and `opponent.json` have the two squads, with the availability of each player for Sunday and the statistics of the last ten matches. `results.json` has each match with goals, cards and xG. Two more files have the league table and the next fixtures.

The data tells real stories. Trabzonspor won all four home matches in the sample, with a total score of 13–0. Gaziantep concede late: a third of their goals against came after minute 75. The Gaziantep player with the most minutes is suspended. Salah has 8 goals and 5 assists in ten matches. Franculino, the second-best scorer, is doubtful. On Thursday, four days after this match, Trabzonspor play Freiburg in Europe.

Two rules apply to each tool. **First, `null` means "not shown on the source". It does not mean zero.** For example, the data has no xG for the Gaziantep cup match. A model can read `None` as zero. So each tool returns `"not available"`, and a test makes sure that no `None` gets out. **Second, tools return small, calculated answers, not raw files.** If you paste `results.json` (126 KB) into a prompt, the model gets most of it correct. "Most" is the problem. The header of `matchday/tools.py` gives the rule: LLMs interpret, tools count.

## Step 1 · The Scout

**The pattern:** one `LlmAgent` has an instruction and tools. The instruction tells the agent who it is and how to work. The tools are Python functions that the agent can call.

[![Step 1: the scout LlmAgent sends its instruction and tool schemas to Gemini, calls Python tools that read data, and answers with their numbers](images/step1-scout.svg)](images/step1-scout.svg "Open full size")

*One agent with five tools. Gemini selects the tool to call. Python does the work. Tap to open full size.*

This is the full agent. ✏️ **BLANK 1** · paste it into `steps/step1_scout/agent.py`:

<!-- source: steps/step1_scout/agent.py blank: 1 -->
```python
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
```

`HOUSE_RULES` comes from `config.py`. Each agent gets these rules: answer in the language of the user, and use only numbers from a tool. If you write in Turkish, the agent answers in Turkish. A function, `build_scout()`, makes the agent. Step 5 shows why this is useful.

ADK makes the tool schema from the type hints and the docstring of each tool. The model sees only this schema, so write the docstring for the model. Inside the tools, Python does all the calculations. For example, this code calculates the share of goals in each 15-minute window:

<!-- source: matchday/tools.py -->
```python
    t["goals_by_15min"] = {
        window: {
            **g,
            "pct_of_goals_scored": round(100 * g["scored"] / total_for) if total_for else NA,
            "pct_of_goals_conceded": round(100 * g["conceded"] / total_against) if total_against else NA,
        }
        for window, g in t["goals_by_15min"].items()
    }
```

The tools find names without Turkish or Polish letters: `simsir` finds Aral Şimşir. For bad input, a tool returns an error with suggestions. It does not raise an exception.

**Run it:** Save the file. In the dev UI, select `step1_scout`. Ask *"Who's in form for us, and who can't play Sunday?"*

In my run, the scout called `get_availability` one time and `get_top_players` three times (goals, assists, avg_rating). It answered in 12 seconds. A part of the answer:

> **In Form (Last 10 Matches)**
> - **Mohamed Salah** (Available): 8 goals, 5 assists, and an 8.03 average rating in 10 matches (802 minutes).
> - **Ernest Muçi** (Available): 2 goals, 5 assists, and a 7.14 average rating in 9 matches (549 minutes).
> - *(Note: **Franculino** has also been in top form with 7 goals, 2 assists, and a 7.75 average rating in 8 matches / 545 minutes, but he is currently doubtful).* …

<!-- SCREENSHOT: adk web, step1_scout, the events panel showing the get_top_players and get_availability calls -->

**Use it when** one job needs a small number of tools and some judgement. Examples: a support bot, a data assistant, a code helper.

**Do not use it when** the instruction becomes a long list of "first do this, then do that". That is a workflow. Step 2 shows workflows.

**The gotcha: tools do the calculations.** Each number from an agent must come from a tool. Give the model calculated answers (`pct_of_goals_conceded: 33`), not raw rows. My smoke script finds each number in an answer that is not in a tool result. Step 5 shows what happens when you ignore this rule.

## Step 2 · Match Prep

**The pattern:** a `SequentialAgent` runs its sub-agents in a fixed order, each time. It has no model. Each sub-agent gives its work to the next one through session state.

[![Step 2: opponent_analyst, tactician and lineup_picker run in order inside a SequentialAgent, passing opponent_report and game_plan through session state](images/step2-match-prep.svg)](images/step2-match-prep.svg "Open full size")

*Three agents in a row. Each agent saves its answer with output_key. The next agent reads it with a placeholder. Tap to open full size.*

The opponent analyst studies Gaziantep and writes a report. The tactician makes a game plan from the report. The lineup picker makes an XI from the plan. You write the tactician and the line that connects the three agents. ✏️ **BLANK 2a** · `steps/step2_match_prep/agent.py`:

<!-- source: steps/step2_match_prep/agent.py blank: 2a -->
```python
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
```

✏️ **BLANK 2b** · the same file, at the end of `build_match_prep`:

<!-- source: steps/step2_match_prep/agent.py blank: 2b -->
```python
    return SequentialAgent(name=name, description=description, sub_agents=[opponent_analyst, tactician, lineup_picker])
```

`output_key="opponent_report"` saves the final answer of the analyst in session state. Before the tactician calls the model, ADK puts this value into `{opponent_report}` in its instruction. You do not write code to connect the agents.

**Run it:** In the dev UI, select `step2_match_prep`. Ask *"Prepare Sunday's game plan."*

The three agents run in a row. This takes about two minutes. The tactician uses the report of the analyst:

> **Exploit High Conceding Windows:** Gaziantep FK have conceded 67% of their goals in the second half (10 of 15 goals in their last 10 matches). Increase tempo immediately after half-time.

The lineup picker checks the availability and then selects the XI:

> **Formation: 4-1-4-1** · André Onana; Wagner Pina, Stefan Savić, Chibuike Nwaiwu, Mustafa Eskihellaç; Fabinho; Mohamed Salah, Melih Kabasakal, Ernest Muçi, Noah Saviolo; Aral Şimşir.

In an earlier run, the lineup picker tried two player names from its memory. These players are not in this squad. `get_player` answered `{"error": "No player called 'Destan' in either squad.", ...}`. Then the agent used real players. This is why the tools return errors and do not raise exceptions.

<!-- SCREENSHOT: adk web, step2_match_prep, the State tab showing opponent_report, game_plan and lineup -->

**Use it when** the steps are always the same and each step needs the output of the step before it. Example: research, plan, act.

**Do not use it when** the steps are independent. For independent steps, step 3 is faster. Also do not use it when the next step depends on a result.

**The gotcha: `output_key` and placeholders must agree.** If a `{placeholder}` has no value in state, ADK raises a `KeyError` before the model call. Use the same names. Make sure that the agent that writes a value runs before the agent that reads it.

## Step 3 · Scouting Department

**The pattern:** a `ParallelAgent` starts its sub-agents at the same time. Each sub-agent writes its own state key. A `SequentialAgent` contains the `ParallelAgent`, so a report writer can merge the results after the parallel work.

[![Step 3: inside a SequentialAgent, a ParallelAgent runs attack_scout, defense_scout and discipline_scout at once, then report_writer merges attack_report, defense_report and discipline_report](images/step3-scouting-dept.svg)](images/step3-scouting-dept.svg "Open full size")

*Three scouts at the same time, then one writer. Tap to open full size.*

One scout studies the attack of Gaziantep. One scout studies their defence. One scout studies cards and the referee. No scout needs the work of the other scouts, so they do not wait. The scouts are already in the file. You add the writer and connect the agents. ✏️ **BLANK 3** · `steps/step3_scouting_dept/agent.py`:

<!-- source: steps/step3_scouting_dept/agent.py blank: 3 -->
```python
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
```

The instructions of the scouts do not name the opponent. Each scout calls `get_match_info` first to find it. No instruction in this repo contains a fact from the data. For a new fixture, you only change the JSON files.

**Run it:** In the dev UI, select `step3_scouting_dept`. Ask *"Scout Gaziantep for us."*

The three scouts made ten tool calls at the same time. Then the writer merged their reports. The full run took 43 seconds. A part of the brief:

> **Weaknesses to Attack**
> - **Second-half defensive collapse** (last 10 matches – 15 goals conceded, 1.5 avg, 1.63 avg xGA across 9 matches with xG data):
>   - **10 of 15 goals conceded (67%)** came in the second half.
>   - Vulnerability peaks heavily in **46–60 min** (4 conceded, 27%) and **76–90 min** (5 conceded, 33%).
>
> **Three Key Takeaways**
> 1. **Exploit the decimated backline:** Gaziantep's defensive anchor Myenty Abena is suspended, while starting goalkeeper Kacper Tobiasz and three central defenders (Meleke, Kızıldağ, Sangaré) are doubtful with muscle injuries. …

**Use it when** you have independent questions about the same thing. Examples: three searches, three reviewers, three data sources.

**Do not use it when** one task needs the answer of another task. Also do not use it when the parallel agents write to the same state key.

**The gotcha: an agent must merge the results.** A `ParallelAgent` gives you three answers, not one. The answers come in the order in which the agents finish. Give each parallel agent its own `output_key`. Then add a step that reads all the keys. Parallel agents also send more requests each second. On a free key, this can cause rate limit errors.

## Step 4 · Tribün

**The pattern:** a `LoopAgent` runs its sub-agents again and again. It stops when a sub-agent tells it to stop, or at `max_iterations`. Here, one agent proposes and one agent criticises.

[![Step 4: in a LoopAgent, lineup_picker writes lineup, tribun reads it and either writes tribun_feedback, which loops back, or calls exit_loop, which ends the loop](images/step4-tribun.svg)](images/step4-tribun.svg "Open full size")

*Propose, criticise, repeat. exit_loop stops the loop. max_iterations=3 is the safety limit. Tap to open full size.*

In Turkish football, the *tribün* is the stand and the people in it. These people have strong opinions about the team sheet. The critic in this step is the home crowd. ✏️ **BLANK 4** · `steps/step4_tribun/agent.py`:

<!-- source: steps/step4_tribun/agent.py blank: 4 -->
```python
    tribun = LlmAgent(
        name="tribun",
        model=MODEL,
        instruction="""
You are the Tribün: Trabzonspor's passionate home crowd. Loud, funny, loyal, never rude.
Criticise choices, not people. Cheer for us; never chant against the opponent or its fans.

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
```

The crowd does not trust the numbers of the lineup picker. It checks them with its own tools. When the crowd agrees with the lineup, it calls `exit_loop`:

<!-- source: matchday/tools.py -->
```python
def exit_loop(tool_context: ToolContext) -> dict:
    """Approve the lineup and end the review. Call this only when every objection is resolved."""
    tool_context.actions.escalate = True  # tells the LoopAgent to stop after this agent
    return {"status": "approved"}
```

In the next round, the lineup picker reads the objections. In round one, there are no objections. That is why the placeholder has a `?`:

<!-- source: steps/step4_tribun/agent.py -->
```python
The Tribün's last verdict (empty on the first round): {tribun_feedback?}
If it lists objections, fix every one and say in one line what you changed.
```

**Run it:** In the dev UI, select `step4_tribun`. Ask *"Pick the XI for Sunday."*

In round one, the lineup picker proposed a 4-2-3-1 with Melih Kabasakal in midfield. The crowd checked the lineup with `get_team_trends` and `get_discipline`. A part of its answer:

> 1. **Unleash the Storm at Home (Attacking Intent Needed):** … our home record is absolute perfection: **4 matches, 4 wins, 0 draws, 0 losses**, with **13 goals scored and 0 conceded** …
> 2. **Discipline Plan Required for High Card-Risk Starters:** **Melih Kabasakal:** Picked up **1 red card** (straight red) and **1 yellow card** in his last 8 matches …

In round two, the lineup picker changed the XI:

> **What I changed:** Replaced Melih Kabasakal with the card-free Ozan Tufan in midfield to cut disciplinary risk, and deployed an aggressive high-pressing 4-2-3-1 setup to attack from the opening whistle.

Then the crowd called `exit_loop` and gave its approval:

> Bordo-Mavi storm is brewing, Papara Park is ready to roar from minute one!
> With this relentless eleven on the pitch, victory is ours—haydi Trabzonspor, bas geç!

<!-- SCREENSHOT: adk web, step4_tribun, the events panel showing two rounds and the exit_loop call -->

**Use it when** feedback makes the result better, and you can tell when the result is good enough. Examples: a draft and an editor, code and a test runner, a plan and a reviewer.

**Do not use it when** you cannot write a clear stop condition, or when one good prompt is sufficient. Each round costs two or more model calls.

**The gotcha: a loop needs a clear stop and a safety limit.** `exit_loop` is the stop: it sets `escalate = True`. `max_iterations=3` is the safety limit. Without it, a critic that never agrees can use all of your quota. Also keep the `?` in `{tribun_feedback?}`. In round one, the key does not exist. Without the `?`, ADK raises a `KeyError`.

## Step 5 · Technical Director

**The pattern:** an orchestrator is an `LlmAgent` that has other agents as tools. It selects the team to call. Then it writes the final answer.

[![Step 5: technical_director calls four teams wrapped in AgentTool, scout, match_prep, scouting_department and tribun_review, picking each by its description, plus three direct data tools](images/step5-technical-director.svg)](images/step5-technical-director.svg "Open full size")

*The director selects a team by its description. It calls the team like a function and gets the answer back. Tap to open full size.*

The tools of the director are the teams from steps 1 to 4. Each team is in an `AgentTool`. The director also has three data tools. ✏️ **BLANK 5a** · the descriptions, in `steps/step5_technical_director/agent.py`:

<!-- source: steps/step5_technical_director/agent.py blank: 5a -->
```python
# Delegation is driven by these descriptions: they are all the director knows about each team.
SCOUT = "Answers questions about ONE player or ONE team: form, minutes, goals, ratings, availability."
MATCH_PREP = "Writes Sunday's game plan: opponent analysis, then tactics, then an XI of available players."
SCOUTING_DEPT = "Full scouting report on Sunday's opponent: threats, weaknesses, cards and the referee."
TRIBUN = "Picks a final XI and has the home crowd stress-test it. Only when asked to pick or defend the XI."
# Try it live: uncomment these, ask the same questions again, and watch the routing go wrong.
# SCOUT = "Helps with football."
# SCOUTING_DEPT = "Also helps with football."
```

✏️ **BLANK 5b** · the same file, at the start of `build_technical_director`:

<!-- source: steps/step5_technical_director/agent.py blank: 5b -->
```python
    # Each team becomes a tool: the director calls it like a function and gets its answer back.
    teams = [
        AgentTool(build_scout(description=SCOUT)),
        AgentTool(build_match_prep(description=MATCH_PREP)),
        AgentTool(build_scouting_department(description=SCOUTING_DEPT)),
        AgentTool(build_tribun(description=TRIBUN)),
    ]
```

**Run it:** In the dev UI, select `step5_technical_director`. Ask three different questions. The first question is *"Should we rest Salah for Freiburg on Thursday?"*

The director called the scout and `get_fixtures`. A part of its answer:

> - **4 days of rest** between Gaziantep FK and Freiburg (H, Nov 5).
> - **Verdict:** A full benching on Sunday is unnecessary given the 4-day recovery window ahead of Thursday's match. … start Salah against Gaziantep FK and withdraw him around the 60-minute mark once the match is secured.

The second question is *"If we win 2-0, where do we stand?"*

The director called `project_table` one time. It did not need a team:

> - **Trabzonspor Position:** Moves from **3rd to 1st**
> - **Points:** Increases from **19 to 22**
> - **Goal Difference:** Improves from **+14 to +16**
>
> 1. **Trabzonspor:** 22 pts (+16 GD, 10 played)
> 2. **Galatasaray:** 22 pts (+7 GD, 9 played)

The third question asks for the full briefing: *"Bizi pazara hazırla"* ("get us ready for Sunday"). The director called `scouting_department` and then `match_prep`. Seven agents worked on the answer. The director answered in Turkish after 222 seconds:

> **Zafiyetler**
> - **İkinci Yarı Savunma Düşüşü:** Son 10 maçta 15 gol yediler (maç başına 1.50 gol; …). 15 golün 10'u (%67) ikinci yarıda yendi.
>
> **Forvet**
> - **ST:** **Mohamed Salah** (Lig sezonu: 9 maç, 8 gol, 3 asist, 8.01 FotMob reytingi; son 10 maç: 10 maç, 802 dakika, 8 gol, 5 asist)

The answer gives the correct number: 10 of their 15 goals conceded (67%) came in the second half. It also keeps the league-season numbers of Salah apart from his last-10 numbers. Both results come from a fix. The lesson below explains it.

<!-- SCREENSHOT: adk web, step5_technical_director, the trace view of "Bizi pazara hazırla" with the scouting_department and match_prep tool calls -->

**Use it when** the questions are different and need different specialists, and you want one voice to answer.

**Do not use it when** the route is always the same. For a fixed route, a workflow agent is cheaper and more predictable. Also do not use it when one agent with more tools is sufficient.

**The gotchas: three gotchas and one lesson.**

- **Descriptions control the routing.** The director does not see the instructions or the code of a team. It sees only the name and the `description`. Remove the `#` from the two vague descriptions in the file, and ask the same questions again. The director selects the wrong team. A good description tells what the team does and when to use it.
- **One parent for each agent.** In ADK, an agent instance can have only one parent. Thus, step 5 cannot use the `scout` object from step 1 again. For this reason, each step has a `build_*()` function that makes new instances.
- **`AgentTool` or `sub_agents`.** With `sub_agents`, the director *transfers* the conversation. The team answers the user, and the director does not see the answer. With `AgentTool`, the director *calls* the team. It gets the final answer as a tool result and stays in control. For a briefing that combines teams, use `AgentTool`.

The lesson comes from my first run. The scouts wrote "60% of goals conceded come in two windows, 46–60' and 76–90'". The director made a summary of this summary and wrote "60% come in the second half". This is wrong: the correct number is 10 of 15, or 67%. I did not fix this with a stricter prompt. I fixed the tool: `get_team_trends` now also returns the totals for each half. Now no agent adds windows together. Give an orchestrator calculated numbers to quote, not parts to put together.

## Bonus · Live data over MCP

All the steps so far use a snapshot. The bonus changes the data source. It uses the same scout from step 1, but with a live football server instead of local JSON.

[![Bonus: the same build_scout factory gets either the five local tools over the JSON snapshot, or an McpToolset that talks to livescoremcp.com over SSE](images/bonus-live-mcp.svg)](images/bonus-live-mcp.svg "Open full size")

*The same agent with different tools. The instruction and the model do not change. Tap to open full size.*

<!-- source: steps/bonus_live_mcp/agent.py -->
```python
live_football = McpToolset(
    connection_params=SseConnectionParams(url="https://livescoremcp.com/sse", timeout=15),
    # The server has 16 tools; expose only the ones a scout needs, to keep the prompt small.
    tool_filter=["search", "get_team", "get_player", "get_match", "get_standings", "get_head_to_head"],
)

root_agent = build_scout(name="live_scout", tools=[live_football])
```

[MCP](https://modelcontextprotocol.io) (Model Context Protocol) is a standard way for a server to give tools to an agent. ADK gets the tool list from the server. It gives these tools to the model like Python functions. `tool_filter` keeps six of the sixteen tools. MCP support is in the optional `google-adk[mcp]` extra, and this repo includes it.

I asked: *"What were Trabzonspor's last three results, and who scored?"*

The scout made four calls to the live server: `get_team` one time and `get_match` three times. It answered in 18 seconds:

> - **26/10/2026 · Süper Lig: Rizespor 3 - 4 Trabzonspor** · Our scorers: Melih Kabasakal (49'), Aral Şimşir (51'), Franculino (57', 83')
> - **22/10/2026 · UEFA Europa Conference League: Trabzonspor 2 - 0 Heart of Midlothian** · Our scorers: Mohamed Salah (32' pen.), Franculino (58')
> - **19/10/2026 · Süper Lig: Trabzonspor 2 - 0 Beşiktaş J.K.** · Our scorers: Ozan Tufan (21'), Mohamed Salah (71')

The results are the same as in the snapshot, but they come from a different source. The agent code did not change. The server is free, but it accepts only 30 requests per minute from each IP address. All the people in one room share one Wi-Fi network, so they share this limit. For this reason, only I ran this step at the workshop.

## Which recipe when

| You need… | Use | In this repo |
|---|---|---|
| One job, a few tools, some judgement | `LlmAgent` with tools | Step 1 · Scout |
| Fixed steps, each using the last one's output | `SequentialAgent` + `output_key` + `{placeholders}` | Step 2 · Match Prep |
| Independent work on the same input, in less time | `ParallelAgent`, then a merge step | Step 3 · Scouting Department |
| A better result after each review | `LoopAgent` + a critic + `exit_loop` + `max_iterations` | Step 4 · Tribün |
| Different questions need different specialists | `LlmAgent` orchestrator + `AgentTool` + clear descriptions | Step 5 · Technical Director |
| The same agent on another data source | `McpToolset` instead of local tools | Bonus · live MCP |

Some rules apply to all the patterns. Let tools do the calculations. Return small dicts, with "not available" instead of `null`. Make agents with factory functions. Keep the model name in one place.

## Try it yourself

Try these changes. Add a `compare_players` tool to the scout, and ask *"Salah mı Franculino mu daha formda?"* Give the scouting department a fourth scout. Make the Tribün stricter and count the rounds. Then set `max_iterations=1`. Use the vague descriptions and see how the director fails. The README of the repo has one challenge for each step.

The code, the data, the Colab notebook and the tests are at [github.com/omarcevi/trabzonspor_analyst](https://github.com/omarcevi/trabzonspor_analyst). The data is a FotMob and ESPN snapshot from 30 October 2026. The injury news can be different now.

Thank you to GDG Trabzon for DevFest Trabzon 2026. Thank you also to all the people who built a football staff from agents with me on that Saturday.
