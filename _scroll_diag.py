"""Diagnose mobile scrolling on the checkout page with a real (headless) mobile browser."""
import json, sys
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8000/checkout/"

DIAG_JS = """
() => {
  const se = document.scrollingElement || document.documentElement;
  const de = document.documentElement, b = document.body;
  const cs = el => getComputedStyle(el);
  const centerHit = document.elementFromPoint(window.innerWidth/2, window.innerHeight/2);
  // walk up from hit element to find any fixed/absolute ancestor that could trap touches
  let trap = null, el = centerHit;
  while (el && el !== document.documentElement) {
    const s = cs(el);
    if (s.position === 'fixed' || s.position === 'sticky') { trap = {tag: el.tagName, cls: el.className && el.className.toString().slice(0,80), pos: s.position, pe: s.pointerEvents, z: s.zIndex, vis: s.visibility, rect: el.getBoundingClientRect().toJSON()}; break; }
    el = el.parentElement;
  }
  return {
    viewport: {w: window.innerWidth, h: window.innerHeight},
    scroll: {scrollHeight: se.scrollHeight, clientHeight: se.clientHeight, scrollY: window.scrollY},
    html: {overflowX: cs(de).overflowX, overflowY: cs(de).overflowY, height: cs(de).height},
    body: {overflowX: cs(b).overflowX, overflowY: cs(b).overflowY, height: cs(b).height, cls: b.className},
    centerHit: centerHit ? {tag: centerHit.tagName, cls: centerHit.className && centerHit.className.toString().slice(0,80)} : null,
    fixedTrap: trap,
  };
}
"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(
        viewport={"width": 390, "height": 844},
        device_scale_factor=3,
        is_mobile=True,
        has_touch=True,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    )
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append("console.error: " + m.text) if m.type == "error" else None)
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1500)

    diag = page.evaluate(DIAG_JS)
    print("=== DIAGNOSTICS ===")
    print(json.dumps(diag, indent=2))

    # Test 1: programmatic scroll
    page.evaluate("window.scrollTo(0, 600)")
    page.wait_for_timeout(300)
    y1 = page.evaluate("window.scrollY")
    print(f"\n=== window.scrollTo(0,600) -> scrollY = {y1} ===")

    # Test 2: real touch swipe
    page.touchscreen.tap(195, 400)  # ensure touch works
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(200)
    # swipe up (finger moves from 600 to 200 => scroll down)
    cdp = ctx.new_cdp_session(page)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 195, "y": 600}]})
    for y in (550, 480, 400, 320, 250, 200):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 195, "y": y}]})
        page.wait_for_timeout(16)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    page.wait_for_timeout(800)
    y2 = page.evaluate("window.scrollY")
    print(f"=== touch swipe up -> scrollY = {y2} ===")

    print(f"\n=== JS/console errors: {errors if errors else 'none'} ===")
    page.screenshot(path="_mobile_checkout.png")
    browser.close()
