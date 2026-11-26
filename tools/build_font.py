#!/usr/bin/env python3
"""Build the BookAmiri .cpfont family: Gentium Book Plus (Latin, Greek, Cyrillic, IPA) + Amiri (Arabic, presentation forms,
U+FDFA ligature) with composite/lowered Arabic marks (see arabic_marks.py).

    tools/get_sources.sh                  # once
    python tools/build_font.py 12 14 16 18 20 22 24 26      # -> out/BookAmiri/BookAmiri_<size>.cpfont

Sizes are points at 150 dpi (CrossPoint's convention): 18 = 37.5 px em."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "sources", "converter"))
import fontconvert_sdcard as F      # CrossPoint 2.0.0 converter + tools/fontconvert_sdcard.x3.patch
import arabic_marks as M

FAMILY = "BookAmiri"
LATIN = os.path.join(ROOT, "sources", "GentiumBookPlus", "GentiumBookPlus-%s.ttf")
ARABIC = os.path.join(ROOT, "sources", "Amiri", "Amiri-%s.ttf")
INTERVALS = "arabic,latin-ext,greek,cyrillic,ipa-chars,punctuation,symbols,reading,(0xFDFA-0xFDFB),(0x0300-0x036F)"
STYLES = {0: "Regular", 1: "Bold", 2: "Italic", 3: "BoldItalic"}


def main(sizes):
    F.EXTRA_GLYPHS = M.Registry.load(os.path.join(HERE, "marks_registry.json")).extra_glyphs()
    intervals = F.resolve_intervals(INTERVALS)
    out = os.path.join(ROOT, "out", FAMILY)
    os.makedirs(out, exist_ok=True)
    for size in sizes:
        F.generate_cpfont_multistyle(
            {s: LATIN % n for s, n in STYLES.items()}, size, intervals,
            os.path.join(out, "%s_%d.cpfont" % (FAMILY, size)),
            fallback_style_fonts={s: ARABIC % n for s, n in STYLES.items()})


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main([int(a) for a in sys.argv[1:]])
