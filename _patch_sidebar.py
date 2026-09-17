"""
Three fixes in templates/dashboards/base.html and static CSS:
1. Move sidebar close button inside brand row (opposite logo) for all 3 roles
2. Remove old standalone close button
"""
import pathlib

p = pathlib.Path("templates/dashboards/base.html")
t = p.read_text(encoding="utf-8")

CLOSE_BTN = ('<button class="dashboard-sidebar-close" id="dashboardSidebarClose" '
             'type="button" aria-label="Close dashboard menu">'
             '<svg class="sic" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="1.9" stroke-linecap="round">'
             '<path d="M6 6l12 12M18 6 6 18"/></svg></button>')

# ── SELLER: close button inside sside__brandrow ────────────────────────────
# Remove standalone button before sside__brandcard
OLD_SELLER = CLOSE_BTN + "\n      <div class=\"sside__brandcard\">"
NEW_SELLER = "<div class=\"sside__brandcard\">"
assert OLD_SELLER in t, "seller close btn location not found"
t = t.replace(OLD_SELLER, NEW_SELLER, 1)

# Inject close btn at end of sside__brandrow (before its closing </div>)
OLD_BRANDROW_END = ('<span class="sside__live"><i></i>Live</span>\n        </div>')
NEW_BRANDROW_END  = ('<span class="sside__live"><i></i>Live</span>\n'
                    '          <button class="sside__close-btn" id="dashboardSidebarClose" '
                    'type="button" aria-label="Close sidebar">'
                    '<svg class="sic" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                    'stroke-width="2" stroke-linecap="round">'
                    '<path d="M6 6l12 12M18 6 6 18"/></svg></button>\n        </div>')
if OLD_BRANDROW_END in t:
    t = t.replace(OLD_BRANDROW_END, NEW_BRANDROW_END, 1)
    print("OK: seller close btn moved inside brandrow")
else:
    print("WARN: seller brandrow end not found — trying fallback")

# ── ADMIN: close button inside dashboard-brand row ────────────────────────
OLD_ADMIN = CLOSE_BTN + "\n      <a class=\"dashboard-brand\""
NEW_ADMIN = "<a class=\"dashboard-brand\""
assert OLD_ADMIN in t, "admin close btn location not found"
t = t.replace(OLD_ADMIN, NEW_ADMIN, 1)

# Admin brand row: inject close btn after the brand text
OLD_ADMIN_BRAND = ('<span><b>DropHub</b><small>ADMIN CONSOLE</small></span>\n      </a>')
NEW_ADMIN_BRAND  = ('<span><b>DropHub</b><small>ADMIN CONSOLE</small></span>\n'
                   '        <button class="admin-close-btn" id="dashboardSidebarClose" '
                   'type="button" aria-label="Close sidebar" style="margin-left:auto">'
                   '<svg class="sic" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                   'stroke-width="2" stroke-linecap="round">'
                   '<path d="M6 6l12 12M18 6 6 18"/></svg></button>\n      </a>')
if OLD_ADMIN_BRAND in t:
    t = t.replace(OLD_ADMIN_BRAND, NEW_ADMIN_BRAND, 1)
    print("OK: admin close btn moved inside brand")
else:
    print("WARN: admin brand end not found")

# ── BUYER: close button inside bside__brand row ───────────────────────────
OLD_BUYER = CLOSE_BTN + "\n      <a class=\"bside__brand\""
NEW_BUYER = "<a class=\"bside__brand\""
assert OLD_BUYER in t, "buyer close btn location not found"
t = t.replace(OLD_BUYER, NEW_BUYER, 1)

# Buyer brand row has: logo + brandtext + pill — inject close after pill
OLD_BUYER_BRAND = ('<span class="bside__pill"><i></i>Member</span>\n      </a>')
NEW_BUYER_BRAND  = ('<span class="bside__pill"><i></i>Member</span>\n'
                   '        <button class="bside__close-btn" id="dashboardSidebarClose" '
                   'type="button" aria-label="Close sidebar">'
                   '<svg class="sic" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                   'stroke-width="2" stroke-linecap="round">'
                   '<path d="M6 6l12 12M18 6 6 18"/></svg></button>\n      </a>')
if OLD_BUYER_BRAND in t:
    t = t.replace(OLD_BUYER_BRAND, NEW_BUYER_BRAND, 1)
    print("OK: buyer close btn moved inside brand")
else:
    print("WARN: buyer brand end not found")

p.write_text(t, encoding="utf-8")
print("\nbase.html patched. Length:", len(t))
