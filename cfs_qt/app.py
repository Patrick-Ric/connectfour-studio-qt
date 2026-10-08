"""QApplication-Start (Icon, Qt-Uebersetzungen, Hauptfenster)."""

import os
import sys

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication

from cfs_core import APP_NAME, APP_VERSION, paths


class StudioApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName(APP_NAME)
        self.setApplicationVersion(APP_VERSION)
        self.setOrganizationName("ConnectFour Studio")
        self.setDesktopFileName("connectfour-studio-qt")
        icon = os.path.join(paths.DATA_DIR, "connectfour-studio.png")
        if os.path.isfile(icon):
            self.setWindowIcon(QIcon(QPixmap(icon)))
        self._qt_translator = None

    def install_qt_translator(self, code):
        """Qt-eigene Texte (Datei-Dialog, OK/Abbrechen ...) in der UI-Sprache."""
        if self._qt_translator is not None:
            self.removeTranslator(self._qt_translator)
            self._qt_translator = None
        if code == "en":
            return
        tr = QTranslator(self)
        tdir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if tr.load(QLocale(code), "qtbase", "_", tdir):
            self.installTranslator(tr)
            self._qt_translator = tr


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    app = StudioApp(argv)
    from cfs_core import lang as cfs_lang
    from cfs_qt.main_window import MainWindow
    win = MainWindow()
    app.install_qt_translator(cfs_lang.LANG)
    if len(argv) > 1 and os.path.isfile(argv[1]):
        win.load_start_file(argv[1])
    win.show()
    return app.exec()
