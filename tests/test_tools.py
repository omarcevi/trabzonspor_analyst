"""Tool tests. No LLM calls: these run offline in a second."""

from types import SimpleNamespace

import pytest

from matchday import tools as t
from matchday.tools import NA


def no_nulls(value) -> bool:
    """True when no None is left anywhere: nulls must reach the model as 'not available'."""
    if value is None:
        return False
    if isinstance(value, dict):
        return all(no_nulls(v) for v in value.values())
    if isinstance(value, list):
        return all(no_nulls(v) for v in value)
    return True


# --- name matching ------------------------------------------------------------------


@pytest.mark.parametrize(
    "query, expected",
    [
        ("kozlowski", "Kacper Kozłowski"),
        ("simsir", "Aral Şimşir"),
        ("KIZILDAG", "Arda Kızıldağ"),
        ("ibrahim alkis", "İbrahim Alkış"),
        ("Mohamed Salah", "Mohamed Salah"),
        ("  salah ", "Mohamed Salah"),
        ("lopes cabral", "Sidny Lopes Cabral"),
        ("Kozlovski", "Kacper Kozłowski"),  # typo, fuzzy match
        ("yokuslu", "Okay Yokuşlu"),
    ],
)
def test_get_player_matches_names_without_turkish_or_polish_letters(query, expected):
    assert t.get_player(query)["name"] == expected


def test_get_player_ambiguous_name_lists_candidates():
    result = t.get_player("Kacper")
    assert "error" in result
    assert {m["name"] for m in result["matches"]} == {"Kacper Tobiasz", "Kacper Kozłowski"}


def test_get_player_unknown_name_returns_error_with_suggestions():
    result = t.get_player("Messi")
    assert "error" in result and result["suggestions"] == []
    near = t.get_player("Kozlowsky Jan")
    assert "error" in near and "Kacper Kozłowski" in near["suggestions"]


def test_get_player_empty_name_is_an_error():
    assert "error" in t.get_player("")


# --- player stats and nulls ---------------------------------------------------------


def test_get_player_stats_and_computed_fields():
    salah = t.get_player("salah")
    assert salah["team"] == "Trabzonspor"
    assert salah["availability"] == {"status": "available"}
    s = salah["last10"]
    assert (s["goals"], s["assists"], s["goal_involvements"]) == (8, 5, 13)
    assert s["minutes_per_goal_involvement"] == round(802 / 13)
    assert s["avg_rating_last3_rated"] == round((8.7 + 8.4 + 8.3) / 3, 2)


def test_get_player_null_rating_becomes_not_available():
    ratings = {r["opponent"]: r["rating"] for r in t.get_player("salah")["last10"]["ratings_by_match"]}
    assert ratings["Samsunspor"] == NA
    assert ratings["Galatasaray"] == 9.8


def test_get_player_without_appearances_and_without_ratings():
    assert t.get_player("Ahmet Yıldırım")["last10"].startswith("No appearances")
    akcay = t.get_player("Kuzey Akçay")["last10"]
    assert akcay["avg_rating"] == NA and akcay["avg_rating_last3_rated"] == NA
    genc = t.get_player("Mehmet Ali Genç")
    assert genc["position"] == NA and genc["shirt_number"] == 93
    assert t.get_player("Taha Güneş")["shirt_number"] == NA


def test_get_player_doubtful_player_has_reason():
    franculino = t.get_player("franculino")
    assert franculino["availability"] == {"status": "doubtful", "reason": "Muscle injury", "expected_return": "Doubtful"}


# --- availability -------------------------------------------------------------------


def test_get_availability_trabzonspor():
    result = t.get_availability("Trabzonspor")
    assert {p["name"] for p in result["out"]} == {"Okay Yokuşlu", "Arseniy Batagov", "Ruslan Malinovsky", "Paul Onuachu"}
    assert {p["name"] for p in result["doubtful"]} == {"Onuralp Çevikkan", "Cihan Çanak", "Franculino"}
    listed = len(result["out"]) + len(result["doubtful"]) + len(result["not_in_current_squad_list"])
    assert result["available_players"] + listed == 34


def test_get_availability_gaziantep_suspension():
    result = t.get_availability("gaziantep")
    abena = next(p for p in result["out"] if p["name"] == "Myenty Abena")
    assert abena["reason"] == "Suspended" and abena["last10_minutes"] == 851
    assert [p["name"] for p in result["not_in_current_squad_list"]] == ["Mehmet Ali Genç"]


@pytest.mark.parametrize("alias, team", [("us", "Trabzonspor"), ("TRABZON", "Trabzonspor"), ("Antep", "Gaziantep FK"),
                                         ("Gaziantep FK", "Gaziantep FK"), ("opponent", "Gaziantep FK")])
def test_team_aliases(alias, team):
    assert t.get_availability(alias)["team"] == team


def test_unknown_team_returns_error_for_every_team_tool():
    for tool in (t.get_availability, t.get_team_trends, t.get_matches, t.get_top_players, t.get_discipline, t.get_fixtures):
        result = tool("Fenerbahçe")
        assert "error" in result and result["suggestions"] == ["Trabzonspor", "Gaziantep FK"]


# --- trends and matches ---------------------------------------------------------------


def test_get_team_trends_home_record_and_late_goals():
    ts = t.get_team_trends("Trabzonspor")
    home = ts["trends_last10"]["home_away"]["home"]
    assert (home["p"], home["w"], home["gf"], home["ga"], home["points_per_game"]) == (4, 4, 13, 0, 3.0)
    assert ts["league_position"]["position"] == 3

    gfk = t.get_team_trends("Gaziantep FK")["trends_last10"]
    late = gfk["goals_by_15min"]["76-90"]
    assert late["conceded"] == 5 and late["pct_of_goals_conceded"] == round(100 * 5 / 15)
    second = gfk["goals_by_half"]["second_half_46_90"]
    assert (second["conceded"], second["pct_of_goals_conceded"]) == (10, 67)
    first = gfk["goals_by_half"]["first_half_1_45"]
    assert first["scored"] + second["scored"] == gfk["goals_for"]
    assert gfk["home_away"]["home"]["w"] == 0 and gfk["home_away"]["away"]["w"] == 3


def test_get_matches_newest_first_with_scorers_and_xg():
    result = t.get_matches("Trabzonspor", last_n=3)
    assert result["count"] == 3
    assert [m["date"] for m in result["matches"]] == ["2026-10-26", "2026-10-22", "2026-10-19"]
    hearts = result["matches"][1]
    assert hearts["score"] == "Trabzonspor 2-0 Hearts" and hearts["result"] == "W"
    assert hearts["goals"][0] == "32' Mohamed Salah (Trabzonspor, penalty)"
    assert (hearts["xg_for"], hearts["xg_against"], hearts["home_or_away"]) == (1.49, 0.66, "H")


def test_get_matches_stoppage_time_and_competition_filters():
    kups = t.get_matches("Trabzonspor", 10, "europe")["matches"]
    assert {m["competition"] for m in kups} == {"UEFA Conference League", "UEFA Europa League Qualification"}
    assert "90+1' Franculino (Trabzonspor)" in next(m for m in kups if m["opponent"] == "KuPS")["goals"]
    league = t.get_matches("Gaziantep FK", 10, "league")
    assert league["count"] == 9 and all(m["competition"] == "Süper Lig" for m in league["matches"])


def test_get_matches_null_xg_is_not_available():
    cup = t.get_matches("Gaziantep FK", 10, "cup")["matches"][0]
    assert cup["xg_for"] == NA and cup["possession"] == NA


def test_get_matches_clamps_and_rejects_bad_input():
    assert t.get_matches("Trabzonspor", last_n=0)["count"] == 1
    assert t.get_matches("Trabzonspor", last_n=99)["count"] == 10
    assert "error" in t.get_matches("Trabzonspor", competition="friendly")


# --- rankings and discipline -----------------------------------------------------------


def test_get_top_players_goals_and_ratings():
    goals = t.get_top_players("Trabzonspor", "goals", 2)["players"]
    assert [(p["name"], p["goals"]) for p in goals] == [("Mohamed Salah", 8), ("Franculino", 7)]
    assert goals[1]["availability"] == "doubtful"

    rated = t.get_top_players("Trabzonspor", "avg_rating", 15)["players"]
    assert "Batista Mendy" not in {p["name"] for p in rated}  # only 2 rated matches
    assert rated == sorted(rated, key=lambda p: -p["avg_rating"])


def test_get_top_players_metric_validation_and_aliases():
    assert "error" in t.get_top_players("Trabzonspor", "tackles")
    assert t.get_top_players("Gaziantep FK", "yellows", 1)["players"][0]["name"] == "Myenty Abena"
    assert t.get_top_players("Gaziantep FK", "minutes", 1)["players"][0]["minutes"] == 851
    assert len(t.get_top_players("Trabzonspor", "goals", 100)["players"]) <= 15


def test_get_discipline_red_cards_and_referee():
    result = t.get_discipline("Trabzonspor")
    reds = result["red_cards"]
    assert len(reds) == 4
    assert sum(r["player"] == "Sidny Lopes Cabral" and r["type"] == "second yellow" for r in reds) == 2
    assert result["players_with_cards"][0]["name"] == "Sidny Lopes Cabral"
    assert result["team_totals_last10"] == {"matches": 10, "yellow_cards": 23, "red_cards": 4, "yellow_cards_per_match": 2.3}
    assert result["referee"]["yellow_cards_per_match"] == 3.6
    assert result["referee"]["red_cards_per_match"] == NA
    assert result["suspension_thresholds"] == NA


# --- fixtures, table, scenario -----------------------------------------------------------


def test_get_match_info():
    info = t.get_match_info()
    assert (info["home_team"], info["away_team"], info["kickoff_istanbul"]) == ("Trabzonspor", "Gaziantep FK", "16:00 (UTC+3)")
    assert (info["head_to_head"]["Trabzonspor_wins"], info["head_to_head"]["draws"]) == (9, 6)
    assert info["referee"]["penalties_per_match"] == NA
    assert info["top_players_league_season"]["Trabzonspor"]["assists"] == 3  # league season, not last 10 (5)


def test_get_standings_always_includes_both_teams():
    table = t.get_standings(3)["table"]
    assert [r["team"] for r in table] == ["Galatasaray", "Amed SFK", "Trabzonspor", "Gaziantep FK"]
    assert len(t.get_standings()["table"]) == 18


def test_get_fixtures_rest_days():
    ts = t.get_fixtures("Trabzonspor")["fixtures"]
    freiburg = next(f for f in ts if f["opponent"] == "Freiburg")
    assert (freiburg["weekday"], freiburg["days_since_previous_match"], freiburg["home_or_away"]) == ("Thursday", 4, "H")
    gfk = t.get_fixtures("Gaziantep FK")["fixtures"]
    assert gfk[0]["opponent"] == "Trabzonspor" and gfk[0]["home_or_away"] == "A"
    assert gfk[1]["opponent"] == "Kasımpaşa" and gfk[1]["days_since_previous_match"] == 5


def test_project_table_win_draw_loss():
    win = t.project_table(2, 0)
    assert win["Trabzonspor"]["points_after"] == 22 and win["Trabzonspor"]["position_after"] == 1
    assert win["Gaziantep FK"]["goal_difference_after"] == -8
    assert win["top_5_after"][1] == {"position": 2, "team": "Galatasaray", "played": 9, "goal_difference": 7, "points": 22}

    draw = t.project_table(1, 1)
    assert (draw["Trabzonspor"]["points_after"], draw["Gaziantep FK"]["points_after"]) == (20, 9)

    loss = t.project_table(0, 1)
    assert loss["Trabzonspor"]["position_after"] == 3 and loss["Gaziantep FK"]["points_after"] == 11


def test_project_table_does_not_change_the_data():
    t.project_table(5, 0)
    assert t.get_standings()["table"][2]["points"] == 19
    assert t.project_table(2, 0) == t.project_table(2, 0)


@pytest.mark.parametrize("args", [(-1, 0), (0, 21), ("two", 0)])
def test_project_table_rejects_bad_scores(args):
    assert "error" in t.project_table(*args)


# --- loop control and general contract ---------------------------------------------------


def test_exit_loop_escalates():
    ctx = SimpleNamespace(actions=SimpleNamespace(escalate=False))
    assert t.exit_loop(ctx) == {"status": "approved"}
    assert ctx.actions.escalate is True


def test_no_tool_leaks_a_null():
    results = [
        t.get_player("salah"), t.get_player("Ahmet Yıldırım"), t.get_player("Kuzey Akçay"), t.get_player("Mehmet Ali Genç"),
        t.get_availability("Trabzonspor"), t.get_availability("Gaziantep FK"),
        t.get_team_trends("Trabzonspor"), t.get_team_trends("Gaziantep FK"),
        t.get_matches("Trabzonspor", 10), t.get_matches("Gaziantep FK", 10),
        t.get_top_players("Gaziantep FK", "avg_rating", 15), t.get_discipline("Gaziantep FK"),
        t.get_match_info(), t.get_standings(), t.get_fixtures("Gaziantep FK"), t.project_table(3, 3),
    ]
    for result in results:
        assert no_nulls(result), result
