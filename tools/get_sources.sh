#!/bin/bash
# Downloads what the build needs into ./sources and applies the patch to CrossPoint's font converter.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p sources/converter sources/Amiri sources/GentiumBookPlus
CP_TAG=2.0.0
RAW=https://raw.githubusercontent.com/crosspoint-reader/crosspoint-reader/$CP_TAG/lib/EpdFont/scripts
curl -fsSL -o sources/converter/fontconvert_sdcard.py $RAW/fontconvert_sdcard.py
curl -fsSL -o sources/converter/cpfont_version.py     $RAW/cpfont_version.py
( cd sources/converter && patch -p4 < ../../tools/fontconvert_sdcard.x3.patch )
for s in Regular Bold Italic BoldItalic; do
  curl -fsSL -o sources/GentiumBookPlus/GentiumBookPlus-$s.ttf \
    https://raw.githubusercontent.com/google/fonts/main/ofl/gentiumbookplus/GentiumBookPlus-$s.ttf
done
curl -fsSL -o sources/amiri.zip https://github.com/aliftype/amiri/releases/download/1.003/Amiri-1.003.zip
unzip -q -o -j sources/amiri.zip 'Amiri-1.003/Amiri-*.ttf' -d sources/Amiri
rm sources/amiri.zip
echo "sources ready"
