"""TEMP: use Playwright (already in venv) to measure the buyers-grid layout."""

import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011/"
VW, VH = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1440, 900)

with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    page = browser.new_page(viewport={"width": VW, "height": VH})
    page.goto(URL, wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(1200)
    data = page.evaluate(
        """() => {
          const q = s => document.querySelector(s);
          const sec = q('.buyers-section'), hdr = q('.buyers-header'), grid = q('.buyers-grid');
          const nav = q('.navbar');
          const cs = (el, p) => getComputedStyle(el)[p];
          const r = el => { if (!el) return null; const b = el.getBoundingClientRect(); return {h: Math.round(b.height), w: Math.round(b.width), top: Math.round(b.top)}; };
          const inner = (card) => {
            if (!card) return null;
            const out = {};
            const m = card.querySelector('.b-media'); if (m) out.mediaH = Math.round(m.getBoundingClientRect().height);
            const o = card.querySelector(':scope > .b-overlay, .b-media > .b-overlay'); if (o) out.overlayH = Math.round(o.getBoundingClientRect().height);
            const i = card.querySelector(':scope > .b-info'); if (i) out.infoH = Math.round(i.getBoundingClientRect().height);
            return out;
          };
          const cards = Array.from(document.querySelectorAll('.buyers-grid > .b-card'));
          return {
            vh: window.innerHeight, vw: window.innerWidth,
            nav: r(nav), section: r(sec), header: r(hdr), grid: r(grid),
            secPadT: sec ? cs(sec,'paddingTop') : null, secPadB: sec ? cs(sec,'paddingBottom') : null,
            cards: cards.map(el => {
              const b = el.getBoundingClientRect();
              return {cls: el.className.replace(/ reveal.*/,''), h: Math.round(b.height),
                      parts: inner(el),
                      badge: ((el.querySelector('.b-badge') || {}).textContent || '').trim()};
            }),
          };
        }"""
    )
    browser.close()

print("viewport %sx%s" % (data["vw"], data["vh"]))
print("tall computed:", data["tallCS"])
print("tall kids:", data["tallKids"])
print("media/overlay:", data["media"], data["overlay"])
print("section:", data["section"])
print("header:", data["header"])
print("grid:", data["grid"])
for i, c in enumerate(data["cards"], 1):
    print("card%d h=%s w=%s top=%s bot=%s imgH=%s badge=%r cls=%s"
          % (i, c["h"], c["w"], c["top"], c["bot"], c["imgH"], c["badge"].strip(), c["cls"]))
print("grid bottom below section top by:", data["grid"]["top"] + data["grid"]["h"] - data["section"]["top"])
in_view = [c for c in data["cards"] if c["top"] is not None and c["top"] < data["vh"]]
print("cards whose top edge is inside viewport:", len(in_view), "of", len(data["cards"]))
