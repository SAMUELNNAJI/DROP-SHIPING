"""TEMP: use Playwright to measure and screenshot the buyers-grid layout."""

import sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011/"
VW, VH = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1440, 900)

with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    page = browser.new_page(viewport={"width": VW, "height": VH})
    page.goto(URL, wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(1000)
    
    # Scroll buyers section into view
    page.evaluate("document.querySelector('.buyers-section').scrollIntoView()")
    page.wait_for_timeout(500)
    page.screenshot(path="buyers_section_current.png")

    data = page.evaluate(
        """() => {
          const q = s => document.querySelector(s);
          const sec = q('.buyers-section'), hdr = q('.buyers-header'), grid = q('.buyers-grid');
          const cs = (el, p) => el ? getComputedStyle(el)[p] : null;
          const r = el => { if (!el) return null; const b = el.getBoundingClientRect(); return {h: Math.round(b.height), w: Math.round(b.width), top: Math.round(b.top), bottom: Math.round(b.bottom)}; };
          const cards = Array.from(document.querySelectorAll('.buyers-grid > .b-card'));
          return {
            vh: window.innerHeight, vw: window.innerWidth,
            section: r(sec), header: r(hdr), grid: r(grid),
            secPadT: cs(sec,'paddingTop'), secPadB: cs(sec,'paddingBottom'),
            cards: cards.map(el => {
              const b = el.getBoundingClientRect();
              const m = el.querySelector('.b-media');
              const o = el.querySelector(':scope > .b-overlay, .b-media > .b-overlay');
              const info = el.querySelector(':scope > .b-info');
              return {
                cls: el.className.replace(/ reveal.*/,''),
                h: Math.round(b.height),
                w: Math.round(b.width),
                top: Math.round(b.top),
                bottom: Math.round(b.bottom),
                mediaH: m ? Math.round(m.getBoundingClientRect().height) : null,
                infoH: info ? Math.round(info.getBoundingClientRect().height) : null,
                badge: ((el.querySelector('.b-badge') || {}).textContent || '').trim()
              };
            }),
          };
        }"""
    )
    browser.close()

print(f"viewport: {data['vw']}x{data['vh']}")
print(f"section: {data['section']}, padT: {data['secPadT']}, padB: {data['secPadB']}")
print(f"header: {data['header']}")
print(f"grid: {data['grid']}")
for i, c in enumerate(data['cards'], 1):
    print(f"card {i}: h={c['h']} top={c['top']} bot={c['bottom']} mediaH={c['mediaH']} infoH={c['infoH']} cls={c['cls']} badge={c['badge']}")
