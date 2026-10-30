# Building Trabzonspor's AI Analysis Room

Agent recipes with Google's Agent Development Kit.

> **Türkçe özet:** Cumartesi gecesi. Trabzonspor pazar günü Gaziantep FK'yı ağırlıyor ve sen kulübün yeni yapay zekâ analiz ekibisin. Bu atölyede Google'ın Agent Development Kit'i (ADK) ile beş temel ajan desenini, iki takımın son 10 maçından gelen gerçek verilerle kuruyorsun: tek ajan, sıralı ekip, paralel ekip, döngü (Tribün) ve hepsini yöneten Teknik Direktör. Kurulum aşağıda üç adım. Ajanlara Türkçe yazabilirsin; onlar da Türkçe cevap verir.

DevFest Trabzon 2026 workshop (90 minutes). You build the five core agent patterns with [Google ADK](https://adk.dev) (Python), one Trabzonspor staff member at a time, on real data from both teams' last 10 matches.

[![The whole staff: the Technical Director delegates to the four teams](guide/images/overview.svg)](guide/images/overview.svg "Open full size")

*The whole staff. Every box with the ADK logo is an agent; the director calls the four teams as tools.*

## Setup (3 steps)

1. **Install uv:** `curl -LsSf https://astral.sh/uv/install.sh | sh` (Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`).
2. **Get a free Gemini API key** at [aistudio.google.com/apikey](https://aistudio.google.com/apikey), then `cp .env.example .env` and paste it into `.env`.
3. **Run it:** `uv sync && uv run adk web --reload_agents steps`, open http://localhost:8000 and pick a step from the dropdown.

**Or use Cloud Shell, with nothing to install.** It copies the repo and opens a tutorial panel next to the editor. Its links open each file and select each BLANK for you. In the dialog, select **Trust repo**, then **Confirm**:

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/omarcevi/trabzonspor_analyst.git&cloudshell_git_branch=main&cloudshell_tutorial=tutorial.md&cloudshell_workspace=.&show=ide%2Cterminal)

No luck on your laptop? Use the **Colab fallback**: [notebook/match_day_agents.ipynb](notebook/match_day_agents.ipynb) · [Open in Colab](https://colab.research.google.com/github/omarcevi/trabzonspor_analyst/blob/main/notebook/match_day_agents.ipynb)

## Two branches

- **`main`** (you start here): each step's key code is a ✏️ BLANK. The [guide](guide/match-day-agents.md) shows the code for every blank: select the BLANK line in the file, paste the code over it, save, and run the step. `adk web --reload_agents` picks up the change; no restart needed.
- **`demo`**: the finished agent team, every blank filled. `git switch demo` to see where you're heading.

Fell behind? `uv run python scripts/blanks.py fill 3` pastes BLANK 3 for you (`list` shows what's still empty, `fill all` does everything).

## The five steps

| Step | Pattern | What you build | Demo prompt |
|---|---|---|---|
| 1 · `step1_scout` | `LlmAgent` + tools | The Scout: answers player and team questions from the data | *Who's in form for us, and who can't play Sunday?* |
| 2 · `step2_match_prep` | `SequentialAgent` | Opponent analyst → tactician → lineup picker, handing work over through state | *Prepare Sunday's game plan.* |
| 3 · `step3_scouting_dept` | `ParallelAgent` in a `SequentialAgent` | Three scouts at once, then a report writer merges them | *Scout Gaziantep for us.* |
| 4 · `step4_tribun` | `LoopAgent` | The lineup picker vs. the Tribün (the home crowd) until the crowd approves | *Pick the XI for Sunday.* |
| 5 · `step5_technical_director` | Orchestrator with `AgentTool` | The Technical Director: delegates to the teams above and writes the briefing | *Should we rest Salah for Freiburg on Thursday?* · *If we win 2-0, where do we stand?* · *Bizi pazara hazırla* |
| Bonus · `bonus_live_mcp` | `McpToolset` over SSE | The same Scout on a live football MCP server (speaker only: 30 requests/min per IP) | *What were Trabzonspor's last three results, and who scored?* |

<details>
<summary>Diagrams for each step</summary>

[![Step 1: the Scout](guide/images/step1-scout.svg)](guide/images/step1-scout.svg "Open full size")
[![Step 2: Match Prep](guide/images/step2-match-prep.svg)](guide/images/step2-match-prep.svg "Open full size")
[![Step 3: Scouting Department](guide/images/step3-scouting-dept.svg)](guide/images/step3-scouting-dept.svg "Open full size")
[![Step 4: Tribün](guide/images/step4-tribun.svg)](guide/images/step4-tribun.svg "Open full size")
[![Step 5: Technical Director](guide/images/step5-technical-director.svg)](guide/images/step5-technical-director.svg "Open full size")
[![Bonus: live MCP](guide/images/bonus-live-mcp.svg)](guide/images/bonus-live-mcp.svg "Open full size")

</details>

All data tools live in [`matchday/tools.py`](matchday/tools.py), and the model is set in one place, [`matchday/config.py`](matchday/config.py) (or `MODEL` in `.env`). The tools do every sum, average and ranking in Python; the agents only interpret the results.

## Try it yourself

1. **Scout:** add a `compare_players(name_a, name_b)` tool to `matchday/tools.py` and give it to the scout. Ask *"Salah mı Franculino mu daha formda?"*
2. **Match Prep:** add a fourth agent, `set_piece_coach`, that reads `{game_plan}` and writes `set_pieces`. Where does it go in the list, and why does the order matter?
3. **Scouting Department:** add a fourth scout (for example a `form_scout` that compares the last five results of both teams) and make the report writer use its output.
4. **Tribün:** make the crowd stricter: it rejects any XI with fewer than two forwards at home, or with a player who has a red card in the last 10. How many rounds does it take now? What happens when you set `max_iterations=1`?
5. **Technical Director:** uncomment the vague descriptions in `steps/step5_technical_director/agent.py` and ask the same three questions. Then write a description so good that the director never picks the wrong team.

## Checks

```bash
uv run pytest                                   # tool tests, no LLM calls
uv run python scripts/smoke.py                  # each step once with its demo prompt (needs the key)
uv run python scripts/build_diagrams.py         # regenerate guide/images/*.svg
uv run --with playwright python scripts/render_diagrams.py   # render the diagrams and check the layout
```

The step-by-step written guide is in [guide/match-day-agents.md](guide/match-day-agents.md).

## About the data

`data/` is a snapshot taken on **30 October 2026** from [FotMob](https://www.fotmob.com), [ESPN](https://www.espn.com/soccer/standings/_/league/tur.1) and Turkish match reports; source URLs are inside each file and in [data/README.md](data/README.md). `null` means "not shown on the source", never zero, and the tools say "not available" instead of inventing a number. Injury news changes; check it on the morning of the match.

Built for DevFest Trabzon 2026 with GDG Trabzon.
