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


def run_smoke(app, win, report=print):
    """Selbsttest (CFS_SMOKE_TEST=1, z.B. offscreen in der AppImage):
    Hauptfenster + jeden Dialog einmal oeffnen, einen Computerzug rechnen,
    alles schliessen. Rueckgabe: Liste der Fehler (leer = OK)."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QFileDialog

    from cfs_qt.dialogs import RandomDialog
    errors = []

    def check(name, cond):
        report(f"smoke: {name}: {'ok' if cond else 'FEHLER'}")
        if not cond:
            errors.append(name)

    def s_dialogs():
        check("main window", win.isVisible() and len(win.menuBar().actions()) == 5)
        d = RandomDialog(win)
        d.show()
        check("random dialog", d.isVisible())
        d.close()
        win.match_dialog()
        check("match dialog", win._match_win is not None and win._match_win.isVisible())
        win._match_win.close()
        win.show_help()
        check("help dialog", win._help_win is not None and win._help_win.isVisible())
        win._help_win.close()
        win.show_info()
        check("info dialog", win._info_win is not None and win._info_win.isVisible())
        win._info_win.close()
        fd = QFileDialog(win)
        fd.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        fd.show()
        check("file dialog", fd.isVisible())
        fd.close()
        win.anim = False
        win.engine_move()

    def s_wait(n=[0]):
        n[0] += 1
        if (win.thinking or not win.history) and n[0] < 300:
            QTimer.singleShot(100, s_wait)
            return
        check("engine move", len(win.history) == 1 and not win.thinking)
        win.close()
        app.exit(1 if errors else 0)

    QTimer.singleShot(200, s_dialogs)
    QTimer.singleShot(400, s_wait)
    return errors


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
    if os.environ.get("CFS_SMOKE_TEST"):
        errors = run_smoke(app, win)
        rc = app.exec()
        print("SMOKE OK" if rc == 0 and not errors else "SMOKE FEHLER: " + ", ".join(errors))
        return rc
    return app.exec()
