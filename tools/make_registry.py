#!/usr/bin/env python3
"""Choose which mark stacks get a composite glyph, from the books you read.

    python tools/make_registry.py BOOK.epub [BOOK.epub ...]     # rewrites tools/marks_registry.json

The registry has 13 slots (the spare mark code points). The most frequent stacks of above-marks (two or more marks over one
letter) in the given books get one each; rarer stacks keep CrossPoint's default placement. The shipped registry was derived
from three fully vowelled Arabic/English books. Rebuild the fonts and re-run convert_book.py after changing it."""
import collections
import json
import os
import re
import sys
import zipfile

from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arabic_marks as M


def book_text(path):
    z = zipfile.ZipFile(path)
    out = []
    for n in sorted(z.namelist()):
        if n.endswith((".xhtml", ".html", ".htm")):
            x = etree.fromstring(z.read(n), etree.XMLParser(recover=True, resolve_entities=False))
            out.append("".join(x.itertext()))
    return "\n".join(out)


cnt, used = collections.Counter(), collections.Counter()
for b in sys.argv[1:]:
    t = book_text(b)
    for c in M.SPARE:
        used[c] += t.count(chr(c))
    for m in M._RUN.finditer(t):
        above, _ = M.split_cluster(tuple(ord(c) for c in m.group(0)))
        if len(above) >= 2:
            cnt[above] += 1
if not cnt:
    sys.exit("no stacked marks found")
free = [c for c in M.SPARE if not used[c]]
top = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:len(free)]
reg = {"+".join("%04X" % x for x in s): c for (s, n), c in zip(top, free)}
print("covered %d of %d stacked clusters (%d distinct stacks); spare codes already used by the books: %s" % (
    sum(n for s, n in top), sum(cnt.values()), len(cnt), {hex(k): v for k, v in used.items() if v} or "none"))
json.dump(reg, open(os.path.join(HERE, "marks_registry.json"), "w"), indent=1)
