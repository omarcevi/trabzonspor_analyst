"""Data tools for the match-day agents.

Every tool is a plain Python function. ADK reads the type hints and the docstring
and turns them into the tool schema the model sees, so the docstrings are written
for the model.

LLMs interpret, tools count: every sum, average, percentage, ranking and table
position below is computed here in Python. The agents only read the results and
explain them. Ask a model to add up goals across ten matches and it will
sometimes get it wrong; ask Python and it never will.

Rules every tool follows:
- Return a small dict, never a whole file.
- `null` in the data means "not shown on the source", never zero. Tools turn it
  into the string "not available" so the model can't mistake it for a number.
- Bad input returns {"error": ..., "suggestions": [...]} instead of raising.
"""

from __future__ import annotations

import json
import os
import unicodedata
from datetime import date, datetime, timedelta
from difflib import get_close_matches
from functools import cache
from pathlib import Path

from google.adk.tools import ToolContext

DATA_DIR = Path(os.getenv("MATCHDAY_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
NA = "not available"
TEAMS = ("Trabzonspor", "Gaziantep FK")
METRICS = ("goals", "assists", "minutes", "avg_rating", "yellow_cards")
MIN_RATED_MATCHES = 3  # avg_rating rankings ignore players with fewer rated matches


# --- loading and matching helpers -------------------------------------------------


@cache
def _load(name: str) -> dict:
    return json.loads((DATA_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _fold(text: str) -> str:
    """Lowercase and strip accents so 'simsir' matches 'Şimşir' and 'kozlowski' 'Kozłowski'."""
    text = text.strip().lower().translate(str.maketrans({"ı": "i", "ł": "l", "ø": "o", "đ": "d", "ß": "ss"}))
    text = unicodedata.normalize("NFKD", text)
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


def _na(value):
    """null in the data means 'not shown on the source': say so instead of a number."""
    if value is None:
        return NA
    if isinstance(value, dict):
        return {k: _na(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_na(v) for v in value]
    return value


_TEAM_ALIASES = {
    "Trabzonspor": {"trabzonspor", "trabzon", "ts", "us", "we", "our team", "home", "biz", "bizim takim"},
    "Gaziantep FK": {"gaziantep fk", "gaziantep", "antep", "gfk", "opponent", "them", "away", "rakip"},
}


def _team(team: str) -> str | None:
    folded = _fold(team or "")
    for name, aliases in _TEAM_ALIASES.items():
        if folded in aliases or (len(folded) >= 4 and folded in _fold(name)) or _fold(name) in folded:
            return name
    return None


def _team_error(team: str) -> dict:
    return {"error": f"Unknown team '{team}'. The data covers two teams.", "suggestions": list(TEAMS)}


def _squad(team: str) -> dict:
    return _load("squad") if team == "Trabzonspor" else _load("opponent")


def _all_players() -> list[tuple[str, dict]]:
    return [(team, p) for team in TEAMS for p in _squad(team)["players"]]


def _find_players(name: str) -> list[tuple[str, dict]]:
    """Exact name, then every word of the query in the name, then a fuzzy match for typos."""
    query = _fold(name or "")
    if not query:
        return []
    players = _all_players()
    exact = [tp for tp in players if _fold(tp[1]["name"]) == query]
    if exact:
        return exact
    words = query.split()
    partial = [tp for tp in players if all(w in _fold(tp[1]["name"]).split() for w in words)]
    if not partial:
        partial = [tp for tp in players if query in _fold(tp[1]["name"])]
    if partial:
        return partial
    by_key: dict[str, tuple[str, dict]] = {}
    for tp in players:
        full = _fold(tp[1]["name"])
        by_key[full] = tp
        for part in full.split():
            if len(part) > 3:
                by_key.setdefault(part, tp)
    hits = get_close_matches(query, list(by_key), n=3, cutoff=0.8)
    return list({id(by_key[h][1]): by_key[h] for h in hits}.values())


def _suggest(name: str) -> list[str]:
    """Names that look like the query: compared with full names and with each surname."""
    keys: dict[str, str] = {}
    for _, p in _all_players():
        full = _fold(p["name"])
        keys[full] = p["name"]
        for part in full.split():
            keys.setdefault(part, p["name"])
    hits = get_close_matches(_fold(name or ""), list(keys), n=5, cutoff=0.7)
    return list(dict.fromkeys(keys[h] for h in hits))


def _availability(player: dict) -> dict:
    a = player["availability"]
    if a["status"] == "available":
        return {"status": "available"}
    return {"status": a["status"], "reason": a["reason"] or NA, "expected_return": a["expected_return"] or NA}


def _minute(event: dict) -> str:
    extra = event.get("added_time")
    return f"{event['minute']}+{extra}'" if extra else f"{event['minute']}'"


# --- player tools -----------------------------------------------------------------


def get_player(name: str) -> dict:
    """Look up one player of Trabzonspor or Gaziantep FK: profile, availability for Sunday and last-10-match stats.

    Name matching ignores case and Turkish or Polish letters, and accepts a surname only
    (for example "salah", "simsir", "kozlowski").

    Args:
        name: The player's name or surname.

    Returns:
        The player's team, position, availability (available, doubtful or out, with the
        reason) and stats from his team's last 10 matches: matches, starts, minutes,
        goals, assists, cards, average rating and the rating in each match.
    """
    found = _find_players(name)
    if not found:
        return {"error": f"No player called '{name}' in either squad.", "suggestions": _suggest(name)}
    if len(found) > 1:
        return {
            "error": f"'{name}' matches more than one player. Ask again with the full name.",
            "matches": [{"name": p["name"], "team": t, "position": p["position"] or NA} for t, p in found],
        }
    team, p = found[0]
    result = {
        "name": p["name"],
        "team": team,
        "shirt_number": p["shirt_number"],
        "position": p["position"],
        "position_group": p["position_group"],
        "age": p["age"],
        "nationality": p["nationality"],
        "availability": _availability(p),
    }
    stats = p["last10"]
    if stats is None:
        result["last10"] = "No appearances in the team's last 10 matches."
        return _na(result)
    ratings = [r["rating"] for r in stats["ratings_by_match"] if r["rating"] is not None]
    recent = ratings[-3:]
    result["last10"] = {
        **{k: v for k, v in stats.items() if k != "ratings_by_match"},
        "goal_involvements": stats["goals"] + stats["assists"],
        "minutes_per_goal_involvement": round(stats["minutes_approx"] / (stats["goals"] + stats["assists"]))
        if stats["goals"] + stats["assists"]
        else NA,
        "avg_rating_last3_rated": round(sum(recent) / len(recent), 2) if recent else NA,
        "ratings_by_match": [{"date": r["date"], "opponent": r["opponent"], "rating": r["rating"]} for r in stats["ratings_by_match"]],
    }
    return _na(result)


def get_availability(team: str) -> dict:
    """List the players of a team who are out or doubtful for Sunday's match, with the reason.

    Args:
        team: "Trabzonspor" or "Gaziantep FK".

    Returns:
        Players who are out, doubtful or not in the current squad list, each with position,
        reason, expected return and how much they played in the last 10 matches.
        Every player not listed is available.
    """
    name = _team(team)
    if not name:
        return _team_error(team)
    groups: dict[str, list] = {"out": [], "doubtful": [], "not_in_current_squad_list": []}
    available = 0
    for p in _squad(name)["players"]:
        status = p["availability"]["status"]
        if status == "available":
            available += 1
            continue
        stats = p["last10"] or {}
        groups[status].append({
            "name": p["name"],
            "position": p["position"] or NA,
            "reason": p["availability"]["reason"] or NA,
            "expected_return": p["availability"]["expected_return"] or NA,
            "last10_starts": stats.get("starts", 0),
            "last10_minutes": stats.get("minutes_approx", 0),
            "last10_goals": stats.get("goals", 0),
        })
    return {
        "team": name,
        **groups,
        "available_players": available,
        "note": "Players not listed are available. Suspension thresholds for yellow cards: not available.",
    }


def get_top_players(team: str, metric: str = "goals", n: int = 5) -> dict:
    """Rank a team's players over the last 10 matches by one metric.

    Args:
        team: "Trabzonspor" or "Gaziantep FK".
        metric: One of "goals", "assists", "minutes", "avg_rating", "yellow_cards".
        n: How many players to return (1 to 15).

    Returns:
        The top n players with the metric value, matches, minutes and availability for Sunday.
        avg_rating only ranks players with at least 3 rated matches.
    """
    name = _team(team)
    if not name:
        return _team_error(team)
    aliases = {"rating": "avg_rating", "ratings": "avg_rating", "minutes_approx": "minutes", "yellows": "yellow_cards",
               "cards": "yellow_cards", "yellow": "yellow_cards", "goal": "goals", "assist": "assists"}
    key = aliases.get(_fold(metric), _fold(metric))
    if key not in METRICS:
        return {"error": f"Unknown metric '{metric}'.", "suggestions": list(METRICS)}
    field = "minutes_approx" if key == "minutes" else key
    n = max(1, min(int(n), 15))
    rows = []
    for p in _squad(name)["players"]:
        s = p["last10"]
        if not s or s[field] is None:
            continue
        if key == "avg_rating" and s["rated_matches"] < MIN_RATED_MATCHES:
            continue
        rows.append({
            "name": p["name"],
            "position": p["position"] or NA,
            key: s[field],
            "matches": s["matches"],
            "minutes": s["minutes_approx"],
            "availability": p["availability"]["status"],
        })
    rows.sort(key=lambda r: (-r[key], -r["minutes"], r["name"]))
    result = {"team": name, "metric": key, "window": "last 10 matches", "players": rows[:n]}
    if key == "avg_rating":
        result["note"] = f"Only players with at least {MIN_RATED_MATCHES} rated matches; some matches have no ratings."
    return result


def get_discipline(team: str) -> dict:
    """Card risk for one team plus Sunday's referee: who collects cards, red cards, and the referee's averages.

    Args:
        team: "Trabzonspor" or "Gaziantep FK".

    Returns:
        Players with at least one card in the last 10 matches (most cards first) and their
        availability, every red card with date and minute, team card totals per match,
        and the referee's yellow card and foul averages.
    """
    name = _team(team)
    if not name:
        return _team_error(team)
    players = []
    for p in _squad(name)["players"]:
        s = p["last10"]
        if s and (s["yellow_cards"] or s["red_cards"]):
            players.append({
                "name": p["name"],
                "position": p["position"] or NA,
                "yellow_cards": s["yellow_cards"],
                "red_cards": s["red_cards"],
                "matches": s["matches"],
                "availability": p["availability"]["status"],
            })
    players.sort(key=lambda r: (-r["red_cards"], -r["yellow_cards"], r["name"]))
    matches = _load("results")[name]
    reds, yellows = [], 0
    for m in matches:
        for c in m["cards"] or []:
            if c["team"] != name:
                continue
            if c["card"] == "yellow":
                yellows += 1
            else:
                kind = "second yellow" if c["card"] == "second_yellow" else "straight red"
                reds.append({"date": m["date"], "opponent": m["opponent"], "player": c["player"], "minute": _minute(c), "type": kind})
    referee = _load("match")["referee"]
    return _na({
        "team": name,
        "players_with_cards": players,
        "red_cards": reds,
        "team_totals_last10": {
            "matches": len(matches),
            "yellow_cards": yellows,
            "red_cards": len(reds),
            "yellow_cards_per_match": round(yellows / len(matches), 1),
        },
        "referee": {k: v for k, v in referee.items() if k != "country"},
        "suspension_thresholds": NA,
        "note": "red_cards include second yellows; the first yellow of that match also counts as a yellow.",
    })


# --- team tools -------------------------------------------------------------------


def get_team_trends(team: str) -> dict:
    """A team's form over its last 10 matches and its league position.

    Args:
        team: "Trabzonspor" or "Gaziantep FK".

    Returns:
        Wins, draws, losses, goals, clean sheets, average xG, the home and away split,
        goals scored and conceded per 15-minute window and per half (with the share of all goals),
        the form string (oldest to newest) and the current league position.
    """
    name = _team(team)
    if not name:
        return _team_error(team)
    squad = _squad(name)
    t = dict(squad["trends_last10"])
    total_for, total_against = t["goals_for"], t["goals_against"]
    t["goals_by_15min"] = {
        window: {
            **g,
            "pct_of_goals_scored": round(100 * g["scored"] / total_for) if total_for else NA,
            "pct_of_goals_conceded": round(100 * g["conceded"] / total_against) if total_against else NA,
        }
        for window, g in t["goals_by_15min"].items()
    }
    t["goals_by_half"] = {}
    for half, windows in (("first_half_1_45", ("1-15", "16-30", "31-45")), ("second_half_46_90", ("46-60", "61-75", "76-90"))):
        scored = sum(t["goals_by_15min"][w]["scored"] for w in windows)
        conceded = sum(t["goals_by_15min"][w]["conceded"] for w in windows)
        t["goals_by_half"][half] = {
            "scored": scored,
            "conceded": conceded,
            "pct_of_goals_scored": round(100 * scored / total_for) if total_for else NA,
            "pct_of_goals_conceded": round(100 * conceded / total_against) if total_against else NA,
        }
    t["home_away"] = {
        side: {**r, "points_per_game": round((3 * r["w"] + r["d"]) / r["p"], 2) if r["p"] else NA}
        for side, r in t["home_away"].items()
    }
    t["xg_note"] = f"avg xG is over the {t['xg_matches']} matches that have xG data."
    position = {k: v for k, v in squad["league_position"].items() if k != "form"}
    return _na({"team": name, "trends_last10": t, "league_position": position})


def get_matches(team: str, last_n: int = 5, competition: str = "all") -> dict:
    """A team's most recent matches, newest first, as compact summaries.

    Args:
        team: "Trabzonspor" or "Gaziantep FK".
        last_n: How many matches (1 to 10).
        competition: "all", "league" (Süper Lig), "europe" (UEFA) or "cup" (Turkish Cup).

    Returns:
        For each match: date, competition, opponent, H or A, score, result (W/D/L),
        scorers with minutes, xG for and against, possession and the team's formation.
    """
    name = _team(team)
    if not name:
        return _team_error(team)
    comp = _fold(competition or "all")
    filters = {"all": lambda c: True, "league": lambda c: "super lig" in c, "europe": lambda c: "uefa" in c,
               "cup": lambda c: "cup" in c}
    if comp not in filters:
        return {"error": f"Unknown competition '{competition}'.", "suggestions": list(filters)}
    matches = [m for m in _load("results")[name] if filters[comp](_fold(m["competition"]))]
    last_n = max(1, min(int(last_n), 10))
    summaries = []
    for m in reversed(matches[-last_n:]):
        side, other = m["focus_side"], "away" if m["focus_side"] == "home" else "home"
        home, away = m["score"]["ft"]
        summaries.append({
            "date": m["date"],
            "competition": m["competition"],
            "opponent": m["opponent"],
            "home_or_away": "H" if side == "home" else "A",
            "score": f"{m['home_team']} {home}-{away} {m['away_team']}",
            "result": m["result"],
            "goals": [
                f"{_minute(g)} {g['scorer']} ({g['team']}{', ' + g['type'].replace('_', ' ') if g['type'] else ''})"
                for g in m["goals"]
            ],
            "xg_for": m["stats"][side]["xg"],
            "xg_against": m["stats"][other]["xg"],
            "possession": m["stats"][side]["possession"],
            "formation": m["formation"][side],
        })
    return _na({"team": name, "competition": comp, "count": len(summaries), "matches": summaries})


# --- fixture, table and scenario tools ---------------------------------------------


def get_match_info() -> dict:
    """Sunday's fixture: teams, kick-off, venue, referee averages, coaches, last formations, head-to-head and each team's top player (league season stats)."""
    m = _load("match")
    kickoff = datetime.fromisoformat(m["kickoff_utc"].replace("Z", "+00:00"))
    return _na({
        "home_team": m["home_team"],
        "away_team": m["away_team"],
        "competition": m["competition"],
        "round": m["round"],
        "date": m["date"],
        "kickoff_istanbul": (kickoff + timedelta(hours=3)).strftime("%H:%M") + " (UTC+3)",
        "venue": f"{m['venue']}, {m['city']}",
        "capacity": m["capacity"],
        "weather_forecast_temp_c": m["weather_forecast_temp_c"],
        "referee": m["referee"],
        "coaches": m["coaches"],
        "last_starting_formations": m["last_starting_formations"],
        "head_to_head": {k: v for k, v in m["head_to_head"].items() if k != "past_meetings"},
        "top_players_league_season": m["top_players"],
        "top_players_note": "Süper Lig season stats from FotMob. For last-10-match stats (all competitions) use get_player.",
        "insights": m["insights"],
    })


def get_standings(top_n: int = 20) -> dict:
    """The Süper Lig table as it is now (before Sunday's round).

    Args:
        top_n: How many rows from the top (1 to 18). Both of Sunday's teams are always included.

    Returns:
        Position, team, played, won, drawn, lost, goals for and against, goal difference and points.
    """
    s = _load("standings")
    rows = [{k: v for k, v in r.items() if k != "form"} for r in s["table"]]
    top_n = max(1, min(int(top_n), len(rows)))
    shown = rows[:top_n] + [r for r in rows[top_n:] if r["team"] in TEAMS]
    return {"competition": s["competition"], "season": s["season"], "after_round": s["after_round"], "table": shown}


def get_fixtures(team: str) -> dict:
    """A team's next fixtures after Sunday, with the rest days between matches.

    Args:
        team: "Trabzonspor" or "Gaziantep FK".

    Returns:
        Sunday's match plus each upcoming fixture: date, kick-off (UTC), competition,
        opponent, H or A, venue and days since the previous match.
    """
    name = _team(team)
    if not name:
        return _team_error(team)
    m = _load("match")
    sunday = {
        "date": m["date"], "kickoff_utc": m["kickoff_utc"], "competition": m["competition"], "round": m["round"],
        "home": m["home_team"], "away": m["away_team"], "venue": m["venue"],
        "home_away": "H" if m["home_team"] == name else "A",
    }
    upcoming = _load("fixtures")["trabzonspor_next" if name == "Trabzonspor" else "gaziantep_next"]
    rows, previous = [], None
    for f in [sunday, *upcoming]:
        day = date.fromisoformat(f["date"])
        rows.append({
            "date": f["date"],
            "weekday": day.strftime("%A"),
            "kickoff_utc": f["kickoff_utc"],
            "competition": f["competition"],
            "round": f["round"],
            "opponent": f["away"] if f["home"] == name else f["home"],
            "home_or_away": f["home_away"],
            "venue": f["venue"],
            "days_since_previous_match": (day - previous).days if previous else NA,
        })
        previous = day
    return {"team": name, "fixtures": rows}


def project_table(trabzonspor_goals: int, gaziantep_goals: int) -> dict:
    """Project the Süper Lig table if Sunday's match ends with this score. Other teams stay as they are now.

    Args:
        trabzonspor_goals: Goals Trabzonspor score on Sunday.
        gaziantep_goals: Goals Gaziantep FK score on Sunday.

    Returns:
        Points, goal difference and league position before and after for both teams,
        and the new top five.
    """
    # LLMs interpret, tools count: points, goal difference and positions are computed here.
    try:
        ts, gfk = int(trabzonspor_goals), int(gaziantep_goals)
    except (TypeError, ValueError):
        return {"error": "Scores must be whole numbers.", "suggestions": ["project_table(2, 0)"]}
    if not (0 <= ts <= 20 and 0 <= gfk <= 20):
        return {"error": "Scores must be between 0 and 20.", "suggestions": ["project_table(2, 0)"]}
    before = {r["team"]: r for r in _load("standings")["table"]}
    after = {team: dict(row) for team, row in before.items()}
    for team, scored, conceded in (("Trabzonspor", ts, gfk), ("Gaziantep FK", gfk, ts)):
        r = after[team]
        r["played"] += 1
        r["goals_for"] += scored
        r["goals_against"] += conceded
        r["goal_difference"] = r["goals_for"] - r["goals_against"]
        outcome = "won" if scored > conceded else "drawn" if scored == conceded else "lost"
        r[outcome] += 1
        r["points"] += {"won": 3, "drawn": 1, "lost": 0}[outcome]
    table = sorted(after.values(), key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["team"]))
    for position, r in enumerate(table, start=1):
        r["position"] = position

    def change(team: str) -> dict:
        b, a = before[team], after[team]
        return {
            "points_before": b["points"], "points_after": a["points"],
            "goal_difference_before": b["goal_difference"], "goal_difference_after": a["goal_difference"],
            "position_before": b["position"], "position_after": a["position"],
        }

    result = "draw" if ts == gfk else ("Trabzonspor win" if ts > gfk else "Gaziantep FK win")
    return {
        "scenario": f"Trabzonspor {ts}-{gfk} Gaziantep FK ({result})",
        "Trabzonspor": change("Trabzonspor"),
        "Gaziantep FK": change("Gaziantep FK"),
        "top_5_after": [{k: r[k] for k in ("position", "team", "played", "goal_difference", "points")} for r in table[:5]],
        "assumptions": "Other Round 10 matches not played yet. Ties broken by goal difference, then goals scored "
                       "(head-to-head tiebreaks not modelled).",
    }


# --- loop control -------------------------------------------------------------------


def exit_loop(tool_context: ToolContext) -> dict:
    """Approve the lineup and end the review. Call this only when every objection is resolved."""
    tool_context.actions.escalate = True  # tells the LoopAgent to stop after this agent
    return {"status": "approved"}
