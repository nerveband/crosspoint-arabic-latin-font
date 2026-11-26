"""Stacked and lowered Arabic marks for CrossPoint's .cpfont renderer.

CrossPoint draws every mark centred on its base letter, raising it only until it clears that letter
(combiningMark::raiseAboveBase). Consequences, both fixed here without touching the firmware:
  1. two marks above one letter (shadda + fatha, ...) land on top of each other
     -> a ready-made stack is stored as ONE mark glyph under a spare Arabic mark code point, drawn from Amiri by HarfBuzz
        (so Amiri's stacked-mark shapes and spacing are kept); books write that code instead of the sequence.
  2. a mark whose own glyph is already higher than the letter stays there and floats over short letters
     -> every harakat bitmap gets its bottom edge 1 px above the baseline plus a few blank rows, so the firmware's
        raise ALWAYS applies and each mark rides a fixed distance above its own letter.
"""
import os
import re

import freetype
import uharfbuzz as hb

HERE = os.path.dirname(os.path.abspath(__file__))
AMIRI_DIR = os.environ.get("AMIRI_DIR", os.path.join(HERE, "..", "sources", "Amiri"))
STYLE_FILE = {0: "Regular", 1: "Bold", 2: "Italic", 3: "BoldItalic"}

# marks that sit below the letter (everything else in the Arabic mark blocks is drawn above)
BELOW = {0x064D, 0x0650, 0x0655, 0x0656, 0x065F, 0x06E3, 0x06ED}
MARKS = (set(range(0x0610, 0x061B)) | set(range(0x064B, 0x0660)) | {0x0670} | set(range(0x06D6, 0x06DD))
         | set(range(0x06DF, 0x06E5)) | {0x06E7, 0x06E8} | set(range(0x06EA, 0x06EE)))
# Arabic NSM code points that CrossPoint's bidi table treats as zero-width marks and books practically never use
SPARE = [0x0615, 0x0616, 0x0617, 0x0618, 0x0619, 0x061A, 0x0658, 0x0659, 0x065A, 0x065B, 0x065C, 0x065D, 0x065F]
# marks that sit right above the letter like harakat (Qur'anic waqf signs U+06D6-06DC stay high, where Amiri puts them)
LOWER = (set(range(0x064B, 0x0660)) - BELOW) | {0x0670, 0x06DF, 0x06E1, 0x06E2, 0x06E4, 0x06E7, 0x06E8}
LOWER_ON = True

_FACES = {}


def _path(style):
    return os.path.join(AMIRI_DIR, "Amiri-%s.ttf" % STYLE_FILE[style])


def _hb(style):
    if style not in _FACES:
        face = hb.Face(hb.Blob.from_file_path(_path(style)))
        _FACES[style] = (face, hb.Font(face))
    return _FACES[style]


def split_cluster(marks):
    """marks: code points following one base letter -> (above, below)"""
    return tuple(c for c in marks if c not in BELOW), tuple(c for c in marks if c in BELOW)


def composite_bitmap(above, style, size):
    """The stack `above`, laid out like HarfBuzz+Amiri over a plain beh. 8-bit coverage dict for fontconvert."""
    face, font = _hb(style)
    upem = face.upem
    buf = hb.Buffer()
    buf.add_str("\u0628" + "".join(chr(c) for c in above))
    buf.direction, buf.script, buf.language = "rtl", "Arab", "ar"
    hb.shape(font, buf, {})
    glyphs, pen = [], 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        if pos.x_advance == 0:                       # a mark glyph (the base has an advance)
            glyphs.append((info.codepoint, pos.x_offset + pen, pos.y_offset))
        pen += pos.x_advance
    ft = freetype.Face(_path(style))
    ft.set_char_size(size << 6, size << 6, 150, 150)
    scale = size * 150 / 72 / upem                   # font units -> pixels
    tiles = []
    for gid, xo, yo in glyphs:
        ft.load_glyph(gid, freetype.FT_LOAD_RENDER)
        bm = ft.glyph.bitmap
        if bm.rows == 0 or bm.width == 0:
            continue
        pitch = abs(bm.pitch)
        px = [bm.buffer[r * pitch + c] for r in range(bm.rows) for c in range(bm.width)]
        tiles.append((bm.width, bm.rows, px, ft.glyph.bitmap_left + round(xo * scale), ft.glyph.bitmap_top + round(yo * scale)))
    if not tiles:
        return None
    x0 = min(t[3] for t in tiles); x1 = max(t[3] + t[0] for t in tiles)
    ytop = max(t[4] for t in tiles); ybot = min(t[4] - t[1] for t in tiles)
    W, H = x1 - x0, ytop - ybot
    canvas = bytearray(W * H)
    for w, h, px, left, top in tiles:
        for r in range(h):
            for c in range(w):
                v = px[r * w + c]
                if v:
                    i = (ytop - (top - r)) * W + (left - x0 + c)
                    canvas[i] = max(canvas[i], v)
    return {"width": W, "rows": H, "left": x0, "top": ytop, "buffer": bytes(canvas)}


def single_mark_bitmap(cp, style, size):
    ft = freetype.Face(_path(style))
    ft.set_char_size(size << 6, size << 6, 150, 150)
    gid = ft.get_char_index(cp)
    if gid == 0:
        return None
    ft.load_glyph(gid, freetype.FT_LOAD_RENDER)
    bm = ft.glyph.bitmap
    if bm.rows == 0 or bm.width == 0:
        return None
    pitch = abs(bm.pitch)
    buf = bytes(bm.buffer[r * pitch + c] for r in range(bm.rows) for c in range(bm.width))
    return {"width": bm.width, "rows": bm.rows, "left": ft.glyph.bitmap_left, "top": ft.glyph.bitmap_top, "buffer": buf}


def floor_pad(bm, size):
    """Bottom edge 1 px above the baseline + p blank rows under the ink: the firmware's raise always applies."""
    if bm is None:
        return None
    p = max(1, round(size * 150 / 72 * 0.05))
    w, h = bm["width"], bm["rows"]
    return {"width": w, "rows": h + p, "left": bm["left"], "top": 1 + h + p, "buffer": bm["buffer"] + bytes(p * w)}


class Registry:
    """Spare code point <-> stack of above-marks."""

    def __init__(self, stacks=None):
        self.stacks = dict(stacks or {})             # tuple of marks -> code point

    @classmethod
    def load(cls, path):
        import json
        with open(path) as f:
            return cls({tuple(int(x, 16) for x in k.split("+")): c for k, c in json.load(f).items()})

    def extra_glyphs(self):
        """callable for the patched converter: (style_id, size, code point) -> bitmap dict or None"""
        by_code = {c: s for s, c in self.stacks.items()}
        cache = {}

        def f(style_id, size, cp):
            key = (style_id, size, cp)
            if key not in cache:
                if cp in by_code:
                    cache[key] = floor_pad(composite_bitmap(by_code[cp], style_id, size), size)
                elif cp in LOWER and LOWER_ON:
                    cache[key] = floor_pad(single_mark_bitmap(cp, style_id, size), size)
                else:
                    cache[key] = None
            return cache[key]
        return f


_RUN = re.compile("[%s]{2,}" % "".join(chr(c) for c in sorted(MARKS)))


def remap_text(text, reg):
    """Replace stacked above-mark runs by their composite code point. Returns (text, replacements)."""
    n = [0]

    def sub(m):
        above, below = split_cluster(tuple(ord(c) for c in m.group(0)))
        code = reg.stacks.get(above) if len(above) >= 2 else None
        if code is None:
            return m.group(0)
        n[0] += 1
        return chr(code) + "".join(chr(c) for c in below)
    return _RUN.sub(sub, text), n[0]
