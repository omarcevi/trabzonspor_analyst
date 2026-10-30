"""Build the guide's architecture diagrams as self-contained SVGs (same look as the earlier workshop guides).

    uv run python scripts/build_diagrams.py        # writes guide/images/*.svg

Every diagram uses the helpers below (card, zone, row, chip, arrow, badge, legend), so all
of them share exact colours, fonts and spacing. Icons are embedded as base64, so each SVG
works on its own. Replace guide/assets/adk-logo.png and re-run to update the logo everywhere.
Preview and layout checks: uv run --with playwright python scripts/render_diagrams.py
"""

from __future__ import annotations

import base64
import html
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "guide" / "assets"
OUT = ROOT / "guide" / "images"

FONT = "'Google Sans',Roboto,'Helvetica Neue',Arial,sans-serif"
MONO = "'Google Sans Code','Roboto Mono',Menlo,Consolas,monospace"
INK, MUTED, BORDER, BLUE, GREY = "#202124", "#5f6368", "#dadce0", "#1a73e8", "#80868b"
ROW, HIGHLIGHT = "#f1f3f4", "#e8f0fe"
ZONES = {  # fill, border
    "seq": ("#e8f0fe", "#aecbfa"),
    "par": ("#e6f4ea", "#a8dab5"),
    "loop": ("#fef7e0", "#fdd663"),
    "frame": ("#f8f9fa", "#dadce0"),
}
CHIPS = {  # fill, border, text, dashed
    "tool": (ROW, BORDER, "#3c4043", False),
    "state": ("#fff", GREY, "#3c4043", True),
    "exit": (HIGHLIGHT, "#aecbfa", BLUE, False),
    "mcp": ("#e8f0fe", "#aecbfa", "#174ea6", False),
}


def _png(name: str) -> str:
    return "data:image/png;base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


# Line icons in #80868b on a 32x32 grid, like the Customer icon in the reference diagrams.
LINE_ICONS = {
    "person": '<circle cx="16" cy="10" r="6"/><path d="M5 29a11 10 0 0 1 22 0"/>',
    "data": '<ellipse cx="16" cy="7" rx="10" ry="4"/><path d="M6 7v18a10 4 0 0 0 20 0V7"/><path d="M6 16a10 4 0 0 0 20 0"/>',
    "code": '<path d="M8 3h11l6 6v20H8z"/><path d="M19 3v6h6"/><path d="M14 15l-3 3 3 3M19 15l3 3-3 3"/>',
    "tools": '<path d="M12 5c-3 0-3 2-3 5s-1 5-3 6c2 1 3 3 3 6s0 5 3 5M20 5c3 0 3 2 3 5s1 5 3 6c-2 1-3 3-3 6s0 5-3 5"/>',
    "globe": '<circle cx="16" cy="16" r="12"/><ellipse cx="16" cy="16" rx="5" ry="12"/><path d="M4 16h24M6 10h20M6 22h20"/>',
    "check": '<circle cx="16" cy="16" r="12"/><path d="M10 16l4 4 8-8"/>',
}


def text_width(s: str, size: float, mono: bool = False, bold: bool = False) -> float:
    """Rough rendered width, used to size chips and label halos (render_diagrams.py checks the result)."""
    if mono:
        return len(s) * size * 0.6
    narrow, wide = set("il.,:;|!'()[]{}ftjrI1 "), set("mwMWGOQD@")
    units = sum(0.55 if c in narrow else 1.35 if c in wide else 1.25 if c.isupper() else 1.0 for c in s)
    return units * size * (0.53 if bold else 0.5)


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    def left(self, t: float = 0.5): return (self.x, self.y + self.h * t)
    def right(self, t: float = 0.5): return (self.x + self.w, self.y + self.h * t)
    def top(self, t: float = 0.5): return (self.x + self.w * t, self.y)
    def bottom(self, t: float = 0.5): return (self.x + self.w * t, self.y + self.h)


class Diagram:
    def __init__(self, name: str, w: int, h: int, title: str, subtitle: str):
        self.name, self.w, self.h = name, w, h
        self.layers: list[list[str]] = [[], [], [], []]  # zones, arrows, cards, labels and badges
        self.used: set[str] = set()
        self.alt = f"{title}. {subtitle}"
        self.icon("adk", 24, 15, 28, layer=3)
        self.text(60, 36, title, 18, INK, 600)
        self.text(60, 58, subtitle, 12.5, MUTED)

    # --- primitives --------------------------------------------------------------------

    def text(self, x, y, s, size=12, color=MUTED, weight=None, anchor="start", mono=False, italic=False,
             layer=3, inside: Box | None = None, halo=False):
        attrs = [f'x="{x:g}"', f'y="{y:g}"', f'font-size="{size:g}"', f'fill="{color}"']
        if weight:
            attrs.append(f'font-weight="{weight}"')
        if anchor != "start":
            attrs.append(f'text-anchor="{anchor}"')
        if mono:
            attrs.append(f'font-family="{MONO}"')
        if italic:
            attrs.append('font-style="italic"')
        if halo:
            attrs.append('stroke="#fff" stroke-width="5" stroke-linejoin="round" paint-order="stroke"')
        if inside:
            attrs.append(f'data-in="{inside.x:g},{inside.y:g},{inside.w:g},{inside.h:g}"')
        self.layers[layer].append(f"<text {' '.join(attrs)}>{html.escape(s)}</text>")

    def icon(self, name, x, y, size, layer=2):
        self.used.add(name)
        self.layers[layer].append(f'<use href="#i-{name}" x="{x:g}" y="{y:g}" width="{size}" height="{size}"/>')

    def rect(self, box: Box, fill, stroke, rx=8, dashed=False, layer=2, cls=None, width=1.2):
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        c = f' class="{cls}"' if cls else ""
        self.layers[layer].append(
            f'<rect{c} x="{box.x:g}" y="{box.y:g}" width="{box.w:g}" height="{box.h:g}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"{dash}/>')

    # --- building blocks -----------------------------------------------------------------

    def card(self, x, y, w, h, name, detail="", icon="adk", top=False, fill="#fff", dashed=False) -> Box:
        """White card with a 32px icon on the left, a bold name and a one-line detail.
        top=True puts the header at the top so rows and chips can go underneath."""
        box = Box(x, y, w, h)
        self.rect(box, fill, BORDER, dashed=dashed, cls="card")
        if top:
            self.icon(icon, x + 14, y + 14, 32)
            self.text(x + 58, y + 30, name, 14, INK, 600, inside=box)
            if detail:
                self.text(x + 58, y + 47, detail, 11.5, MUTED, inside=box)
        else:
            self.icon(icon, x + 14, y + h / 2 - 16, 32)
            self.text(x + 58, y + h / 2 + (-3 if detail else 5), name, 14, INK, 600, inside=box)
            if detail:
                self.text(x + 58, y + h / 2 + 15, detail, 11.5, MUTED, inside=box)
        return box

    def zone(self, x, y, w, h, label, kind="seq", sub="", icon="adk") -> Box:
        """Soft container for a workflow agent (or a plain frame), with a 20px icon and a label."""
        box = Box(x, y, w, h)
        fill, stroke = ZONES[kind]
        self.rect(box, fill, stroke, rx=10, layer=0)
        self.icon(icon, x + 14, y + 12, 20, layer=0)
        self.text(x + 42, y + 27, label, 14, INK, 600, inside=box)
        if sub:
            self.text(x + 42, y + 45, sub, 11.5, MUTED, inside=box)
        return box

    def row(self, x, y, w, label, highlight=False, h=28, mono=False, sub="") -> Box:
        """An inner strip (#f1f3f4), or #e8f0fe when highlighted."""
        box = Box(x, y, w, h)
        self.rect(box, HIGHLIGHT if highlight else ROW, "none", rx=6, width=0)
        size = 12 if mono else 12.5
        if sub:
            self.text(x + 10, y + h / 2 - 2, label, size, INK, 500, mono=mono, inside=box)
            self.text(x + 10, y + h / 2 + 13, sub, 11, MUTED, mono=True, inside=box)
        else:
            self.text(x + 10, y + h / 2 + 4.5, label, size, INK, 500 if not mono else None, mono=mono, inside=box)
        return box

    def chip(self, x, y, label, kind="tool") -> Box:
        fill, stroke, color, dashed = CHIPS[kind]
        if kind == "state":
            label = "→ " + label
        box = Box(x, y, text_width(label, 11.5, mono=True) + 16, 22)
        self.rect(box, fill, stroke, rx=11 if dashed else 5, dashed=dashed, width=1)
        self.text(x + 8, y + 15.5, label, 11.5, color, mono=True, inside=box)
        return box

    def chips(self, x, y, labels, max_w, kind="tool", gap=6) -> float:
        """Lay chips out left to right, wrapping at max_w. Returns the y below the last row."""
        cx, cy = x, y
        for label in labels:
            w = text_width(label, 11.5, mono=True) + 16
            if cx > x and cx + w > x + max_w:
                cx, cy = x, cy + 28
            self.chip(cx, cy, label, kind)
            cx += w + gap
        return cy + 22

    def person(self, cx, cy, label, sub=""):
        self.icon("person", cx - 22, cy - 26, 44)
        self.text(cx, cy + 36, label, 14, INK, 600, anchor="middle")
        if sub:
            self.text(cx, cy + 53, sub, 11.5, MUTED, anchor="middle")

    def arrow(self, *points, kind="main", label="", label_at=None, anchor="middle", badge=None, badge_at=None):
        """Right-angle polyline. main: blue with a filled head. aux: grey, dashed (tool calls, state)."""
        color = BLUE if kind == "main" else GREY
        dash = ' stroke-dasharray="6 4"' if kind == "aux" else ""
        d = "M" + " L".join(f"{x:g} {y:g}" for x, y in points)
        self.layers[1].append(
            f'<path class="arrow" d="{d}" fill="none" stroke="{color}" stroke-width="1.6"{dash} '
            f'marker-end="url(#head-{kind})"/>')
        if label:
            lx, ly = label_at or ((points[0][0] + points[-1][0]) / 2, (points[0][1] + points[-1][1]) / 2 - 8)
            self.text(lx, ly, label, 11.5, BLUE if kind == "main" else MUTED, 500, anchor=anchor, mono="_" in label,
                      halo=True)
        if badge is not None:
            bx, by = badge_at or _longest_midpoint(points)
            self.badge(bx, by, badge)

    def badge(self, x, y, n):
        self.layers[3].append(
            f'<g class="badge"><circle cx="{x:g}" cy="{y:g}" r="11" fill="{BLUE}"/><text x="{x:g}" y="{y + 4.3:g}" '
            f'font-size="12" font-weight="700" fill="#fff" text-anchor="middle">{n}</text></g>')

    def legend(self, items, cols=3, y=None, col_w=None, x=24):
        """Numbered legend along the bottom, explaining each badge in plain words."""
        rows = -(-len(items) // cols)
        y = y if y is not None else self.h - 24 - (rows - 1) * 30
        col_w = col_w or (self.w - 2 * x) / cols
        for i, item in enumerate(items):
            cx, cy = x + (i // rows) * col_w, y + (i % rows) * 30
            self.badge(cx + 11, cy - 4, i + 1)
            self.text(cx + 30, cy + 0.5, item, 13, INK)

    # --- output ---------------------------------------------------------------------------

    def svg(self) -> str:
        defs = [
            f'<marker id="head-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{c}"/></marker>'
            for k, c in (("main", BLUE), ("aux", GREY))
        ]
        for name in sorted(self.used):
            if name in LINE_ICONS:
                body = (f'<g fill="none" stroke="{GREY}" stroke-width="2" stroke-linecap="round" '
                        f'stroke-linejoin="round">{LINE_ICONS[name]}</g>')
            else:
                body = f'<image href="{_png("adk-logo.png" if name == "adk" else "gemini-sparkle.png")}" width="32" height="32"/>'
            defs.append(f'<symbol id="i-{name}" viewBox="0 0 32 32">{body}</symbol>')
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
            f'height="{self.h}" font-family="{FONT}" role="img" aria-label="{html.escape(self.alt)}">'
            f'<defs>{"".join(defs)}</defs><rect width="{self.w}" height="{self.h}" fill="#fff"/>'
            + "".join("".join(layer) for layer in self.layers) + "</svg>\n"
        )


def _longest_midpoint(points):
    segments = list(zip(points, points[1:]))
    (x1, y1), (x2, y2) = max(segments, key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
    return (x1 + x2) / 2, (y1 + y2) / 2


def agent_card(d: Diagram, x, y, w, h, name, detail, tools=(), output=None, reads=None, extra_chips=(),
               reads_note="") -> Box:
    """An LlmAgent: header, optional 'reads {key}' line, tool chips, and its output_key at the bottom."""
    box = d.card(x, y, w, h, name, detail, top=True)
    cy = y + 66
    if reads:
        d.text(x + 16, cy + 4, reads, 11.5, BLUE, mono=True, inside=box)
        if reads_note:
            d.text(x + 24 + text_width(reads, 11.5, mono=True), cy + 4, reads_note, 11.5, MUTED, inside=box)
        cy += 18
    if tools or extra_chips:
        cy = d.chips(x + 16, cy, list(tools), w - 32)
        if extra_chips:
            d.chips(x + 16, cy + 6, list(extra_chips), w - 32, kind="exit")
    if output:
        d.chip(x + 16, y + h - 34, output, kind="state")
    return box


# --- the diagrams ----------------------------------------------------------------------------


def step1() -> Diagram:
    d = Diagram("step1-scout", 1180, 600, "Step 1 · The Scout",
                "One LlmAgent: an instruction plus tools. Gemini picks the tools; Python does the counting.")
    d.person(110, 170, "You", "staff member")
    scout = d.card(260, 110, 430, 214, "scout", "LlmAgent · steps/step1_scout/agent.py", top=True)
    d.row(276, 176, 398, "instruction: the scout's role and how to answer")
    d.row(276, 212, 398, "+ HOUSE_RULES: your language, only tool numbers")
    d.row(276, 248, 398, "tools: five plain Python functions", highlight=True)
    d.text(276, 300, "model=MODEL (matchday/config.py)", 11.5, MUTED, mono=True, inside=scout)
    gem = d.card(870, 110, 290, 72, "gemini-3.8-flash", "MODEL · one place to change it", icon="gem")
    answer = d.card(20, 262, 170, 64, "Answer", "tool numbers only", icon="check")
    tools = d.zone(260, 384, 430, 130, "matchday/tools.py", "frame", "docstrings become the tool schemas", icon="code")
    d.chips(280, 444, ["get_player", "get_availability", "get_team_trends", "get_top_players", "get_matches"], 390)
    data = d.card(870, 416, 290, 72, "data/*.json", "squad · opponent · results · match", icon="data")
    d.arrow((150, 170), scout.left(60 / 214), badge=1)
    d.arrow(scout.right(36 / 214), gem.left(36 / 72), label="instruction + tool schemas", label_at=(780, 170), badge=2,
            badge_at=(780, 146))
    d.arrow((455, 324), (455, 384), badge=3, badge_at=(455, 354))
    d.arrow((535, 384), (535, 324), kind="aux", badge=4, badge_at=(535, 354))
    d.text(437, 358, "function call", 11.5, MUTED, anchor="end")
    d.text(553, 358, "small dict back", 11.5, MUTED)
    d.arrow(tools.right(70 / 130), data.left(38 / 72), kind="aux", label="reads, counts", label_at=(780, 446))
    d.arrow((260, 294), answer.right(), badge=5, badge_at=(225, 294))
    d.legend([
        "You ask, in Turkish or English",
        "Gemini reads the instruction and every docstring",
        "It asks ADK to run a tool with arguments",
        "The tool reads data/, does the maths, returns a dict",
        "The scout answers using only those numbers",
    ], cols=3)
    return d


def step2() -> Diagram:
    d = Diagram("step2-match-prep", 1300, 620, "Step 2 · Match Prep",
                "A SequentialAgent runs three agents in a fixed order. They hand over work through session state.")
    d.person(95, 250, "You", "“Prepare Sunday's game plan.”")
    d.zone(200, 90, 1075, 320, "match_prep · SequentialAgent", "seq",
           "no model of its own: runs 1 → 2 → 3, every time, in this order")
    a = agent_card(d, 225, 160, 265, 225, "opponent_analyst", "LlmAgent · studies the opponent",
                   ["get_match_info", "get_team_trends", "get_top_players", "get_availability", "get_matches"],
                   output="opponent_report")
    b = agent_card(d, 615, 160, 265, 225, "tactician", "LlmAgent · writes the game plan",
                   ["get_team_trends", "get_match_info"], output="game_plan", reads="{opponent_report}")
    c = agent_card(d, 1005, 160, 245, 225, "lineup_picker", "LlmAgent · picks the XI",
                   ["get_availability", "get_player", "get_top_players"], output="lineup", reads="{game_plan}")
    d.arrow((140, 250), a.left(90 / 225), badge=1, badge_at=(172, 250))
    d.arrow(a.right(0.45), b.left(0.45), label="opponent_report", label_at=(552, 240), badge=2, badge_at=(552, 268))
    d.arrow(b.right(0.45), c.left(0.45), label="game_plan", label_at=(942, 240), badge=3, badge_at=(942, 268))
    d.zone(200, 430, 1075, 100, "session.state", "frame", "every output_key is saved here", icon="data")
    for card, key in ((a, "opponent_report"), (b, "game_plan"), (c, "lineup")):
        x = card.x + card.w - 60
        d.arrow((x, card.y + card.h), (x, 492), kind="aux")
        d.chip(x - (text_width("→ " + key, 11.5, True) + 16) / 2, 492, key, kind="state")
    d.badge(c.x + c.w - 60, 410, 4)
    d.legend([
        "You ask once; the SequentialAgent runs all three",
        "opponent_analyst saves opponent_report (output_key)",
        "tactician reads {opponent_report}, saves game_plan",
        "lineup_picker reads {game_plan}, picks available players",
    ], cols=2, col_w=520)
    return d


def step3() -> Diagram:
    d = Diagram("step3-scouting-dept", 1310, 740, "Step 3 · Scouting Department",
                "A ParallelAgent runs three scouts at once; a report writer merges their work into one brief.")
    d.person(105, 300, "You", "“Scout Gaziantep for us.”")
    d.zone(230, 90, 1055, 540, "scouting_department · SequentialAgent", "seq", "step 1: the scouts, step 2: the writer")
    d.zone(255, 150, 1005, 280, "scouts · ParallelAgent", "par", "three scouts at the same time, each with its own output_key")
    cards = [
        agent_card(d, 275, 210, 305, 195, "attack_scout", "LlmAgent · their threats",
                   ["get_match_info", "get_top_players", "get_team_trends", "get_matches"], output="attack_report"),
        agent_card(d, 605, 210, 305, 195, "defense_scout", "LlmAgent · their weaknesses",
                   ["get_match_info", "get_team_trends", "get_availability", "get_player"], output="defense_report"),
        agent_card(d, 935, 210, 305, 195, "discipline_scout", "LlmAgent · cards and the referee",
                   ["get_match_info", "get_discipline"], output="discipline_report"),
    ]
    writer = d.card(345, 500, 830, 104, "report_writer", "LlmAgent · no tools: it only merges", top=True)
    d.text(361, 586, "reads {attack_report} {defense_report} {discipline_report}", 11.5, BLUE, mono=True, inside=writer)
    d.chip(1175 - 190, 572, "scouting_brief", kind="state")
    answer = d.card(20, 510, 200, 64, "Scouting brief", "one voice, four sections", icon="check")  # centre y=542
    d.arrow((150, 300), (255, 300), badge=1, badge_at=(200, 300))
    d.badge(240, 166, 2)
    for card, key in zip(cards, ("attack_report", "defense_report", "discipline_report")):
        x = card.x + 120
        d.arrow((x, card.y + card.h), (x, writer.y), label=key, label_at=(x + 12, 480), anchor="start")
    d.badge(cards[1].x + 120, 450, 3)
    d.arrow(writer.left(42 / 104), answer.right(), badge=4)
    d.legend([
        "You ask: one prompt starts the whole department",
        "The ParallelAgent starts all three scouts at once",
        "Each scout saves its own key; they never share mid-run",
        "report_writer reads the three keys and merges them",
    ], cols=2, col_w=560)
    return d


def step4() -> Diagram:
    d = Diagram("step4-tribun", 1240, 720, "Step 4 · Tribün",
                "A LoopAgent: the lineup picker proposes, the home crowd objects, until the crowd calls exit_loop.")
    d.person(100, 240, "You", "“Pick the XI for Sunday.”")
    d.zone(220, 90, 995, 410, "tribun_review · LoopAgent", "loop",
           "repeats lineup_picker → tribun until exit_loop, at most max_iterations=3 rounds")
    pick = agent_card(d, 250, 160, 390, 214, "lineup_picker", "LlmAgent · proposes formation + XI",
                      ["get_availability", "get_player", "get_top_players"], output="lineup",
                      reads="{tribun_feedback?}", reads_note="empty on round 1")
    crowd = agent_card(d, 795, 160, 390, 214, "tribun", "LlmAgent · the home crowd, as a critic",
                       ["get_availability", "get_player", "get_team_trends", "get_discipline"], output="tribun_feedback",
                       reads="{lineup}", extra_chips=["exit_loop"])
    approved = d.card(865, 548, 320, 66, "Approved XI", "escalate=True ends the loop", icon="check")
    d.arrow((145, 240), pick.left(80 / 214), badge=1, badge_at=(190, 240))
    d.arrow(pick.right(0.33), crowd.left(0.33), label="lineup", label_at=(750, 218), badge=2,
            badge_at=(680, pick.y + pick.h * 0.33))
    d.arrow((crowd.x + 117, crowd.y + crowd.h), (crowd.x + 117, 420), (pick.x + 195, 420), pick.bottom(0.5),
            label="tribun_feedback: the objections", label_at=(717, 442), badge=3, badge_at=(540, 420))
    d.arrow((1107, crowd.y + crowd.h), (1107, approved.y), label="exit_loop", label_at=(1123, 530), anchor="start",
            badge=4, badge_at=(1107, 452))
    d.text(266, 482, "max_iterations=3 is the safety net: the loop stops after round 3 even without approval.",
           11.5, MUTED, italic=True)
    d.badge(250, 478, 5)
    d.legend([
        "You ask once; the loop runs by itself",
        "lineup_picker proposes an XI and saves lineup",
        "tribun checks it with tools; objections loop back",
        "Happy crowd: exit_loop sets escalate=True, loop stops",
        "No approval after 3 rounds: max_iterations stops it",
    ], cols=3)
    return d


def step5() -> Diagram:
    d = Diagram("step5-technical-director", 1300, 700, "Step 5 · Technical Director",
                "An orchestrator. Each team is wrapped in AgentTool; the director picks one by its description.")
    d.person(100, 165, "You", "“Bizi pazara hazırla”")
    director = d.card(230, 100, 800, 136, "technical_director", "LlmAgent · steps/step5_technical_director/agent.py",
                      top=True)
    d.row(246, 164, 768, "reads every tool's description, makes the fewest calls, writes the briefing", highlight=True)
    d.badge(258, 215, 4)
    d.text(276, 220, "direct tools:", 11.5, MUTED, inside=director)
    d.chips(356, 204, ["get_fixtures", "get_standings", "project_table"], 600)
    gem = d.card(1060, 110, 220, 70, "gemini-3.8-flash", "chooses the tools", icon="gem")
    teams = [
        ("scout", "AgentTool(build_scout(...))", "LlmAgent · 5 tools", "“ONE player or ONE team: form,", "minutes, goals, availability.”"),
        ("match_prep", "AgentTool(build_match_prep(...))", "SequentialAgent · 3 agents", "“Game plan: opponent analysis,",
         "then tactics, then an XI.”"),
        ("scouting_department", "AgentTool(build_scouting_…)", "Sequential + Parallel · 4 agents",
         "“Full scouting report on the", "opponent: threats, cards, referee.”"),
        ("tribun_review", "AgentTool(build_tribun(...))", "LoopAgent · max 3 rounds", "“Picks a final XI and has the",
         "home crowd stress-test it.”"),
    ]
    boxes = []
    for i, (name, wrap, kind, desc1, desc2) in enumerate(teams):
        x = 230 + i * 265
        box = d.card(x, 310, 245, 170, name, wrap, top=True)
        d.text(x + 16, 384, "description=", 11.5, MUTED, mono=True, inside=box)
        d.text(x + 16, 403, desc1, 12, INK, italic=True, inside=box)
        d.text(x + 16, 420, desc2, 12, INK, italic=True, inside=box)
        d.row(x + 16, 438, 213, kind, h=26)
        boxes.append(box)
    d.arrow((145, 165), director.left(65 / 136), badge=1, badge_at=(188, 165))
    d.arrow(director.right(36 / 136), gem.left(26 / 70))
    for i, box in enumerate(boxes):
        if box.x + box.w / 2 < director.x + director.w:
            d.arrow((box.x + box.w / 2, director.y + director.h), box.top(), badge=2 if i == 1 else None,
                    badge_at=(box.x + box.w / 2, 273))
        else:
            d.arrow((1000, director.y + director.h), (1000, 270), (box.x + box.w / 2, 270), box.top())
    d.arrow(boxes[0].left(0.6), (210, 412), (210, 205), director.left(105 / 136), kind="aux", badge=3, badge_at=(210, 310))
    note = d.zone(230, 512, 1040, 74, "Two rules", "frame", icon="code")
    d.text(372, 539, "One parent per agent: build_*() returns fresh instances, so step 5 reuses the step 1–4 teams safely.",
           12.5, INK, inside=note)
    d.text(372, 562, "AgentTool returns the answer to the director (it stays in charge); sub_agents would hand the user over.",
           12.5, INK, inside=note)
    d.legend([
        "You ask the director, in any language",
        "It calls the team whose description fits (AgentTool)",
        "The team runs in its own session; its final text comes back",
        "Schedule and table questions use the direct tools",
    ], cols=2, col_w=600)
    return d


def overview() -> Diagram:
    d = Diagram("overview", 1320, 870, "Building Trabzonspor's AI Analysis Room · the whole staff",
                "The Technical Director (step 5) delegates to the teams from steps 1–4. Every box with the ADK logo is an agent.")
    d.person(100, 160, "You", "analysis staff")
    director = d.card(230, 100, 830, 110, "technical_director", "LlmAgent · step 5 · delegates through AgentTool", top=True)
    d.text(246, 186, "direct tools:", 11.5, MUTED, inside=director)
    d.chips(330, 170, ["get_fixtures", "get_standings", "project_table"], 600)
    gem = d.card(1120, 110, 185, 70, "gemini-3.8-flash", "every LlmAgent", icon="gem")
    d.arrow((145, 160), director.left(60 / 110), badge=1, badge_at=(188, 160))
    d.arrow(director.right(35 / 110), gem.left(25 / 70), badge=5, badge_at=(1088, 135))

    scout = d.card(230, 290, 200, 330, "scout", "LlmAgent · step 1", top=True)
    for i, tool in enumerate(["get_player", "get_availability", "get_team_trends", "get_top_players", "get_matches"]):
        d.row(246, 362 + i * 36, 168, tool, mono=True)

    d.zone(450, 290, 210, 330, "match_prep", "seq", "Sequential · step 2")
    for i, (agent, key) in enumerate([("opponent_analyst", "→ opponent_report"), ("tactician", "→ game_plan"),
                                      ("lineup_picker", "→ lineup")]):
        d.row(466, 352 + i * 70, 178, agent, h=44, sub=key)
        if i:
            d.arrow((555, 352 + i * 70 - 26), (555, 352 + i * 70))

    d.zone(680, 290, 270, 330, "scouting_department", "seq", "Sequential + Parallel · step 3")
    d.zone(694, 346, 242, 172, "scouts", "par", "Parallel")
    for i, agent in enumerate(["attack_scout", "defense_scout", "discipline_scout"]):
        d.row(708, 400 + i * 36, 214, agent)
    d.row(694, 548, 242, "report_writer", sub="merges the three reports", h=48)
    d.arrow((815, 518), (815, 548))

    d.zone(970, 290, 200, 330, "tribun_review", "loop", "Loop · step 4")
    d.row(986, 352, 168, "lineup_picker", h=44, sub="→ lineup")
    d.row(986, 452, 168, "tribun", h=44, sub="→ tribun_feedback")
    d.arrow((1040, 396), (1040, 452))
    d.arrow((1100, 452), (1100, 396))
    d.text(1070, 530, "exit_loop or", 11.5, MUTED, anchor="middle")
    d.text(1070, 546, "max 3 rounds", 11.5, MUTED, anchor="middle")

    for x, team in ((330, scout), (555, None), (815, None), (1040, None)):
        d.arrow((x, 210), (x, 290), badge=2 if x == 555 else None, badge_at=(555, 250))
    d.arrow((300, 290), (300, 210), kind="aux", badge=4, badge_at=(300, 250))

    tools = d.zone(230, 680, 940, 64, "matchday/tools.py", "frame",
                   "11 plain Python functions · they read data/ and do every sum, average and ranking", icon="code")
    for x in (330, 555, 815, 1070):
        d.arrow((x, 620), (x, 680), kind="aux", badge=3 if x == 815 else None, badge_at=(815, 646))
    data = d.card(1190, 680, 115, 64, "data/", "JSON", icon="data")
    d.arrow(tools.right(0.5), data.left(0.5), kind="aux")
    d.legend([
        "You ask the technical director",
        "It calls one team as a tool, chosen by description",
        "Agents call Python tools; tools read data/",
        "Each team's final answer comes back to the director",
        "Every LlmAgent calls Gemini (MODEL in config.py)",
    ], cols=3)
    return d


def bonus() -> Diagram:
    d = Diagram("bonus-live-mcp", 1240, 600, "Bonus · Live data over MCP",
                "Same build_scout() as step 1. Only the tools change: from local JSON to a live MCP server.")
    factory = d.card(410, 96, 420, 80, "build_scout(name, tools)", "steps/step1_scout/agent.py · same instruction, same model")
    d.badge(410, 96, 1)
    left = d.zone(40, 260, 540, 230, "step1_scout · scout", "frame", "tools=SCOUT_TOOLS (the default)", icon="adk")
    d.chips(60, 320, ["get_player", "get_availability", "get_team_trends", "get_top_players", "get_matches"], 500)
    snap = d.card(60, 400, 500, 66, "data/*.json", "snapshot, 30 Oct 2026 · FotMob, ESPN", icon="data")
    right = d.zone(660, 260, 540, 230, "bonus_live_mcp · live_scout", "frame",
                   "tools=[McpToolset(SseConnectionParams(url=…/sse))]", icon="adk")
    d.chips(680, 320, ["search", "get_team", "get_player", "get_match", "get_standings", "get_head_to_head"], 500, kind="mcp")
    live = d.card(680, 400, 500, 66, "livescoremcp.com/sse", "live football data · free · 30 requests/min per IP", icon="globe")
    d.arrow((560, 176), (560, 218), (310, 218), left.top(), label="default tools", label_at=(460, 210), badge=2,
            badge_at=(350, 218))
    d.arrow((680, 176), (680, 218), (930, 218), right.top(), label="tools=[live_football]", label_at=(780, 210), badge=3,
            badge_at=(890, 218))
    d.arrow((310, 370), (310, 400), kind="aux")
    d.arrow((930, 370), (930, 400), kind="aux", label="MCP over SSE", label_at=(958, 390), anchor="start", badge=4,
            badge_at=(902, 385))
    d.legend([
        "The factory from step 1: instruction and model unchanged",
        "Default: five Python tools over the JSON snapshot",
        "Bonus: one McpToolset replaces them",
        "ADK lists the server's tools over SSE; tool_filter keeps six",
    ], cols=2, col_w=600)
    return d


DIAGRAMS = [overview, step1, step2, step3, step4, step5, bonus]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for build in DIAGRAMS:
        d = build()
        (OUT / f"{d.name}.svg").write_text(d.svg(), encoding="utf-8")
        print(f"wrote guide/images/{d.name}.svg")


if __name__ == "__main__":
    main()
