#!/usr/bin/env bash
# Linux-AppImage bauen: ConnectFour_Studio_Qt-x86_64.AppImage
#
# Basis: python-appimage (manylinux_2_28, eigenes CPython 3.14), darin
# PySide6-Essentials + Pillow + BitBully per pip; danach ausgeduennt
# (prune_appdir.py), geprueft (verify_appdir.py) und mit appimagetool
# verpackt. Downloads landen in build/cache (einmalig).
#
# Aufruf (im Projektordner):  packaging/linux/build_appimage.sh
# Voraussetzungen: curl, readelf (binutils), gcc/make/pkg-config + xcb-Header
# (nur fuer den libxcb-cursor-Fallback), Internetzugang beim ersten Lauf.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HERE="$ROOT/packaging/linux"
BUILD="$ROOT/build/appimage"
CACHE="$ROOT/build/cache"
APPDIR="$BUILD/AppDir"
OUT="$ROOT/ConnectFour_Studio_Qt-x86_64.AppImage"

PY_URL="https://github.com/niess/python-appimage/releases/download/python3.14/python3.14.8-cp314-cp314-manylinux_2_28_x86_64.AppImage"
TOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
RUNTIME_URL="https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64"
XCBC_URL="https://xorg.freedesktop.org/archive/individual/lib/xcb-util-cursor-0.1.6.tar.xz"
# xcb-Hilfsbibliotheken, die Qts xcb-Plugin braucht und die nicht ueberall
# installiert sind (alle glibc <= 2.28-kompatibel; cursor wird selbst gebaut).
XCB_HOST_LIBS="libxcb-icccm.so.4 libxcb-image.so.0 libxcb-keysyms.so.1 libxcb-render-util.so.0 libxcb-util.so.1"

export APPIMAGE_EXTRACT_AND_RUN=1   # Werkzeug-AppImages ohne FUSE starten

fetch() {  # fetch URL ZIEL
    if [ ! -s "$2" ]; then
        echo ">> Download $(basename "$2")"
        curl -fsSL --retry 3 -o "$2.part" "$1"
        mv "$2.part" "$2"
    fi
}

mkdir -p "$CACHE"
fetch "$PY_URL" "$CACHE/python.AppImage"
fetch "$TOOL_URL" "$CACHE/appimagetool.AppImage"
fetch "$RUNTIME_URL" "$CACHE/runtime-x86_64"
fetch "$XCBC_URL" "$CACHE/xcb-util-cursor.tar.xz"
chmod +x "$CACHE/python.AppImage" "$CACHE/appimagetool.AppImage"

echo ">> AppDir aus der Python-Basis"
rm -rf "$BUILD"
mkdir -p "$BUILD"
( cd "$BUILD" && "$CACHE/python.AppImage" --appimage-extract >/dev/null )
mv "$BUILD/squashfs-root" "$APPDIR"
PY="$APPDIR/opt/python3.14/bin/python3.14"

echo ">> Abhaengigkeiten (pip, nur Binaer-Wheels)"
"$PY" -s -m pip install --no-cache-dir --only-binary=:all: --disable-pip-version-check \
    -r "$ROOT/requirements.txt" >/dev/null

echo ">> Ausduennen"
python3 "$HERE/prune_appdir.py" "$APPDIR"

echo ">> libxcb-cursor (glibc-2.28-kompatibel) + xcb-Fallback-Bibliotheken"
FB="$APPDIR/usr/lib/xcb-fallback"
mkdir -p "$FB"
# Direkt uebersetzt (ohne autotools/xorg-macros); -std=gnu99 vermeidet die
# C23-Umleitung strtol -> __isoc23_strtol (GLIBC_2.38), der Shim sichert ab.
XB="$(mktemp -d /tmp/cfs-xcb-cursor.XXXXXX)"
trap 'rm -rf "$XB"' EXIT
tar -xf "$CACHE/xcb-util-cursor.tar.xz" -C "$XB" --strip-components=1
gcc -O2 -fPIC -std=gnu99 -shared -DHAVE_ENDIAN_H -I"$XB/cursor" \
    -DXCURSORPATH='"~/.local/share/icons:~/.icons:/usr/share/icons:/usr/share/pixmaps"' \
    "$XB"/cursor/cursor.c "$XB"/cursor/load_cursor.c "$XB"/cursor/parse_cursor_file.c \
    "$XB"/cursor/shape_to_id.c "$HERE/xcb_cursor_compat.c" \
    $(pkg-config --cflags --libs xcb xcb-render xcb-renderutil xcb-image) \
    -Wl,-soname,libxcb-cursor.so.0 -o "$FB/libxcb-cursor.so.0"
strip --strip-unneeded "$FB/libxcb-cursor.so.0"
for lib in $XCB_HOST_LIBS; do
    src="$(ldconfig -p | awk -v n="$lib" '$1==n && /x86-64/ {f=$NF} END {print f}')"
    if [ -n "$src" ]; then cp -L "$src" "$FB/"; else echo "!! $lib nicht gefunden"; exit 1; fi
done
# Kontrolle: keine Symbole neuer als GLIBC_2.28
for f in "$FB"/*.so.*; do
    v=$(objdump -T "$f" | grep -o 'GLIBC_[0-9.]*' | sort -V | tail -1)
    case "$v" in GLIBC_2.2[0-8]|GLIBC_2.1*|GLIBC_2.[0-9]|GLIBC_2.[0-9].*|"") ;; \
        *) echo "!! $f braucht $v"; exit 1 ;; esac
done

echo ">> Programm"
APP="$APPDIR/opt/connectfour-studio-qt"
mkdir -p "$APP"
cp "$ROOT/connectfour_studio_qt.py" "$ROOT/LICENSE" "$ROOT/README.md" "$APP/"
cp -r "$ROOT/cfs_core" "$ROOT/cfs_qt" "$ROOT/data" "$APP/"
find "$APP" -name "__pycache__" -type d -prune -exec rm -rf {} +
"$PY" -m compileall -q "$APP" "$APPDIR/opt/python3.14/lib/python3.14" >/dev/null || true

echo ">> Starter, Desktop-Datei, Icon"
cp "$HERE/AppRun" "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"
cp "$HERE/connectfour-studio-qt.desktop" "$APPDIR/"
cp "$ROOT/data/connectfour-studio.png" "$APPDIR/connectfour-studio-qt.png"
ln -sf connectfour-studio-qt.png "$APPDIR/.DirIcon"
mkdir -p "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp "$HERE/connectfour-studio-qt.desktop" "$APPDIR/usr/share/applications/"
cp "$ROOT/data/connectfour-studio.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/connectfour-studio-qt.png"

echo ">> Inhalt pruefen"
python3 "$HERE/verify_appdir.py" "$APPDIR"

echo ">> AppImage packen"
rm -f "$OUT"
ARCH=x86_64 "$CACHE/appimagetool.AppImage" --no-appstream \
    --runtime-file "$CACHE/runtime-x86_64" "$APPDIR" "$OUT" >/dev/null
chmod +x "$OUT"
ls -la "$OUT"
echo ">> Fertig: $OUT"
