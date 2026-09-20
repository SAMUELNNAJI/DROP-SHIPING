"""TEMP: final verification - PDP styles + cart dropdown + mobile hamburger."""
from playwright.sync_api import sync_playwright

errors = []

with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.on("console", lambda m: errors.append(f"[console] {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))
    page.on("response", lambda r: errors.append(f"[http {r.status}] {r.url}") if r.status >= 400 else None)
    page.goto("http://127.0.0.1:8012/products/15/", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(600)

    style = page.evaluate(
        """() => { const q = s => document.querySelector(s); const cs = (e,p) => e ? getComputedStyle(e)[p] : null;
          return { gridCols: cs(q('.pdp-grid'),'gridTemplateColumns'),
                   stageRadius: cs(q('.pdp-gallery__stage'),'borderRadius'),
                   addBtnBg: cs(q('.pdp-add-btn'),'backgroundColor') }; }""")
    print("PDP styles:", style)

    page.click("#cartToggle")
    page.wait_for_timeout(600)
    cart = page.evaluate(
        """() => { const dd = document.getElementById('cartDropdown');
          const r = dd.getBoundingClientRect(); const cs = getComputedStyle(dd);
          const hit = document.elementFromPoint(r.x + r.width/2, r.y + 20);
          return { vis: cs.visibility, op: cs.opacity,
                   rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
                   hit: hit ? (hit.className || hit.tagName) : 'none' }; }""")
    print("cart dropdown open:", cart)
    page.screenshot(path="final_cart_open.png")

    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(400)
    page.click("#navBurger")
    page.wait_for_timeout(700)
    menu = page.evaluate(
        """() => { const m = document.getElementById('mobileMenu'); const cs = getComputedStyle(m);
          return { mmenuOpen: m.classList.contains('mmenu--open'), vis: cs.visibility,
                   pe: cs.pointerEvents, locked: document.body.classList.contains('mmenu-locked') }; }""")
    print("mobile menu open:", menu)
    page.screenshot(path="final_mobile_menu.png")
    browser.close()

print("errors:", errors if errors else "(none)")
