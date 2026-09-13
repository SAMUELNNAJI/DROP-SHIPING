# -*- coding: utf-8 -*-
"""Remove duplicate inline Cart Dropdown Toggle IIFEs (handled by cart.js)."""
import io, re, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

block_re = re.compile(
    r"[ \t]*// Cart Dropdown Toggle[ \t]*\r?\n"
    r"[ \t]*\(function \(\) \{[ \t]*\r?\n"
    r".*?"
    r"[ \t]*\}\)\(\);[ \t]*\r?\n"
    r"\r?\n"
    r"(?=[ \t]*// Navbar Scroll state)",
    re.S,
)

for fname in ("blog.html", "contact.html"):
    with io.open(fname, "r", encoding="utf-8", newline="") as fh:
        txt = fh.read()
    new, n = block_re.subn("", txt)
    if n:
        with io.open(fname, "w", encoding="utf-8", newline="") as fh:
            fh.write(new)
    print(fname, "- duplicate toggle blocks removed:", n)