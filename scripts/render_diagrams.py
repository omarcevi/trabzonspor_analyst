"""Render every guide diagram in headless Chrome, save PNG previews and check the layout.

    uv run --with playwright python scripts/render_diagrams.py

Checks, per SVG: text inside the canvas and inside its card/chip/zone, no overlapping text,
no diagonal arrows, no arrow running through text or a card, no badge covering text.
Exits with 1 and lists the problems if any check fails. Previews go to scripts/diagram_previews/.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "guide" / "images"
PREVIEWS = Path(__file__).resolve().parent / "diagram_previews"

CHECK_JS = """
() => {
  const svg = document.querySelector('svg');
  const W = +svg.getAttribute('width'), H = +svg.getAttribute('height');
  const issues = [];
  const box = el => { const b = el.getBBox(); return {x: b.x, y: b.y, w: b.width, h: b.height}; };
  const hit = (a, b, pad = 0) => a.x + pad < b.x + b.w && b.x + pad < a.x + a.w && a.y + pad < b.y + b.h && b.y + pad < a.y + a.h;
  const texts = [...svg.querySelectorAll('text')].filter(t => !t.closest('.badge') && t.textContent.trim());
  const tb = texts.map(t => ({t: t.textContent, b: box(t), inside: t.getAttribute('data-in')}));
  for (const {t, b, inside} of tb) {
    if (b.x < 2 || b.y < 2 || b.x + b.w > W - 2 || b.y + b.h > H - 2) issues.push(`off canvas: "${t}"`);
    if (inside) {
      const [x, y, w, h] = inside.split(',').map(Number);
      if (b.x < x + 2 || b.x + b.w > x + w - 2 || b.y < y || b.y + b.h > y + h) issues.push(`clipped by its box: "${t}"`);
    }
  }
  for (let i = 0; i < tb.length; i++)
    for (let j = i + 1; j < tb.length; j++)
      if (hit(tb[i].b, tb[j].b, 1)) issues.push(`text overlap: "${tb[i].t}" / "${tb[j].t}"`);
  const cards = [...svg.querySelectorAll('rect.card')].map(box);
  for (const p of svg.querySelectorAll('path.arrow')) {
    const pts = p.getAttribute('d').slice(1).split(' L').map(s => s.trim().split(/\\s+/).map(Number));
    for (let k = 0; k + 1 < pts.length; k++) {
      const [x1, y1] = pts[k], [x2, y2] = pts[k + 1];
      if (x1 !== x2 && y1 !== y2) issues.push(`diagonal arrow segment ${x1},${y1} -> ${x2},${y2}`);
      const seg = {x: Math.min(x1, x2) - 0.8, y: Math.min(y1, y2) - 0.8, w: Math.abs(x2 - x1) + 1.6, h: Math.abs(y2 - y1) + 1.6};
      for (const {t, b} of tb) if (hit(seg, b, 0.5)) issues.push(`arrow through text: "${t}"`);
      for (const c of cards) if (hit(seg, {x: c.x + 3, y: c.y + 3, w: c.w - 6, h: c.h - 6})) issues.push(`arrow through a card at ${c.x},${c.y}`);
    }
  }
  for (const g of svg.querySelectorAll('.badge')) {
    const b = box(g);
    for (const {t, b: x} of tb) if (hit(b, x, 0.5)) issues.push(`badge covers text: "${t}"`);
  }
  return [...new Set(issues)];
}
"""


def main() -> int:
    PREVIEWS.mkdir(exist_ok=True)
    failed = False
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception:
            browser = p.chromium.launch()
        for svg in sorted(IMAGES.glob("*.svg")):
            markup = svg.read_text(encoding="utf-8")
            width, height = (int(re.search(rf'{k}="(\d+)"', markup).group(1)) for k in ("width", "height"))
            # A fresh page per diagram: resizing one page in headless Chrome can tile the screenshot.
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1.5)
            page.set_content(f'<html><body style="margin:0">{markup}</body></html>')
            page.evaluate("document.fonts.ready")
            page.screenshot(path=str(PREVIEWS / f"{svg.stem}.png"))
            issues = page.evaluate(CHECK_JS)
            print(f"{svg.name}: {'ok' if not issues else f'{len(issues)} issue(s)'}")
            for issue in issues:
                print(f"   - {issue}")
            failed |= bool(issues)
            page.close()
        browser.close()
    print(f"previews in {PREVIEWS.relative_to(ROOT)}/")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
