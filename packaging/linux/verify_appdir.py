"""Entpackten AppImage-Inhalt pruefen: nichts Fremdes, alles Noetige da.

Aufruf: python3 verify_appdir.py <squashfs-root|AppDir>
Exit 1 bei Verstoss.
"""

import os
import re
import sys

FORBIDDEN = [
    (r"(?i)mustrum", "Mustrum-Bezug"),
    (r"(^|/)elo_run(/|$)", "elo_run"),
    (r"^opt/connectfour-studio-qt/tools(/|$)", "tools/"),
    (r"(^|/)\.env", ".env*"),
    (r"(^|/)\.venv(/|$)", ".venv"),
    (r"(^|/)\.git(/|$)", ".git"),
    (r"quicksave\.4gp$", "quicksave.4gp"),
    (r"screenshot-\d+\.png$", "Screenshot"),
    (r"(^|/)lang\.cfg$", "lang.cfg"),
    (r"(^|/)settings\.json$", "settings.json"),
    (r"\.AppImage$", "AppImage im AppImage"),
    # Tk/Tcl (Pillows reiner Python-Helfer PIL/_tkinter_finder ist erlaubt)
    (r"(?i)(^|/)(tkinter|tcltk|libtk|libtcl|_tkinter(?!_finder))", "Tk/Tcl"),
    (r"site-packages/(build|pyproject_hooks|certifi|setuptools)(/|-)", "Build-Werkzeuge"),
    (r"site-packages/sitecustomize\.py$", "pip-Hook der Python-Basis"),
    (r"PySide6/(Qt/qml|designer|assistant|linguist|Qt/libexec|typesystems|include)(/|$)", "Qt-Entwicklerwerkzeuge"),
    (r"PySide6/Qt(Quick|Qml|Designer|Network|Sql|Test|Help|OpenGL|PrintSupport|Svg|Xml|UiTools)\w*\.abi3\.so$", "unnoetiges PySide6-Modul"),
    (r"libQt6(Quick|Qml|Designer|Network|Sql|Test|Help|Pdf|Multimedia|WebEngine)", "unnoetige Qt-Bibliothek"),
    (r"(^|/)(pip|ensurepip)(/|$)", "pip"),
]

REQUIRED = [
    "AppRun",
    "connectfour-studio-qt.desktop",
    "connectfour-studio-qt.png",
    "opt/python3.14/bin/python3.14",
    "opt/connectfour-studio-qt/connectfour_studio_qt.py",
    "opt/connectfour-studio-qt/cfs_core/engine.py",
    "opt/connectfour-studio-qt/cfs_qt/main_window.py",
    "opt/connectfour-studio-qt/LICENSE",
    "opt/connectfour-studio-qt/data/connectfour-studio.png",
] + [f"opt/connectfour-studio-qt/data/images/set{n}/back.bmp" for n in range(1, 21)]

REQUIRED_PATTERNS = [
    r"site-packages/PySide6/QtWidgets\.abi3\.so$",
    r"site-packages/PySide6/Qt/lib/libQt6Widgets\.so\.6$",
    r"site-packages/PySide6/Qt/plugins/platforms/libqxcb\.so$",
    r"site-packages/PySide6/Qt/plugins/platforms/libqwayland\.so$",
    r"site-packages/PySide6/Qt/plugins/platforms/libqoffscreen\.so$",
    r"site-packages/PySide6/Qt/translations/qtbase_de\.qm$",
    r"site-packages/shiboken6/",
    r"site-packages/bitbully/",
    r"site-packages/bitbully_databases/assets/book_12ply_distances\.dat$",
    r"site-packages/PIL/",
    r"usr/lib/xcb-fallback/libxcb-cursor\.so\.0$",
]


def main(root):
    files = []
    for dp, dn, fn in os.walk(root):
        for n in fn + [d for d in dn if os.path.islink(os.path.join(dp, d))]:
            files.append(os.path.relpath(os.path.join(dp, n), root).replace(os.sep, "/"))
    errors = []
    for pat, what in FORBIDDEN:
        hits = [f for f in files if re.search(pat, f)]
        if hits:
            errors.append(f"verboten ({what}): {hits[:5]}{' ...' if len(hits) > 5 else ''}")
    fs = set(files)
    for req in REQUIRED:
        if req not in fs:
            errors.append(f"fehlt: {req}")
    for pat in REQUIRED_PATTERNS:
        if not any(re.search(pat, f) for f in files):
            errors.append(f"fehlt (Muster): {pat}")
    # Uebersicht
    sizes = {}
    for f in files:
        p = os.path.join(root, f)
        if os.path.islink(p):
            continue
        parts = f.split("/")
        key = "/".join(parts[:2]) if parts[0] in ("opt", "usr") else parts[0]
        if "site-packages/" in f:
            key = "site-packages/" + f.split("site-packages/")[1].split("/")[0]
        sizes[key] = sizes.get(key, 0) + os.path.getsize(p)
    print(f"Dateien: {len(files)}")
    for k, v in sorted(sizes.items(), key=lambda kv: -kv[1])[:20]:
        print(f"  {v / 1e6:8.1f} MB  {k}")
    qtmods = sorted(f.split("/")[-1] for f in files if re.search(r"PySide6/Qt\w+\.abi3\.so$", f))
    qtlibs = sorted(f.split("/")[-1] for f in files if re.search(r"PySide6/Qt/lib/", f))
    print("PySide6-Module:", " ".join(qtmods))
    print("Qt-Bibliotheken:", " ".join(qtlibs))
    print("Programmordner:", " ".join(sorted(os.listdir(os.path.join(root, "opt", "connectfour-studio-qt")))))
    if errors:
        print("PRUEFUNG FEHLGESCHLAGEN:")
        for e in errors:
            print("  -", e)
        return 1
    print("PRUEFUNG OK: nichts Fremdes, alle Pflichtteile vorhanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
