"""AppDir ausduennen: nur die noetigen Qt-Module, kein Tk, kein pip.

Aufruf: python3 prune_appdir.py <AppDir>

Qt: behalten werden die Python-Module QtCore/QtGui/QtWidgets, ausgewaehlte
Plugins (Plattformen xcb/wayland/offscreen/minimal, Plattform-Themes,
Eingabemethoden, xcb-GL, Wayland-Client, SVG-Icons) und genau die Qt-
Bibliotheken, die diese per DT_NEEDED (rekursiv) brauchen. Uebersetzungen
nur qtbase fuer die 6 Programmsprachen.
"""

import glob
import os
import re
import shutil
import subprocess
import sys

KEEP_PY_MODULES = {"QtCore", "QtGui", "QtWidgets"}
KEEP_PLUGINS = {
    "platforms": {"libqxcb.so", "libqwayland.so", "libqoffscreen.so", "libqminimal.so"},
    "platformthemes": None,             # alle (Portal/GTK3 fuer native Dialoge)
    # Compose/IBus (Tottasten); NICHT das Virtual-Keyboard (zieht QtQuick)
    "platforminputcontexts": {"libcomposeplatforminputcontextplugin.so",
                              "libibusplatforminputcontextplugin.so"},
    "xcbglintegrations": None,
    "wayland-decoration-client": None,
    "wayland-graphics-integration-client": {"libqt-plugin-wayland-egl.so"},
    "wayland-shell-integration": {"libxdg-shell.so"},
    "iconengines": {"libqsvgicon.so"},  # SVG-Symbole im Datei-Dialog
    "imageformats": {"libqsvg.so"},
}
KEEP_TRANSLATIONS = {f"qtbase_{c}.qm" for c in ("de", "en", "es", "fr", "nl", "it")}
PYSIDE_REMOVE = ("assistant", "designer", "linguist", "lrelease", "lupdate", "qmlformat",
                 "qmllint", "qmlls", "svgtoqml", "doc", "glue", "include", "lib",
                 "scripts", "typesystems", "libpyside6qml.abi3.so.6.12",
                 "Qt/qml", "Qt/libexec", "Qt/metatypes")
STDLIB_REMOVE = ("test", "idlelib", "tkinter", "turtledemo", "ensurepip", "turtle.py",
                 "__phello__", "pydoc_data")


def rm(path):
    if os.path.islink(path) or os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def needed(path):
    try:
        out = subprocess.run(["readelf", "-d", path], capture_output=True, text=True).stdout
    except FileNotFoundError:
        sys.exit("readelf fehlt (binutils)")
    return re.findall(r"\(NEEDED\)\s+Shared library: \[(.+?)\]", out)


def prune_pyside(site):
    ps = os.path.join(site, "PySide6")
    qt = os.path.join(ps, "Qt")
    for name in PYSIDE_REMOVE:
        rm(os.path.join(ps, name))
    for f in os.listdir(ps):
        m = re.match(r"(Qt\w+)\.(abi3\.so|pyi)$", f)
        if f.endswith(".pyi") or (m and m.group(1) not in KEEP_PY_MODULES):
            rm(os.path.join(ps, f))
    # Plugins
    pdir = os.path.join(qt, "plugins")
    for sub in os.listdir(pdir):
        keep = KEEP_PLUGINS.get(sub, set())
        d = os.path.join(pdir, sub)
        if sub not in KEEP_PLUGINS:
            rm(d)
            continue
        if keep is None:
            continue
        for f in os.listdir(d):
            if f not in keep:
                rm(os.path.join(d, f))
    # Uebersetzungen
    tdir = os.path.join(qt, "translations")
    for f in os.listdir(tdir):
        if f not in KEEP_TRANSLATIONS:
            rm(os.path.join(tdir, f))
    # Qt-Bibliotheken: DT_NEEDED-Huelle der behaltenen Module/Plugins
    libdir = os.path.join(qt, "lib")
    available = {f: os.path.join(libdir, f) for f in os.listdir(libdir)}
    roots = [os.path.join(ps, f"{m}.abi3.so") for m in KEEP_PY_MODULES]
    roots += glob.glob(os.path.join(ps, "libpyside6.abi3.so*"))
    roots += glob.glob(os.path.join(pdir, "*", "*.so"))
    keep_libs, todo = set(), list(roots)
    while todo:
        for dep in needed(todo.pop()):
            if dep in available and dep not in keep_libs:
                keep_libs.add(dep)
                todo.append(available[dep])
    for f, p in available.items():
        if f not in keep_libs:
            rm(p)
    return sorted(keep_libs)


def prune_python(appdir, site):
    pyroot = os.path.join(appdir, "opt", "python3.14")
    stdlib = os.path.join(pyroot, "lib", "python3.14")
    for name in STDLIB_REMOVE:
        rm(os.path.join(stdlib, name))
    for f in glob.glob(os.path.join(stdlib, "lib-dynload", "_tkinter*")):
        rm(f)
    for pkg in glob.glob(os.path.join(site, "pip")) + glob.glob(os.path.join(site, "pip-*")):
        rm(pkg)
    for f in glob.glob(os.path.join(pyroot, "bin", "pip*")) + glob.glob(os.path.join(appdir, "usr", "bin", "pip*")):
        rm(f)
    # Tcl/Tk (nur fuer tkinter) und Begleitbibliotheken entfernen
    rm(os.path.join(appdir, "usr", "share", "tcltk"))
    for pat in ("libtk*", "libtcl*", "libXft*", "libXrender*", "libXss*"):
        for f in glob.glob(os.path.join(appdir, "usr", "lib", pat)):
            rm(f)
    # Starter/Metadaten der Python-Basis-AppImage
    for f in ("AppRun", ".DirIcon"):
        rm(os.path.join(appdir, f))
    for f in glob.glob(os.path.join(appdir, "*.desktop")) + glob.glob(os.path.join(appdir, "*.png")) \
            + glob.glob(os.path.join(appdir, "*.svg")):
        rm(f)
    for d in ("applications", "metainfo", "icons"):
        rm(os.path.join(appdir, "usr", "share", d))
    for d in glob.glob(os.path.join(site, "*", "tests")):
        rm(d)
    # Werkzeuge der Python-Basis, die das Programm nicht braucht
    for name in ("build", "packaging", "pyproject_hooks", "certifi", "setuptools", "wheel",
                 "_distutils_hack"):
        for f in glob.glob(os.path.join(site, name)) + glob.glob(os.path.join(site, name + "-*")):
            rm(f)
    # Eroeffnungsbuecher: das Programm laedt fest nur 12-ply-dist
    for f in ("book_12ply.dat", "book_8ply.dat"):
        rm(os.path.join(site, "bitbully_databases", "assets", f))
    rm(os.path.join(site, "sitecustomize.py"))
    rm(os.path.join(site, "distutils-precedence.pth"))
    rm(os.path.join(appdir, "opt", "_internal"))
    bindir = os.path.join(pyroot, "bin")
    for f in os.listdir(bindir):
        if not f.startswith("python"):
            rm(os.path.join(bindir, f))


def main(appdir):
    site = glob.glob(os.path.join(appdir, "opt", "python3.14", "lib", "python3.14", "site-packages"))[0]
    libs = prune_pyside(site)
    prune_python(appdir, site)
    print("Qt-Bibliotheken behalten:", " ".join(libs))


if __name__ == "__main__":
    main(sys.argv[1])
