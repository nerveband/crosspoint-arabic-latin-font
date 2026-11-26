# BookAmiri: Arabic + English in one font for CrossPoint e-readers

A `.cpfont` family for [CrossPoint](https://github.com/crosspoint-reader/crosspoint-reader) (the open-source firmware for
Xteink e-readers) that draws **English with full transliteration marks and fully vowelled Arabic in the same book, with no black
boxes**. Tested on an Xteink X3 running CrossPoint 2.0.0.

![An Arabic line on a real X3 (top), the old font in an emulator (middle), this font (bottom)](docs/arabic-line-18pt.png)

*Top: a real X3 screenshot (1-bit capture, so edges are harder than on the screen). Middle: the same line with the first version
of the font in an emulator that matches the capture. Bottom: this font. The marks now sit on their letters.*

## The problem

CrossPoint uses **one reader font for the whole book** and ignores fonts embedded in an EPUB. Any character the selected font
lacks is drawn as U+FFFD, a black diamond with a question mark. With a Latin font such as Gentium Book Plus, every Arabic letter
becomes one; with Amiri, English is fine but a few Latin letters are missing. On a device without extra RAM (X3, X4) only
`.cpfont` files can be loaded, so a TTF is no help.

## What this is

`BookAmiri` = the Latin, Greek, Cyrillic and IPA glyphs of **Gentium Book Plus** (all of ā ī ū ḥ ṣ ḍ ṭ ẓ ʿ ʾ and the other
transliteration letters) + everything Arabic from **Amiri** (letters, the contextual forms CrossPoint's shaper produces, ornate
brackets ﴾﴿, the ﷺ ligature). Sizes **12, 14, 16, 18, 20, 22, 24, 26** pt (CrossPoint's sizes stop at 18; points are at 150 dpi,
so 18 is 37.5 px; on the X3's 257 ppi panel 18 is about 10.5 pt of print and 24 about 14 pt).

Coverage, computed per book after running the Arabic through CrossPoint's own bidi and shaping code (characters with no glyph
are what the firmware shows as black boxes):

| book | built-in Noto Sans | Gentium Book Plus | Amiri | **BookAmiri** |
|---|---|---|---|---|
| *Purification of the Soul* (Ibn Qudamah, vowelled Arabic) | 16,877 | 14,705 | 0 | **0** |
| *Sea Without Shore* (Keller) | 1,659 | 1,610 | 0 | **0** |

## Install

1. Download `BookAmiri-fonts.zip` from the [latest release](../../releases/latest).
2. Copy the `BookAmiri` folder to the SD card as `/.fonts/BookAmiri/` (or `/fonts/BookAmiri/`; keep it in one place only).
3. Restart the reader. Settings, Reader, Reader Font Family: **BookAmiri**, then Reader Font Size.

## Stacked and floating Arabic marks

CrossPoint draws each mark centred on its letter and lifts it only until it clears that letter. That causes two visible faults,
both worked around in the font without touching the firmware:

1. **Two marks over one letter** (shadda + fatha, fatha + superscript alef, ...) land on top of each other. The font carries
   ready-made stacks, rendered from Amiri with HarfBuzz (so Amiri's own stacked-mark shapes and spacing are kept), under 13
   spare Arabic mark code points. A book has to write that code instead of the sequence: `tools/convert_book.py` does it.
2. **Marks hover over short letters** (beh, noon, yah) because Amiri's mark glyphs are drawn tall and CrossPoint leaves a mark
   where its glyph already is. Every harakat bitmap now has its bottom edge 1 px above the baseline plus a couple of blank
   rows, so the firmware's lift always applies and each mark rides just above its own letter.

![Stacked marks: unconverted text, converted text, Chrome with real OpenType shaping](docs/stacked-marks-24pt.png)

*Top: shadda + fatha as two marks. Middle: as one composite mark. Bottom: Chrome with OpenType shaping, for reference.*

The font works for any book without conversion (you only miss fix 1). To get fix 1, and to replace characters that no font has
(a few symbols and emoji), convert the EPUB:

    python tools/convert_book.py book.epub book-bookamiri.epub

It also removes embedded fonts (CrossPoint ignores them). Converted books need BookAmiri: with another font the stack marks
are simply not drawn. The 13-stack registry (`tools/marks_registry.json`) was derived from three vowelled Arabic/English books;
`tools/make_registry.py` rebuilds it from yours (then rebuild the fonts).

## Limits

- Tested on one device (Xteink X3, CrossPoint 2.0.0), a handful of books, and one real screenshot. The lowered-mark placement
  (fix 2) was tuned in an emulator that matched that screenshot; please report how it looks on your screen.
- Marks are centred over the letter's bitmap, not placed at Amiri's per-letter anchor points, so on wide letters (س ش ص) a mark
  can sit slightly off. Marks below the letter (kasra) are unchanged, and kasra can still collide with deep descenders
  ([CrossPoint #3328](https://github.com/crosspoint-reader/crosspoint-reader/issues/3328)).
- Rare mark combinations beyond the 13 stacks keep CrossPoint's default placement.
- Larger sizes use more RAM on the ESP32-C3. If 24 or 26 makes the reader fail, delete that one file.
- A font change in CrossPoint cannot be per book: it is one global setting.

## Rebuild

    pip install -r requirements.txt
    tools/get_sources.sh                                   # CrossPoint 2.0.0 converter + patch, Gentium Book Plus, Amiri 1.003
    python tools/build_font.py 12 14 16 18 20 22 24 26     # -> out/BookAmiri/

I reproduced every released file byte for byte from a clean checkout with these steps (rasterisation depends on the FreeType version, so another machine may differ in unimportant bytes). `tools/fontconvert_sdcard.x3.patch` adds a
hook for synthetic glyphs to CrossPoint's `fontconvert_sdcard.py` (tag 2.0.0).

## How it was found

A real X3 screenshot over USB (`CMD:SCREENSHOT` on the serial port) was compared with an emulation of CrossPoint's drawing code
(read from the 2.0.0 sources): `GfxRenderer::drawText` places marks relative to the base glyph only, `EpdFont::getGlyph` falls
back to U+FFFD, and the bidi table decides which code points count as marks. The marks fix would be a few lines in the firmware
(a mark should raise `lastBaseTop` so the next one clears it); doing it in the font needs no flashing.

## Licenses

- **The fonts** are Modified Versions of Gentium Book Plus (copyright 2003-2022 SIL International, Reserved Font Names "Gentium"
  and "SIL") and Amiri (copyright 2010-2022 The Amiri Project Authors), converted to CrossPoint's bitmap format, subset, combined
  and with added mark glyphs. Both are under the **SIL Open Font License 1.1**, so this font is too
  ([licenses/](licenses/)). It is named BookAmiri because the OFL forbids a Modified Version from using the Reserved Font Names.
- **The tools** are MIT ([LICENSE](LICENSE)). `tools/fontconvert_sdcard.x3.patch` modifies a file from CrossPoint Reader
  (MIT, Copyright (c) 2025 CrossPoint Reader organization, [licenses/MIT-CrossPoint-Reader.txt](licenses/MIT-CrossPoint-Reader.txt)).

Not affiliated with CrossPoint, Xteink, SIL International or the Amiri project.
