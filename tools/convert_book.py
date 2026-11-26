#!/usr/bin/env python3
"""Make an EPUB drawable with the BookAmiri font (no black boxes, stacked Arabic marks separated).

    python tools/convert_book.py IN.epub OUT.epub [--keep-fonts]

  1. embedded fonts / @font-face removed (CrossPoint ignores them)
  2. stacked above-marks (shadda+fatha, ...) written as one composite mark code (tools/marks_registry.json)
  3. characters BookAmiri has no glyph for are replaced by plain equivalents (SUBST below); text nodes only,
     tags and attributes are never touched. Everything else in the zip is copied unchanged.
Add your own pairs to SUBST: a character with no glyph is drawn by CrossPoint as a black diamond with a question mark."""
import collections
import html.entities
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arabic_marks as M

SUBST = {
    "\u273a": "*",                     # sixteen pointed asterisk
    "\u2752": "[ ]",                   # shadowed white square (check box)
    "\u2229": "AND", "\u222a": "OR",   # Venn intersection / union
    "\u9b06": "[character]",           # a lone CJK character
    "\u2666": "*",                     # black diamond suit
    "\U0001F7EA": "", "\U0001F4C5": "", "\U0001F381": "",   # emoji
}
TEXT_MEMBERS = (".xhtml", ".html", ".htm", ".ncx", ".opf", ".xml")
ENT = re.compile(r"&(#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")
WANTED = set(SUBST) | set(chr(c) for c in M.MARKS)


def _entity(m):
    s = m.group(1)
    try:
        if s[0] == "#":
            c = chr(int(s[2:], 16) if s[1] in "xX" else int(s[1:]))
        else:
            cp = html.entities.name2codepoint.get(s)
            c = chr(cp) if cp else None
    except (ValueError, OverflowError):
        c = None
    return c if c in WANTED else m.group(0)


def convert_text_nodes(data, reg, stats):
    parts = re.split(r"(<[^>]*>)", data)
    for i, p in enumerate(parts):
        if p.startswith("<") or not p:
            continue
        p = ENT.sub(_entity, p)
        p, n = M.remap_text(p, reg)
        stats["stacks"] += n
        for ch, rep in SUBST.items():
            if ch in p:
                stats["subst"][ch] += p.count(ch)
                p = p.replace(ch, rep)
        parts[i] = p
    return "".join(parts)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    reg = M.Registry.load(os.path.join(HERE, "marks_registry.json"))
    stats = {"stacks": 0, "subst": collections.Counter()}
    zin = zipfile.ZipFile(src)
    font_files = set() if "--keep-fonts" in sys.argv else \
        {n for n in zin.namelist() if re.search(r"\.(ttf|otf|woff2?)$", n, re.I)}
    with zipfile.ZipFile(dst, "w") as zout:
        for info in zin.infolist():
            n = info.filename
            if n in font_files:
                continue
            data = zin.read(n)
            low = n.lower()
            if low.endswith(TEXT_MEMBERS):
                txt = data.decode("utf-8")
                if low.endswith(".opf") and font_files:
                    for f in font_files:
                        txt = re.sub(r'\s*<item\b[^>]*href="[^"]*%s"[^>]*/>' % re.escape(os.path.basename(f)), "", txt)
                data = convert_text_nodes(txt, reg, stats).encode("utf-8")
            elif low.endswith(".css") and font_files:
                data = re.sub(r"@font-face\s*\{[^}]*\}\s*", "", data.decode("utf-8")).encode("utf-8")
            zi = zipfile.ZipInfo(n, info.date_time)
            zi.compress_type = zipfile.ZIP_STORED if n == "mimetype" else zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr
            zout.writestr(zi, data)
    print("%s: stacked-mark runs remapped %d, substitutions %s, embedded fonts removed %d" % (
        os.path.basename(dst), stats["stacks"], dict(stats["subst"]), len(font_files)))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main()
