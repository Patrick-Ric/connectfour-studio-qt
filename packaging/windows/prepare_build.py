"""Bereitet den Windows-Build (PyInstaller) vor.

Kopiert die Programmdateien nach build/src und erzeugt das Programm-Icon
(build/src/connectfour-studio-qt.ico). Die Dateien im Repository bleiben
unveraendert.

Anders als bei der Tk-Version ist KEIN Patchen der Quellen mehr noetig:
cfs_core/paths.py erkennt den gepackten Betrieb selbst (sys._MEIPASS fuer
die Bilder) und schreibt Quicksave, Sprachwahl und Einstellungen nach
%APPDATA%\\ConnectFour Studio Qt (bzw. CFS_USER_DIR, falls gesetzt).
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "build", "src")

FILES = ["connectfour_studio_qt.py", "LICENSE", "README.md"]
PACKAGES = ["cfs_core", "cfs_qt"]


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    for f in FILES:
        shutil.copy2(os.path.join(ROOT, f), OUT)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for p in PACKAGES:
        shutil.copytree(os.path.join(ROOT, p), os.path.join(OUT, p), ignore=ignore)
    shutil.copytree(os.path.join(ROOT, "data"), os.path.join(OUT, "data"), ignore=ignore)
    for leftover in ("lang.cfg", "settings.json", "quicksave.4gp"):
        p = os.path.join(OUT, "data", leftover)
        if os.path.exists(p):
            os.remove(p)

    sys.path.insert(0, os.path.join(ROOT, "packaging"))
    import make_icon
    make_icon.main([os.path.join(OUT, "connectfour-studio-qt.ico")])
    print("Build-Quellen vorbereitet in", OUT)


if __name__ == "__main__":
    main()
