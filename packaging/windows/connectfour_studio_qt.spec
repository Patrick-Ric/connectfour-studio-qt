# -*- mode: python ; coding: utf-8 -*-
# PyInstaller-Spec fuer ConnectFour Studio (Qt). Erwartet die von
# prepare_build.py vorbereiteten Quellen in build/src.
#
#   pyinstaller --noconfirm --clean packaging/windows/connectfour_studio_qt.spec
#
# Ergebnis (onedir): dist/ConnectFour Studio Qt/ConnectFour Studio Qt.exe
# Nur QtCore/QtGui/QtWidgets werden eingebunden (PySide6-Hook sammelt die
# zugehoerigen Plugins); vom Eroeffnungsbuch nur 12-ply-dist.
import os

import bitbully_databases

SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
ROOT = os.path.dirname(os.path.dirname(SPEC_DIR))
SRC = os.path.join(ROOT, "build", "src")
APP_NAME = "ConnectFour Studio Qt"

book = os.path.join(os.path.dirname(bitbully_databases.__file__), "assets",
                    "book_12ply_distances.dat")

datas = [
    (os.path.join(SRC, "data", "images"), os.path.join("data", "images")),
    (os.path.join(SRC, "data", "connectfour-studio.png"), "data"),
    (os.path.join(SRC, "LICENSE"), "."),
    (book, os.path.join("bitbully_databases", "assets")),
]

excludes = [
    "tkinter", "_tkinter", "unittest", "pydoc_data", "test",
    "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtSql", "PySide6.QtTest",
    "PySide6.QtXml", "PySide6.QtSvg", "PySide6.QtSvgWidgets", "PySide6.QtPrintSupport",
    "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtUiTools", "PySide6.QtDBus",
    "PySide6.QtConcurrent",
]

a = Analysis(
    [os.path.join(SRC, "connectfour_studio_qt.py")],
    pathex=[SRC],
    binaries=[],
    datas=datas,
    hiddenimports=["bitbully_databases", "bitbully.bitbully_core"],
    hookspath=[],
    hooksconfig={"PySide6": {}},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
# Qt-Uebersetzungen nur fuer die 6 Programmsprachen (qtbase_*.qm)
KEEP_QM = {f"qtbase_{c}.qm" for c in ("de", "en", "es", "fr", "nl", "it")}
a.datas = [d for d in a.datas
           if not (d[0].replace("\\", "/").split("/")[-2:-1] == ["translations"]
                   and d[0].endswith(".qm") and os.path.basename(d[0]) not in KEEP_QM)]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(SRC, "connectfour-studio-qt.ico"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)
