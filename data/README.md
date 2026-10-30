# Match Day Agents — workshop data

Trabzonspor vs Gaziantep FK · Süper Lig Round 10 · Sun 1 Nov 2026, 16:00 Istanbul (13:00 UTC) · Papara Park
Snapshot taken 30 Oct 2026 from FotMob, ESPN and Turkish match reports. Source URLs are inside each file.

## Files
| File | What's in it | Used by |
|---|---|---|
| match.json | Fixture, referee (avg cards/fouls), coaches, last formations, head-to-head, top players | Every agent (context) |
| squad.json | Trabzonspor: 34 players, availability for Sunday, per-player last-10 stats (minutes, goals, assists, cards, avg rating, rating per match), team trends | Scout, Lineup Picker, Tribün |
| opponent.json | Gaziantep FK: same structure as squad.json | Opponent Analyst, scouts |
| results.json | Last 10 competitive matches for each team: score, goals with minutes and assists, cards, possession, xG, shots, formations, lineups with ratings | Scouts, trend tools |
| standings.json | Süper Lig table after Round 9 | Technical Director |
| fixtures.json | Next fixtures for both teams (Freiburg on Thu 5 Nov) | Tribün, Technical Director |

`trends_last10` in squad.json and opponent.json is pre-computed in Python: W/D/L, goals, clean sheets, avg xG, home/away split, goals per 15-minute window. Agents should read these instead of doing arithmetic.

## Storylines already in the data
- Trabzonspor at home in this sample: 4 played, 4 won, 13–0. Gaziantep have no home wins this season but 3 away wins.
- Gaziantep concede late: 5 of their 15 goals against came after 75'.
- Trabzonspor won their last 6 straight; Gaziantep lost their last 4 league games before a cup win.
- Salah: 8 goals, 5 assists in the last 10. Franculino (7 goals) is doubtful with a muscle injury.
- Gaziantep's most-used player, Abena, is suspended (he picked up 4 yellows in the last 10). Kozłowski (2G, 1A) is their creative hub.
- Sidny Lopes Cabral was sent off twice in Europe (second yellows): a discipline flag for the Tribün critic.
- Freiburg at home on Thursday: rotation dilemma for the Technical Director.
- Head-to-head: Gaziantep have never beaten Trabzonspor (9W 6D).

## Known gaps (null = not shown on the source, not zero)
- Shots on target, corners, fouls: Gaziantep league games and 2 Trabzonspor games only.
- Half-time scores: mostly derived from goal minutes (noted per match).
- Player ratings missing for Trabzonspor's Samsunspor and Rizespor games and Gaziantep's cup game.
- Yellow-card suspension thresholds: not reported by any source.
- Two Trabzonspor matches (Samsunspor, Rizespor) use aggregator stats, so their xG may not be comparable with the FotMob ones.
- Check before going on stage: injury news on Saturday morning; Salah at Trabzonspor is as FotMob lists it.
