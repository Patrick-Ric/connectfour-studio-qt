"""GUI-Smoke-Test (QT_QPA_PLATFORM=offscreen): Hauptfenster, alle Dialoge,
Tastenkuerzel und die wichtigsten Ablaeufe einmal durchspielen."""
import os
import time

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog

from cfs_core import game as gm
from cfs_core import lang as cfs_lang
from cfs_core import paths

DRAW_SEQ = gm.parse_4gp("455714637617614767242476316455122212535333")


def wait_until(cond, timeout=30.0):
    end = time.time() + timeout
    while time.time() < end:
        QApplication.processEvents()
        if cond():
            return True
        time.sleep(0.01)
    QApplication.processEvents()
    return cond()


@pytest.fixture(scope="module")
def app():
    from cfs_qt.app import StudioApp
    a = QApplication.instance() or StudioApp(["test"])
    yield a


@pytest.fixture()
def win(app):
    from cfs_qt.main_window import MainWindow
    cfs_lang.set_lang("de")
    w = MainWindow()
    w.anim = False          # schnelle Tests (Animation separat getestet)
    w.show()
    w.activateWindow()
    QApplication.processEvents()
    yield w
    w.stop()
    w.close()
    QApplication.processEvents()


def menu_titles(w):
    return [a.text() for a in w.menuBar().actions()]


def menu_texts(w, idx):
    m = w.menuBar().actions()[idx].menu()
    return [a.text() for a in m.actions() if not a.isSeparator()]


# ---------------------------------------------------------------------------
def test_main_window_layout(win):
    assert win.windowTitle() == "ConnectFour Studio"
    # Natuerliche Startgroesse (Zoom 0,30 x 256 px = 77 px), sofern sie auf den
    # Bildschirm passt; sonst gekappt (offscreen-Bildschirm ist nur 800x600).
    from cfs_qt.main_window import START_ZOOM
    QApplication.processEvents()
    extra_w = win.width() - win.central.width()
    extra_h = win.height() - win.central.height()
    want = win._central_hint(START_ZOOM)
    fits = win._cap_to_screen(want.width() + extra_w, want.height() + extra_h) == \
        (want.width() + extra_w, want.height() + extra_h)
    if fits:
        assert wait_until(lambda: win.canvas.cell == 77, 3)
    else:
        assert 20 <= win.canvas.cell < 77
        scr = win.screen().availableGeometry()
        assert win.height() <= scr.height() and win.width() <= scr.width()
    assert menu_titles(win) == ["Datei", "Ansicht", "Einstellungen", "Kommandos", "Hilfe"]
    assert [b.text() for b in win.bar_buttons] == ["Neu", "<<", "<", ">", ">>", "Ziehen", "Analyse"]
    assert win.status_text() == "Bereit."
    cell = win.canvas.cell
    assert win.canvas.width() == 7 * cell
    assert all(b.width() == cell for b in win.bar_buttons)
    # Brett folgt der Fenstergroesse
    win.resize(1200, 900)
    assert wait_until(lambda: win.canvas.cell > cell, 5)
    img = win.grab()
    assert not img.isNull()


def test_menu_entries_and_accelerators(win):
    file_m = menu_texts(win, 0)
    assert file_m[0] == "Neues Spiel" and "Schnell speichern (F3)\tF3" in file_m
    assert menu_texts(win, 3) == ["erster Zug\tPfeil hoch", "Zug zurück\tPfeil links",
                                  "Zug vor\tPfeil rechts", "letzter Zug\tPfeil runter",
                                  "ziehen (Computer)\tF5", "alle Züge bewerten (1x)\tF6",
                                  "Dauer-Analyse\tF7"]
    settings = menu_texts(win, 2)
    assert "vorheriges Set\tBild hoch" in settings
    assert sum(1 for t in settings if t.startswith("Stein-Set ")) == 20
    assert len(win.level_actions) == 15
    assert win.level_actions["perfekt"].isChecked()


def test_every_dialog_opens(win, monkeypatch, tmp_path):
    from cfs_qt.dialogs import HelpDialog, InfoDialog, MatchDialog, RandomDialog
    # Zufallsstellung
    d = RandomDialog(win)
    d.show()
    assert d.n_spin.value() == 3 and d.w_combo.currentData() == "Gewinn"
    d.n_spin.setValue(5)
    d._ok()
    assert d.result_value == (5, "Gewinn")
    # Match
    win.match_dialog()
    assert isinstance(win._match_win, MatchDialog) and win._match_win.isVisible()
    md = win._match_win
    assert md.cb_g.currentData() == "leicht" and md.cb_r.currentData() == "mittel"
    assert not md.psw1[0].isEnabled()
    md.cb_r.setCurrentIndex(md.cb_r.findData("user1"))
    assert md.psw1[0].isEnabled() and not md.psw2[0].isEnabled()
    md.close()
    assert win._match_win is None
    # Info
    win.show_info()
    assert isinstance(win._info_win, InfoDialog)
    assert "BitBully" in win._info_win.text.toPlainText()
    win._info_win.close()
    # Hilfe: Links, Suche, Zoom
    win.show_help()
    h = win._help_win
    assert isinstance(h, HelpDialog) and h.isVisible()
    h.resize(660, 300)
    QApplication.processEvents()
    sb = h.text.verticalScrollBar()
    h.goto("tasten")
    QApplication.processEvents()
    assert sb.value() > 0
    h.find_edit.setText("ghost")
    h.find_next()
    assert len(h.text.extraSelections()) == 1 and h.find_info.text() == ""
    h.find_edit.setText("xyzzy-nicht-da")
    h.find_next()
    assert h.find_info.text() == "nichts gefunden"
    h.zoom(+1)
    assert h.zoom_info.text() == "110%"
    for _ in range(20):
        h.zoom(+1)
    assert h.zoom_info.text() == "180%"
    h.zoom(0)
    assert h.zoom_info.text() == "100%"
    h.close()
    # Datei-Dialoge: echter Qt-Dialog einmal zeigen ...
    fd = QFileDialog(win, cfs_lang.t("file_open_title"), str(tmp_path), win._file_filter(True))
    fd.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    fd.show()
    QApplication.processEvents()
    assert fd.isVisible()
    fd.close()
    # ... und Speichern/Laden ueber die Dialog-Pfade (Startordner = Home)
    target = tmp_path / "partie"
    captured = {}

    def fake_save(parent, title, start, flt):
        captured["start"] = start
        return str(target), flt
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(fake_save))
    win.game.set_moves([3, 3, 2])
    win.save_pos()
    assert captured["start"] == os.path.expanduser("~")
    assert (tmp_path / "partie.4gp").read_text() == "443"     # Endung .4gp ergaenzt

    def fake_open(parent, title, start, flt):
        captured["open_start"] = start
        return str(tmp_path / "partie.4gp"), flt
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(fake_open))
    win.new_game()
    win.load_pos()
    assert captured["open_start"] == str(tmp_path)              # zuletzt benutzter Ordner
    assert win.history == [3, 3, 2]
    assert win.status_text() == "Geladen: partie.4gp"


def test_keyboard_shortcuts(win):
    win.two_player = True                      # kein Computer-Gegenzug
    QTest.keyClick(win, Qt.Key.Key_4)
    QTest.keyClick(win, Qt.Key.Key_5)
    if win.history != [3, 4]:                  # Fallback, falls offscreen nicht aktiv
        for s in win._shortcuts[3:5]:
            s.activated.emit()
    assert win.history == [3, 4]
    QTest.keyClick(win, Qt.Key.Key_Left)
    assert win.history == [3]
    QTest.keyClick(win, Qt.Key.Key_Right)
    assert win.history == [3, 4]
    QTest.keyClick(win, Qt.Key.Key_Up)
    assert win.history == []
    QTest.keyClick(win, Qt.Key.Key_Down)
    assert win.history == [3, 4]
    old = win.set_no
    QTest.keyClick(win, Qt.Key.Key_PageDown)
    assert win.set_no != old
    QTest.keyClick(win, Qt.Key.Key_PageUp)
    assert win.set_no == old
    QTest.keyClick(win, Qt.Key.Key_F6)
    assert win.scores_visible
    QTest.keyClick(win, Qt.Key.Key_F6)
    assert not win.scores_visible and win.status_text() == "Bewertung aus (1-7)."
    QTest.keyClick(win, Qt.Key.Key_F3)
    assert open(paths.quicksave_path()).read() == "45"
    win.new_game()
    QTest.keyClick(win, Qt.Key.Key_F4)
    assert win.history == [3, 4]
    QTest.keyClick(win, Qt.Key.Key_F1)
    assert win._help_win is not None and win._help_win.isVisible()
    win._help_win.close()


def test_human_vs_computer_and_score(win):
    win.human_move(3)
    assert wait_until(lambda: not win.thinking and len(win.history) == 2)
    assert win.status_text().startswith("Computer zog")
    assert win.info["info_nodes"].text() != "–"
    # Spielstand: Mensch gewinnt eine Partie
    win._stand_toggle()
    assert win.stand_big.text() == "0-0" and win.act_stand.isChecked()
    win.new_game()
    win.game.set_moves([0, 1, 0, 1, 0, 1])
    win.human_move(0)
    assert win.board.is_game_over()
    assert win.status_text() == "Spielende: Gelb gewinnt!"
    assert win.stand_big.text() == "1-0"
    win._stand_reset()
    assert win.stand_big.text() == "0-0"


def test_computer_opens_on_empty_board(win):
    win.engine_move()
    assert wait_until(lambda: not win.thinking and len(win.history) == 1)
    assert win.human_first is False
    assert win.current_player_label() == "Mensch"


def test_drop_animation(win):
    win.anim = True
    win.two_player = True
    win.human_move(2)
    assert win._anim_running and win.falling is not None
    assert wait_until(lambda: not win._anim_running, 5)
    assert win.history == [2] and win.falling is None


def test_selfplay_finishes(win):
    win.game.set_moves(DRAW_SEQ[:34])
    win.refresh()
    win._select_selfplay()
    assert win.mode == "selfplay"
    assert wait_until(lambda: win.board.is_game_over() and not win.thinking, 60)
    assert win.mode == "computer"              # Modus zurueck nach Partieende


def test_auto_analysis(win):
    win.two_player = True
    win._set_auto_analyze(True)
    assert wait_until(lambda: win.scores_visible and win.status_text().startswith("Analyse:"), 30)
    win.human_move(3)
    assert wait_until(lambda: win.scores_visible and not win.ana_busy, 30)
    win.toggle_auto_analyze_btn()
    assert not win.auto_analyze and win.last_scores[0][1] == ""


def test_eval_after_new_game(win):
    # Tk-Bug behoben: F6 direkt nach "Neu" wurde dort sofort abgebrochen.
    win.new_game()
    win.toggle_scores()
    assert win.scores_visible


def test_random_position(win):
    win.start_random(3, "Gewinn")
    assert wait_until(lambda: len(win.history) == 3 and win.rand_job is None, 30)
    assert win.human_first is False and win.scores_visible


def test_match_turbo(win):
    size = win.size()
    win._match_start("zufall", "perfekt", 2, True, blind=True)
    assert wait_until(lambda: win.match.fertig, 90)
    assert win.size().width() == size.width()     # lange Statuszeile verbreitert nicht
    m = win.match
    assert m.done() == 2 and not m.abgebrochen
    assert win.status_text().startswith("Computer-Computer Match beendet")
    win.match_dialog()
    assert "Partien: 2/2" in win._match_win.result.toPlainText()
    win._match_win.close()


def test_match_with_human_and_stop(win):
    win._match_start("mensch", "zufall", 1, False)
    assert win._match_human_turn()
    win.human_move(3)
    assert wait_until(lambda: not win.thinking and len(win.history) == 2, 30)
    assert win._match_human_turn()
    win.undo()
    assert win.status_text() == cfs_lang.t("status_match_running")
    win.stop()
    assert win.match.fertig and win.match.abgebrochen


def test_language_switch_all(win):
    for code in cfs_lang.LANG_ORDER:
        win.switch_lang(code)
        assert cfs_lang.LANG == code
        assert menu_titles(win)[0] == cfs_lang.t("menu_file", code)
        assert win.bar_buttons[0].text() == cfs_lang.t("btn_new", code)
        assert win.info_box.title() == cfs_lang.t("info_box", code)
        assert win.lang_actions[code].isChecked()
    assert open(os.path.join(paths.user_dir(), "lang.cfg")).read() == "it"
    win.switch_lang("de")
    assert cfs_lang.detect_start_lang() == "de"


def test_settings_persist(win):
    win.act_ghost.setChecked(False)
    win.toggle_ghost()
    win.switch_set(5)
    win.switch_depth("mittel")
    data = paths.load_settings()
    assert data["ghost"] is False and data["set_no"] == 5 and data["level"] == "mittel"
    win.act_ghost.setChecked(True)
    win.toggle_ghost()
    win.switch_set(1)
    win.switch_depth("perfekt")


def test_start_file_argument(win, tmp_path):
    p = tmp_path / "start.4gp"
    p.write_text("4433")
    win.load_start_file(str(p))
    assert win.history == [3, 3, 2, 2] and win.scores_visible


def test_board_mouse(win):
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QWheelEvent
    from cfs_qt.board import SCORE_GAP, SCORE_H
    win.two_player = True
    c = win.canvas
    cell = c.cell
    QTest.mouseMove(c, QPoint(int(4.5 * cell), cell))
    assert wait_until(lambda: win.hover_col == 4, 2)            # Ghost-Stein-Spalte
    QTest.mouseClick(c, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     QPoint(int(2.5 * cell), cell))              # Klick aufs Brett
    assert win.history == [2]
    QTest.mouseClick(c, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     QPoint(int(5.5 * cell), c.board_h() + SCORE_GAP + SCORE_H // 2))
    assert win.history == [2, 5]                                # Klick in die Wertungszeile
    QTest.mouseClick(c, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     QPoint(int(1.5 * cell), c.board_h() + 1))   # Luecke -> nichts
    assert win.history == [2, 5]
    old = win.set_no
    pos = QPointF(cell, cell)
    ev = QWheelEvent(pos, c.mapToGlobal(pos), QPoint(0, 0), QPoint(0, -120),
                     Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                     Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(c, ev)
    assert win.set_no != old                                    # Rad runter = naechstes Set


def test_buttons_highlight_on_hover(win):
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QEnterEvent
    from cfs_qt.buttons import HoverButton
    buttons = win.bar_buttons + [win.stand_toggle_btn, win.stand_reset_btn]
    assert all(isinstance(b, HoverButton) for b in buttons)
    b = win.bar_buttons[0]
    before = b.grab().toImage()
    QApplication.sendEvent(b, QEnterEvent(QPointF(5, 5), QPointF(5, 5), QPointF(5, 5)))
    assert b.hovered
    hover = b.grab().toImage()
    # Stilunabhaengig (Fusion, windows11 ...): ganze Taste vergleichen. Die
    # Toenung in der Hervorhebungsfarbe verschiebt die Pixel Richtung Blau.
    changed, d_red, d_blue = 0, 0, 0
    for y in range(0, hover.height(), 2):
        for x in range(0, hover.width(), 2):
            c0, c1 = before.pixelColor(x, y), hover.pixelColor(x, y)
            if c0 != c1:
                changed += 1
                d_red += c1.red() - c0.red()
                d_blue += c1.blue() - c0.blue()
    assert changed > (hover.width() * hover.height()) // 40   # sichtbar veraendert
    hl = b.palette().highlight().color()
    if hl.blue() > hl.red():
        assert d_blue > d_red                               # Toenung Richtung Hervorhebungsfarbe
    QApplication.sendEvent(b, QEvent(QEvent.Type.Leave))
    assert not b.hovered
    assert b.grab().toImage() == before                 # Verlassen stellt die Taste wieder her
