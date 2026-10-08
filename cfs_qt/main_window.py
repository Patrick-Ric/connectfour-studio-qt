"""Hauptfenster von ConnectFour Studio (Qt-Port von ConnectFourStudio(tk.Tk)).

Ablaufsteuerung 1:1 aus connectfour_studio.py: Modi (Mensch-Computer,
2 Spieler, Computer-Computer ausspielen, Match), Engine-Zug im Worker-Thread,
Dauer-Analyse, Zufallsstellung, Laden/Speichern, Spielstand.

Thread-Modell: Worker sind Python-Threads (BitBully ist durch Engine.lock
geschuetzt). GUI-Zugriffe aus Workern laufen ausschliesslich ueber
_safe_after() -> Qt-Signal (queued) -> Hauptthread.
"""

import os
import threading
import time
import traceback

from PySide6.QtCore import QObject, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QFileDialog, QFrame, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMenu,
                               QMessageBox, QPushButton, QVBoxLayout, QWidget)

from cfs_core import APP_NAME, paths
from cfs_core import engine as eng
from cfs_core import game as gm
from cfs_core import lang as cfs_lang
from cfs_core import levels, sets
from cfs_core.match import Match, SessionScore, human_won_normal
from cfs_qt.board import SCORE_H, BoardCanvas
from cfs_qt.dialogs import HelpDialog, InfoDialog, MatchDialog, RandomDialog
from cfs_qt.tiles import TileCache

COLS, ROWS = gm.COLS, gm.ROWS
MARGIN = 8          # Fensterrand (Tk: padding=8)
PANEL_GAP = 6       # Abstand Brett -> rechte Spalte
BAR_GAP = 2         # Abstand Wertungszeile -> Buttonleiste
START_ZOOM = 0.30   # natuerliche Startgroesse (256-px-Kacheln)
MIN_ZOOM, MAX_ZOOM = 0.08, 4.0

MODE_COMPUTER = "computer"     # Mensch-Computer
MODE_TWO = "two"               # 2-Spieler (beide Mensch)
MODE_SELFPLAY = "selfplay"     # Computer-Computer (ausspielen)

INFO_KEYS = ("info_move", "info_level", "info_depth", "info_value",
             "info_nodes", "info_time", "info_nodes_per_sec", "info_book")
BAR_KEYS = ("btn_new", "btn_first", "btn_back", "btn_forward", "btn_last",
            "btn_move", "btn_analyze")
DASH = "–"


class _Bridge(QObject):
    """Worker-Thread -> GUI-Thread (queued connection)."""
    call = Signal(object, int)


class _Central(QWidget):
    """Zentrales Widget mit eigener Geometrie (Brett links oben, rechte
    Spalte direkt daneben, Restplatz rechts/unten wie in der Tk-Version)."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win

    def resizeEvent(self, ev):
        self.win._do_layout()

    def sizeHint(self):
        return self.win._central_hint(START_ZOOM)

    def minimumSizeHint(self):
        return self.win._central_hint(MIN_ZOOM)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        try:
            cfs_lang.set_lang(cfs_lang.detect_start_lang())
        except Exception:
            pass
        self.settings = paths.load_settings()
        self._closed = False
        self._bridge = _Bridge()
        self._bridge.call.connect(self._run_call)

        self.engine = eng.Engine()
        self.game = gm.Game()
        self.raw = sets.SetArt.load_all()
        self.tiles = TileCache(self.raw)
        ids = [s for s in sets.set_menu_order(self.raw) if s in sets._MENU_SETS] or sorted(self.raw)
        sn = self.settings.get("set_no", sets.START_SET)
        self.set_no = sn if sn in ids else (sets.START_SET if sets.START_SET in ids else ids[0])
        lv = self.settings.get("level", "perfekt")
        self.level = lv if lv in set(levels.STUFEN_ORDER) else "perfekt"

        # Spiel-/Ablaufzustand (Namen wie in der Tk-Version)
        self.mode = MODE_COMPUTER
        self.two_player = False
        self.selfplay = False
        self.human_first = True
        self.match = None
        self.match_stufe = None
        self._match_win = None
        self.thinking = False
        self.cancel = False
        self.rand_job = None
        self.show_last = bool(self.settings.get("show_last", True))
        self.anim = bool(self.settings.get("anim", True))
        self.ghost = bool(self.settings.get("ghost", True))
        self.hover_col = None
        self.falling = None
        self.last_scores = None
        self.scores_visible = False
        self.auto_analyze = False
        self.ana_seq = 0
        self.ana_busy = False
        self.ana_pending = None
        self.ana_running_snap = None
        self.move_times = []
        self.stand = SessionScore()
        self._help_win = None
        self._info_win = None
        self._cell = max(8, int(round(self._tile_w() * START_ZOOM)))

        self._anim_running = False
        self._anim_timer = QTimer(self)
        self._anim_timer.setSingleShot(True)
        self._anim_timer.timeout.connect(lambda: self._anim_next and self._anim_next())
        self._anim_next = None
        self._match_timer = QTimer(self)
        self._match_timer.setSingleShot(True)
        self._match_timer.timeout.connect(lambda: self._match_timer_fn and self._match_timer_fn())
        self._match_timer_fn = None

        self._build_widgets()
        self._build_menu()
        self._build_shortcuts()
        self._apply_panel_width()
        self.refresh(all_scores=False)
        self._initial_size()

    # =====================================================================
    # Hilfsfunktionen
    # =====================================================================
    @property
    def history(self):
        return self.game.history

    @property
    def board(self):
        return self.game.board

    def _tile_w(self):
        try:
            return self.raw[self.set_no]["back"].size[0]
        except Exception:
            return 256

    @property
    def zoom(self):
        return self._cell / float(self._tile_w())

    def set_status(self, text):
        self.status_label.setText(text)

    def status_text(self):
        return self.status_label.text()

    def set_info(self, key, text):
        lab = self.info.get(key)
        if lab is not None:
            lab.setText(text)

    def _safe_after(self, ms, fn):
        """Thread-sicherer GUI-Callback (ersetzt Queue + Tk-Poll)."""
        if self._closed:
            return
        self._bridge.call.emit(fn, int(ms))

    def _run_call(self, fn, ms):
        if self._closed:
            return

        def run():
            if self._closed:
                return
            try:
                fn()
            except Exception:
                traceback.print_exc()
        if ms <= 0:
            run()
        else:
            QTimer.singleShot(ms, run)

    def _save_settings(self):
        self.settings.update(ghost=self.ghost, anim=self.anim, show_last=self.show_last,
                             set_no=self.set_no, level=self.level)
        paths.save_settings(self.settings)

    # =====================================================================
    # Widgets / Layout
    # =====================================================================
    def _build_widgets(self):
        central = _Central(self)
        self.setCentralWidget(central)
        self.central = central
        self.canvas = BoardCanvas(self, central)
        self.canvas.columnClicked.connect(self._on_canvas_click)
        self.canvas.hoverChanged.connect(self.set_hover)
        self.canvas.setWheel.connect(self.cycle_set)

        self.bar_buttons = []
        cmds = (self.new_game, self.goto_first, self.undo, self.redo, self.goto_last,
                self.engine_move, self.toggle_auto_analyze_btn)
        for key, cmd in zip(BAR_KEYS, cmds):
            b = QPushButton(cfs_lang.t(key), central)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setMinimumSize(1, 1)
            b.clicked.connect(lambda _c=False, f=cmd: f())
            self.bar_buttons.append(b)

        panel = QWidget(central)
        self.panel = panel
        pv = QVBoxLayout(panel)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(6)
        # Am Zuge
        self.turn_box = QGroupBox(cfs_lang.t("info_turn"))
        th = QHBoxLayout(self.turn_box)
        self.turn_icon = QLabel()
        self.turn_icon.setFixedSize(40, 40)
        self.turn_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.turn_text = QLabel(cfs_lang.t("info_human"))
        self.turn_text.setWordWrap(True)
        th.addWidget(self.turn_icon)
        th.addWidget(self.turn_text, 1)
        pv.addWidget(self.turn_box)
        # Info
        self.info_box = QGroupBox(cfs_lang.t("info_box"))
        ig = QGridLayout(self.info_box)
        ig.setVerticalSpacing(1)
        self.info = {}
        self.info_labels = {}
        for i, key in enumerate(INFO_KEYS):
            lab = QLabel(cfs_lang.t(key) + ":")
            val = QLabel(DASH)
            ig.addWidget(lab, i, 0)
            ig.addWidget(val, i, 1)
            self.info_labels[key] = lab
            self.info[key] = val
        ig.setColumnStretch(1, 1)
        pv.addWidget(self.info_box)
        # Spielstand (Rahmen immer sichtbar, Inhalt nur wenn an)
        self.stand_box = QGroupBox(cfs_lang.t("score_box"))
        sv = QVBoxLayout(self.stand_box)
        self.stand_head = QLabel("")
        self.stand_head.setWordWrap(True)
        self.stand_big = QLabel("")
        big = QFont(self.font())
        big.setPointSizeF(max(9.0, self.font().pointSizeF()) * 4)
        self.stand_big.setFont(big)
        self.stand_sub = QLabel("")
        self.stand_elo = QLabel("")
        for w, center in ((self.stand_head, False), (self.stand_big, True),
                          (self.stand_sub, True), (self.stand_elo, True)):
            if center:
                w.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            sv.addWidget(w)
        sb = QHBoxLayout()
        self.stand_toggle_btn = QPushButton(cfs_lang.t("score_on"))
        self.stand_reset_btn = QPushButton(cfs_lang.t("score_reset_btn"))
        for b, f in ((self.stand_toggle_btn, self._stand_toggle),
                     (self.stand_reset_btn, self._stand_reset)):
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _c=False, fn=f: fn())
            sb.addWidget(b)
        sb.addStretch(1)
        sv.addLayout(sb)
        pv.addWidget(self.stand_box)
        pv.addStretch(1)

        # Statuszeile (eingesunken wie Tk relief=sunken)
        self.status_label = QLabel(cfs_lang.t("status_ready"))
        self.status_label.setFrameShape(QFrame.Shape.StyledPanel)
        self.status_label.setFrameShadow(QFrame.Shadow.Sunken)
        self.status_label.setMinimumWidth(1)
        self.statusBar().addWidget(self.status_label, 1)
        self.statusBar().setSizeGripEnabled(True)

    def _apply_panel_width(self):
        """Rechte Spalte fest breit (Labels + 15 Zeichen Wert), damit das
        Brett beim Wechsel der Infotexte nicht springt."""
        fm = self.fontMetrics()
        lab_w = max(fm.horizontalAdvance(cfs_lang.t(k) + ":") for k in INFO_KEYS)
        w = lab_w + fm.horizontalAdvance("0") * 15 + 40
        btn_w = (self.stand_toggle_btn.sizeHint().width()
                 + self.stand_reset_btn.sizeHint().width() + 40)
        self.panel.setFixedWidth(max(190, w, btn_w))
        self.central.updateGeometry()
        self._do_layout()

    def _bar_h(self):
        return self.bar_buttons[0].sizeHint().height()

    def _central_hint(self, zoom):
        cell = max(8, int(round(self._tile_w() * zoom)))
        w = 2 * MARGIN + COLS * cell + PANEL_GAP + self.panel.width()
        h_board = 2 * MARGIN + ROWS * cell + SCORE_H + BAR_GAP + self._bar_h()
        h_panel = 2 * MARGIN + self.panel.minimumSizeHint().height()
        return QSize(w, max(h_board, h_panel))

    def _do_layout(self):
        """Auto-Zoom: Brett so gross wie Fensterbreite (minus rechte Spalte)
        und -hoehe erlauben (Zoom 0,08 ... 4,0)."""
        if not hasattr(self, "panel"):
            return
        W, H = self.central.width(), self.central.height()
        bar_h = self._bar_h()
        avail_w = W - 2 * MARGIN - PANEL_GAP - self.panel.width()
        avail_h = H - 2 * MARGIN - SCORE_H - BAR_GAP - bar_h
        tw = self._tile_w()
        cell = int(min(avail_w / COLS, avail_h / ROWS))
        cell = max(int(round(tw * MIN_ZOOM)), min(int(round(tw * MAX_ZOOM)), cell))
        if cell != self._cell or self.canvas.cell != cell:
            self._cell = cell
            self.canvas.set_cell(cell)
            self._update_turn()
        self.canvas.move(MARGIN, MARGIN)
        y = MARGIN + self.canvas.canvas_h() + BAR_GAP
        for c, b in enumerate(self.bar_buttons):
            b.setGeometry(MARGIN + c * cell, y, cell, bar_h)
        self.panel.setGeometry(MARGIN + COLS * cell + PANEL_GAP, MARGIN,
                               self.panel.width(), max(1, H - 2 * MARGIN))

    def showEvent(self, ev):
        super().showEvent(ev)
        if not getattr(self, "_start_fixed", False):
            self._start_fixed = True
            QTimer.singleShot(0, self._fix_start_size)

    def _fix_start_size(self):
        """Natuerliche Startgroesse exakt (Zoom 0,30): fehlende Pixel des
        zentralen Bereichs einmalig auf das Fenster aufschlagen."""
        want = self._central_hint(START_ZOOM)
        dw = max(0, want.width() - self.central.width())
        dh = max(0, want.height() - self.central.height())
        if dw or dh:
            w, h = self._cap_to_screen(self.width() + dw, self.height() + dh)
            self.resize(w, h)

    def _cap_to_screen(self, w, h):
        """Nie groesser als der Bildschirm (minus Taskleisten-Rand, wie Tk)."""
        scr = self.screen().availableGeometry() if self.screen() else None
        if scr is not None:
            w = min(w, max(200, scr.width() - 40))
            h = min(h, max(200, scr.height() - 80))
        return w, h

    def _initial_size(self):
        hint = self.sizeHint()
        self.resize(*self._cap_to_screen(hint.width(), hint.height()))

    # =====================================================================
    # Menue
    # =====================================================================
    def _act(self, menu, key, slot, acc=None, checkable=False, checked=False, group=None, data=None,
             label=None):
        text = label if label is not None else cfs_lang.t(key)
        if acc:
            text = f"{text}\t{acc}"
        a = QAction(text, self)
        if checkable:
            a.setCheckable(True)
            a.setChecked(checked)
        if group is not None:
            group.addAction(a)
        if data is not None:
            a.setData(data)
        a.triggered.connect(lambda _c=False, f=slot: f())
        menu.addAction(a)
        self._menu_objs.append(a)
        return a

    def _build_menu(self):
        """Menueleiste (bei Sprachwechsel komplett neu aufgebaut)."""
        t = cfs_lang.t
        mb = self.menuBar()
        for obj in getattr(self, "_menu_objs", []):
            obj.deleteLater()
        self._menu_objs = []
        for m in mb.findChildren(QMenu):
            m.deleteLater()
        mb.clear()
        m = mb.addMenu(t("menu_file"))
        self._act(m, "new_game", self.new_game)
        self._act(m, "new_random", self.new_random_dialog)
        m.addSeparator()
        self._act(m, "load_position", self.load_pos)
        self._act(m, "save_position", self.save_pos)
        m.addSeparator()
        self._act(m, "quick_save", self.quick_save, acc="F3")
        self._act(m, "quick_load", self.quick_load, acc="F4")
        m.addSeparator()
        self._act(m, "quit", self.close)

        m = mb.addMenu(t("menu_view"))
        self.act_ghost = self._act(m, "ghost_stone", self.toggle_ghost, checkable=True, checked=self.ghost)
        self.act_anim = self._act(m, "drop_animation", self.toggle_anim, checkable=True, checked=self.anim)
        self.act_show = self._act(m, "show_last_move", self.toggle_show_last, checkable=True,
                                  checked=self.show_last)
        m.addSeparator()
        self.act_stand = self._act(m, "score_onoff", self.toggle_stand_menu, checkable=True,
                                   checked=self.stand.enabled)
        self._act(m, "score_reset", self._stand_reset)

        m = mb.addMenu(t("menu_settings"))
        self.menu_settings = m
        dm = m.addMenu(t("computer_level"))
        self.level_group = QActionGroup(self)
        self._menu_objs.append(self.level_group)
        self.level_actions = {}
        for key in levels.STUFEN_ORDER:
            self.level_actions[key] = self._act(
                dm, None, lambda k=key: self.switch_depth(k), checkable=True,
                checked=(key == self.level), group=self.level_group, data=key,
                label=levels.level_label(key))
        m.addSeparator()
        self.mode_group = QActionGroup(self)
        self._menu_objs.append(self.mode_group)
        self.mode_actions = {
            MODE_COMPUTER: self._act(m, "human_computer", self._select_engine, checkable=True,
                                     group=self.mode_group),
            MODE_TWO: self._act(m, "two_player", self.toggle_two_player, checkable=True,
                                group=self.mode_group),
            MODE_SELFPLAY: self._act(m, "selfplay", self._select_selfplay, checkable=True,
                                     group=self.mode_group),
        }
        self._sync_mode_radio()
        self._act(m, "match", self.match_dialog)
        self._act(m, "stop_autoplay", self.stop)
        m.addSeparator()
        self._act(m, "prev_set", lambda: self.cycle_set(-1), acc=t("acc_pgup"))
        self._act(m, "next_set", lambda: self.cycle_set(+1), acc=t("acc_pgdn"))
        m.addSeparator()
        self.set_group = QActionGroup(self)
        self._menu_objs.append(self.set_group)
        self.set_actions = {}
        for s in sets.set_menu_order(self.raw):
            if s not in sets._MENU_SETS:
                continue
            self.set_actions[s] = self._act(
                m, None, lambda n=s: self.switch_set(n), checkable=True,
                checked=(s == self.set_no), group=self.set_group, data=s,
                label=cfs_lang.tf("set_menu_item", no=s, name=sets.set_display_name(s)))

        m = mb.addMenu(t("menu_commands"))
        self._act(m, "first_move", self.goto_first, acc=t("acc_up"))
        self._act(m, "move_back", self.undo, acc=t("acc_left"))
        self._act(m, "move_forward", self.redo, acc=t("acc_right"))
        self._act(m, "last_move", self.goto_last, acc=t("acc_down"))
        m.addSeparator()
        self._act(m, "engine_move", self.engine_move, acc="F5")
        self._act(m, "score_all", self.toggle_scores, acc="F6")
        self._act(m, "permanent_analysis", self.toggle_auto_analyze_btn, acc="F7")

        m = mb.addMenu(t("menu_help"))
        self._act(m, "help_contents", self.show_help, acc="F1")
        self._act(m, "help_info", self.show_info)
        m.addSeparator()
        lm = m.addMenu(t("lang_menu"))
        self.lang_group = QActionGroup(self)
        self._menu_objs.append(self.lang_group)
        self.lang_actions = {}
        for code in cfs_lang.LANG_ORDER:
            self.lang_actions[code] = self._act(
                lm, cfs_lang.LANG_LABEL_KEY[code], lambda c=code: self.switch_lang(c),
                checkable=True, checked=(code == cfs_lang.LANG), group=self.lang_group, data=code)

    def _build_shortcuts(self):
        """Brett-Tasten wirken nur im Hauptfenster (nicht in Dialogen)."""
        def sc(seq, fn, ctx=Qt.ShortcutContext.WindowShortcut):
            s = QShortcut(QKeySequence(seq), self)
            s.setContext(ctx)
            s.setAutoRepeat(True)
            s.activated.connect(fn)
            return s
        self._shortcuts = []
        for i in range(COLS):
            self._shortcuts.append(sc(str(i + 1), lambda c=i: self.human_move(c)))
        for seq, fn in (("Left", self.undo), ("Right", self.redo),
                        ("Up", self.goto_first), ("Down", self.goto_last),
                        ("F3", self.quick_save), ("F4", self.quick_load),
                        ("F5", self.engine_move), ("F6", self.toggle_scores),
                        ("F7", self.toggle_auto_analyze_btn),
                        ("PgUp", lambda: self.cycle_set(-1)),
                        ("PgDown", lambda: self.cycle_set(+1)),
                        ("F10", lambda: None)):
            self._shortcuts.append(sc(seq, fn))
        # F1 wirkt wie in der Tk-Version auch in Dialogen (bind_all).
        self._shortcuts.append(sc("F1", self.show_help, Qt.ShortcutContext.ApplicationShortcut))

    def _sync_mode_radio(self):
        a = getattr(self, "mode_actions", {}).get(self.mode)
        if a is not None:
            a.setChecked(True)

    def _set_mode(self, mode):
        self.mode = mode
        self._sync_mode_radio()

    def _sync_level_radio(self):
        a = getattr(self, "level_actions", {}).get(self.level)
        if a is not None:
            a.setChecked(True)

    # =====================================================================
    # Sprache
    # =====================================================================
    def switch_lang(self, code):
        if cfs_lang.set_lang(code):
            cfs_lang.save_start_lang(code)
        app = QApplication.instance()
        if hasattr(app, "install_qt_translator"):
            app.install_qt_translator(cfs_lang.LANG)
        self._relabel_all()

    def _relabel_all(self):
        t = cfs_lang.t
        self._build_menu()
        for b, key in zip(self.bar_buttons, BAR_KEYS):
            b.setText(t(key))
        self.turn_box.setTitle(t("info_turn"))
        self.info_box.setTitle(t("info_box"))
        self.stand_box.setTitle(t("score_box"))
        for key, lab in self.info_labels.items():
            lab.setText(t(key) + ":")
        self.stand_toggle_btn.setText(t("score_on"))
        self.stand_reset_btn.setText(t("score_reset_btn"))
        self._apply_panel_width()
        self._update_turn()
        self.set_info("info_level", self._display_stufe_label())
        if self.stand.enabled:
            self._stand_show()
        if self.status_text() in {cfs_lang.t("status_ready", c) for c in cfs_lang.STRINGS}:
            self.set_status(t("status_ready"))

    # =====================================================================
    # Brett-Darstellung
    # =====================================================================
    def draw(self):
        self.canvas.update()

    def set_hover(self, col):
        if col != self.hover_col:
            self.hover_col = col
            if not self._anim_running:
                self.draw()

    def _on_canvas_click(self, col):
        if self.thinking or self._anim_running:
            return
        self.human_move(col)

    def _update_turn(self):
        stone = "yellow" if self.game.current_player_no() == 1 else "red"
        size = max(16, min(40, int(round(24 * self.zoom))))
        try:
            self.turn_icon.setPixmap(self.tiles.stone(self.set_no, stone, size))
        except Exception:
            pass
        self.turn_text.setText(self.current_player_label())

    def _set_scores(self, mapping):
        self.last_scores = mapping
        self.draw()

    def _clear_scores(self, silent=False):
        m = {}
        for c in range(COLS):
            if self.board.is_legal_move(c):
                m[c] = (str(c + 1), "", "#d9d9d9")
            else:
                m[c] = ("X", "", "#a0a0a0")
        self._set_scores(m)
        if silent:
            return
        for key in ("info_value", "info_depth", "info_nodes", "info_time",
                    "info_nodes_per_sec", "info_book"):
            self.set_info(key, DASH)
        self.set_info("info_level", self._stufe_label())

    def drop_animation(self, col, stone, done):
        self._anim_running = True
        self._anim_step(col, stone, done, 0)

    def _anim_step(self, col, stone, done, row):
        target_top = ROWS - self.board.get_column_height(col)
        if row >= target_top:
            self._anim_running = False
            self._anim_next = None
            self.falling = None
            self.refresh()
            done()
            return
        self.falling = (col, row * self._cell, stone)
        self.draw()
        self._anim_next = lambda: self._anim_step(col, stone, done, row + 1)
        self._anim_timer.start(16)

    def _cancel_anim(self):
        self._anim_timer.stop()
        self._anim_next = None
        self._anim_running = False
        self.falling = None

    # =====================================================================
    # Stufen / Identitaeten
    # =====================================================================
    def _stufe_key(self):
        return "mensch" if self.two_player else levels.normalize_key(self.level)

    def _stufe_label(self):
        return levels.stufe_label_for(self.level)

    def _match_mode(self):
        return self.match is not None and self.match.running

    def _match_side_stufe(self):
        return self.match.side_stufe(len(self.history))

    def _match_human_turn(self):
        return self._match_mode() and self._match_side_stufe() == "mensch"

    def _valid_match_stufe(self, key):
        return key == "mensch" or key in levels.COMPUTER_KEYS

    def _display_stufe_label(self):
        if self._match_mode():
            return levels.stufe_label_for(self._match_side_stufe())
        if self._valid_match_stufe(self.match_stufe):
            return levels.stufe_label_for(self.match_stufe)
        return self._stufe_label()

    def _move_stufe(self):
        """(key, patzerquote, s, w) fuer den gerade zu spielenden Zug."""
        if self._match_mode():
            return levels.stufen_werte(self._match_side_stufe())
        if self._valid_match_stufe(self.match_stufe):
            return levels.stufen_werte(self.match_stufe)
        return levels.stufen_werte(self._stufe_key())

    def _selfplay_mode(self):
        return self.selfplay or self.mode == MODE_SELFPLAY

    def current_player_label(self):
        """Wer ist am Zug? Match-Seite, Mensch, oder Stufe mit (p,s,w)."""
        if self._match_mode():
            return levels.stufe_label_for(self._match_side_stufe(), mit_psw=True)
        if self.two_player:
            return cfs_lang.t("level_human")
        if self._selfplay_mode():
            return levels.stufe_label_for(self._stufe_key(), mit_psw=True)
        n = len(self.history)
        if (n % 2 == 0) == bool(self.human_first):
            return cfs_lang.t("level_human")
        return levels.stufe_label_for(self._stufe_key(), mit_psw=True)

    # =====================================================================
    # Zuege
    # =====================================================================
    def human_move(self, col):
        if self._anim_running:
            return
        if self.thinking:
            self.set_status(cfs_lang.t("status_wait_thinking"))
            return
        if self._match_mode():
            if not self._match_human_turn():
                self.set_status(cfs_lang.t("status_match_running"))
                return
        elif self._selfplay_mode():
            self.set_status(cfs_lang.t("status_selfplay_running"))
            return
        if self.board.is_game_over():
            self.set_status(cfs_lang.t("status_game_over_new"))
            return
        if not self.board.is_legal_move(col):
            self.set_status(cfs_lang.tf("status_column_full", col=col + 1))
            return
        stone = self.game.stone_to_move()
        self.game.play(col)
        if self.anim:
            self.drop_animation(col, stone, self.after_human)
        else:
            self.refresh()
            self.after_human()

    def after_human(self):
        if self.board.is_game_over():
            self.finish_info()
            if self._match_mode():
                self._match_finish_game()
                return
            if not self.two_player and not self._selfplay_mode():
                self._stand_book_normal(human_won_normal(
                    self.board.winner(), len(self.history), self.human_first))
            return
        if self._selfplay_mode():
            self.engine_move()
            return
        if self._match_mode():
            side = self._match_side_stufe()
            if side != "mensch":
                self.engine_move(stufe=side)
            return
        if not self.two_player and self.mode == MODE_COMPUTER:
            self.engine_move()

    def engine_move(self, stufe=None):
        """Computer-Zug anstossen. stufe (optional) gilt nur fuer diesen Zug
        (Match). Normalmodus bei leerem Brett: Computer beginnt (Mensch Rot)."""
        if self.thinking or self.board.is_game_over() or self._anim_running:
            return
        if (not self._match_mode() and not self.two_player
                and not self._selfplay_mode() and not self.history):
            self.human_first = False
        self.thinking = True
        self.cancel = False
        self.match_stufe = stufe if (stufe and self._valid_match_stufe(stufe)) else None
        match_mode = self._match_mode()
        blind = match_mode and self.match.blind
        if not match_mode:
            self.set_status(cfs_lang.t("status_thinking"))
        if self._valid_match_stufe(self.match_stufe):
            stufe_txt = levels.stufe_label_for(self.match_stufe)
        else:
            stufe_txt = self._stufe_label()
        args = (self.game.copy_board(), list(self.history), self._move_stufe(),
                blind, self.ana_seq, stufe_txt, match_mode)
        threading.Thread(target=self._engine_thread, args=args, daemon=True).start()

    def _engine_thread(self, board, snap, stufe, blind, snap_seq, stufe_txt, match_mode):
        t0 = time.time()

        def prog(depth, scores, nodes, dt):
            if snap_seq != self.ana_seq or not scores:
                return
            if match_mode and blind:
                return
            if match_mode:
                self._safe_after(0, lambda: self.set_info("info_level", stufe_txt))
                return
            label = cfs_lang.t("depth_full") if depth == -1 else str(depth)
            kn = cfs_lang.fmt_thousands(nodes)
            ms = max(1, int(round(dt * 1000)))
            kns = eng.kns_text(nodes, dt)
            self._safe_after(0, lambda: self._engine_prog_ui(label, kn, ms, kns, stufe_txt))

        try:
            col, score, _dist, nodes = self.engine.pick_move(
                board, stufe, on_progress=prog, abort=lambda: self.cancel, keep_tt=blind)
        except Exception as e:
            traceback.print_exc()
            err = str(e)
            self._safe_after(0, lambda: self._engine_failed(err))
            return
        dt = time.time() - t0
        self._safe_after(0, lambda: self._engine_done(col, dt, nodes, score, snap))

    def _engine_prog_ui(self, label, kn_txt, ms, kns_txt, stufe_txt):
        self.set_info("info_depth", f"{label}...")
        self.set_info("info_nodes", kn_txt)
        self.set_info("info_time", f"{ms} ms")
        self.set_info("info_nodes_per_sec", kns_txt)
        self.set_info("info_level", stufe_txt)
        if not self._match_mode():
            self.set_status(cfs_lang.t("status_thinking"))

    def _engine_failed(self, err):
        self.thinking = False
        if self._match_mode():
            self._match_cancelled()
            return
        self.set_status(cfs_lang.tf("status_computer_error", err=err))

    def _engine_done(self, col, dt, nodes=0, score=None, snap=None):
        self.thinking = False
        if self.cancel:
            if self._match_mode():
                self._match_cancelled()
            else:
                self.set_status(cfs_lang.t("status_aborted"))
            return
        if snap is not None and list(self.history) != list(snap):
            self.set_status(cfs_lang.t("status_discarded"))
            self.refresh()
            return
        stone = self.game.stone_to_move()
        ml_played = self.engine.moves_left(self.board, score) if score is not None else None
        self.game.play(col)
        self.move_times.append(dt)
        if self._match_mode() and self.match.blind:
            self.after_engine(col, dt, nodes, score)
            return
        fast = self._match_mode() and self.match.delay_ms() == 0
        if self.anim and not fast:
            self.drop_animation(col, stone,
                                lambda: self.after_engine_anim(col, dt, nodes, score, ml_played))
        else:
            self._refresh_after_engine(col, nodes, score, ml_played)
            self.after_engine(col, dt, nodes, score)

    def after_engine_anim(self, col, dt, nodes=0, score=None, ml_played=None):
        dt0 = self.move_times[-1] if self.move_times else dt
        self._show_engine_info(col, nodes, dt0, score, ml_played)
        self.after_engine(col, dt, nodes, score)

    def after_engine(self, col, dt, nodes=0, score=None):
        if self._match_mode():
            self._match_after_move(col, dt)
            return
        self.set_status(cfs_lang.tf("status_computer_move", col=col + 1, sec=f"{dt:.2f}"))
        if self.board.is_game_over():
            self.finish_info()
            if not self.two_player and not self._selfplay_mode():
                self._stand_book_normal(human_won_normal(
                    self.board.winner(), len(self.history), self.human_first))
            if self._selfplay_mode():
                self._selfplay_stop()
            return
        if self._selfplay_mode():
            self._safe_after(350, self._selfplay_next)

    def _refresh_after_engine(self, col, nodes, score=None, ml_played=None):
        dt = self.move_times[-1] if self.move_times else 0.0
        self._show_engine_info(col, nodes, dt, score, ml_played)
        self.draw()
        self._update_turn()
        self.set_info("info_move", str(len(self.history) + 1))
        self.set_info("info_level", self._display_stufe_label())
        if self.board.is_game_over():
            self.finish_info()
            return
        self.scores_visible = False
        self._clear_scores(silent=True)
        # Wie der Animationsweg (refresh): Dauer-Analyse auch ohne Animation.
        self.schedule_auto_analyze()

    def _show_engine_info(self, col, nodes, dt, score=None, ml_played=None):
        n = len(self.history)
        if score is None:
            self.set_info("info_value", DASH)
        else:
            ml = ml_played if ml_played is not None else self.engine.moves_left(self.board, int(score))
            self.set_info("info_value", eng.value_text(int(score), ml, n % 2 == 1))
        self.set_info("info_depth", self.engine.plies_text(n))
        self.set_info("info_nodes", cfs_lang.fmt_thousands(nodes))
        self.set_info("info_time", f"{max(1, int(round(dt * 1000)))} ms")
        self.set_info("info_nodes_per_sec", eng.kns_text(nodes, dt))
        self.set_info("info_book", self.engine.book_text(n))

    def stop(self):
        """Stop: Engine-Zug, Selbstspiel, Match, Analyse und Zufallssuche.
        Ein noch rechnender Thread laeuft zu Ende, sein Ergebnis wird verworfen."""
        self.cancel = True
        self._selfplay_stop()
        self._match_stop(cancelled=True)
        self.ana_seq += 1
        self.ana_pending = None
        self.ana_busy = False
        self.ana_running_snap = None
        if self.rand_job:
            self.rand_job["stop"] = True
        self.set_status(cfs_lang.t("status_stopped"))

    def _nav_blocked(self):
        if self._anim_running:
            return True
        if self.thinking:
            self.set_status(cfs_lang.t("status_wait_thinking"))
            return True
        if self._match_mode():
            self.set_status(cfs_lang.t("status_match_running"))
            return True
        if self._selfplay_mode():
            self.set_status(cfs_lang.t("status_selfplay_running_stop"))
            return True
        return False

    def undo(self):
        if not self._nav_blocked() and self.game.undo():
            self.refresh()

    def redo(self):
        if not self._nav_blocked() and self.game.redo():
            self.refresh()

    def goto_first(self):
        if not self._nav_blocked():
            self.game.goto_first()
            self.refresh()

    def goto_last(self):
        if not self._nav_blocked():
            self.game.goto_last()
            self.refresh()

    def new_game(self):
        self.stop()
        self._selfplay_stop()
        self.human_first = True
        if self.match is not None:
            self.match = None
            self.match_stufe = None
            self._match_refresh_win()
        self._cancel_anim()
        self.game.reset()
        self.move_times.clear()
        # TT nur zuruecksetzen, wenn kein Worker die Engine gerade haelt.
        if self.engine.lock.acquire(blocking=False):
            try:
                self.engine.agent.reset_transposition_table()
                self.engine.agent.reset_node_counter()
            finally:
                self.engine.lock.release()
        self.set_status(cfs_lang.t("status_new_game"))
        self.refresh()

    # =====================================================================
    # Zufallsstellung
    # =====================================================================
    def new_random_dialog(self):
        if self.thinking:
            return
        dlg = RandomDialog(self)
        if dlg.exec() != RandomDialog.DialogCode.Accepted or not dlg.result_value:
            return
        n, wunsch = dlg.result_value
        self.start_random(n, wunsch)

    def start_random(self, n, wunsch):
        job = {"stop": False}
        self.rand_job = job
        self.set_status(cfs_lang.tf("status_search_random", n=n, wish=self._wish_label(wunsch)))
        threading.Thread(target=self._random_thread, args=(n, wunsch, job), daemon=True).start()

    @staticmethod
    def _wish_label(wunsch):
        key = {"Egal": "new_random_any", "Gewinn": "new_random_win",
               "Unentschieden": "new_random_draw", "Verlust": "new_random_loss"}.get(wunsch)
        return cfs_lang.t(key) if key else str(wunsch)

    def _random_thread(self, n, wunsch, job):
        seq = self.engine.random_position(n, wunsch, stop=lambda: job.get("stop"))
        if seq == "stopped":
            self._safe_after(0, lambda: self.set_status(cfs_lang.t("status_aborted")))
        elif seq is None:
            self._safe_after(0, lambda: self.set_status(cfs_lang.t("status_no_position_found")))
        else:
            self._safe_after(0, lambda: self._random_done(list(seq), wunsch, job))

    def _random_done(self, seq, wunsch, job=None):
        if job is not None and job.get("stop"):
            return
        self.new_game()
        self.game.set_moves(seq)
        self.human_first = (len(seq) % 2 == 0)
        self.rand_job = None
        self.set_status(cfs_lang.tf("status_random_done", n=len(seq), wish=self._wish_label(wunsch)))
        self.refresh(all_scores=True)

    # =====================================================================
    # Datei (.4gp)
    # =====================================================================
    def _file_filter(self, with_all=True):
        f = f"{cfs_lang.t('file_filter_c4')} (*.4gp)"
        if with_all:
            f += f";;{cfs_lang.t('file_filter_all')} (*)"
        return f

    def _remember_dir(self, path):
        self.settings["last_dir"] = os.path.dirname(os.path.abspath(path))
        self._save_settings()

    def ask_open_path(self):
        p, _f = QFileDialog.getOpenFileName(self, cfs_lang.t("file_open_title"),
                                            paths.start_dir(self.settings.get("last_dir")),
                                            self._file_filter(True))
        return p

    def ask_save_path(self):
        p, _f = QFileDialog.getSaveFileName(self, cfs_lang.t("file_save_title"),
                                            paths.start_dir(self.settings.get("last_dir")),
                                            self._file_filter(False))
        if p and not os.path.splitext(os.path.basename(p))[1]:
            p += ".4gp"
        return p

    def load_pos(self):
        if self.thinking:
            self.stop()
            self.set_status(cfs_lang.t("status_load_stopped_thinking"))
            return
        p = self.ask_open_path()
        if not p:
            return
        self.load_file(p)

    def load_file(self, p):
        try:
            self._load_moves(gm.read_4gp(p))
            self._remember_dir(p)
            self.set_status(cfs_lang.tf("status_loaded", path=os.path.basename(p)))
        except Exception as e:
            QMessageBox.critical(self, cfs_lang.t("error_title"), str(e))

    def save_pos(self):
        p = self.ask_save_path()
        if not p:
            return
        self.save_file(p)

    def save_file(self, p):
        try:
            gm.write_4gp(p, self.history)
            self._remember_dir(p)
            self.set_status(cfs_lang.tf("status_saved", path=os.path.basename(p)))
        except Exception as e:
            QMessageBox.critical(self, cfs_lang.t("error_title"), str(e))

    def quick_save(self):
        try:
            gm.write_4gp(paths.quicksave_path(), self.history)
            self.set_status(cfs_lang.tf("status_quick_saved", n=len(self.history)))
        except Exception as e:
            QMessageBox.critical(self, cfs_lang.t("title_quick_save"), str(e))

    def quick_load(self):
        if self.thinking:
            self.stop()
            self.set_status(cfs_lang.t("status_load_stopped_thinking"))
            return
        p = paths.quicksave_path()
        if not os.path.isfile(p):
            self.set_status(cfs_lang.t("status_no_quicksave"))
            return
        try:
            self._load_moves(gm.read_4gp(p))
            self.set_status(cfs_lang.tf("status_quick_loaded", name=os.path.basename(p)))
        except Exception as e:
            QMessageBox.critical(self, cfs_lang.t("title_quick_load"), str(e))

    def _load_moves(self, moves):
        self.new_game()
        self.game.set_moves(moves)
        self.human_first = (len(self.history) % 2 == 0)
        self.refresh(all_scores=self.scores_visible)

    def load_start_file(self, p):
        """Startargument: Stellung laden und sofort bewerten (wie Tk-__main__)."""
        try:
            self.game.set_moves(gm.read_4gp(p))
            self.refresh(all_scores=True)
        except Exception as e:
            print(cfs_lang.t("err_start_position"), e)

    # =====================================================================
    # Bewertung / Analyse
    # =====================================================================
    def toggle_scores(self):
        """F6: 1. Aufruf bewertet sofort, 2. Aufruf zurueck zu 1-7."""
        if self.scores_visible:
            self.scores_visible = False
            self.ana_seq += 1
            self.ana_pending = None
            self._clear_scores()
            self.set_status(cfs_lang.t("status_scores_off"))
        else:
            self.refresh(all_scores=True)

    def refresh(self, all_scores=False):
        self.draw()
        self._update_turn()
        self.set_info("info_move", str(len(self.history) + 1))
        self.set_info("info_level", self._display_stufe_label())
        if self.board.is_game_over():
            self.finish_info()
            return
        if all_scores and not self.thinking:
            # Synchron (wie Tk), iterativ statt Vollsuche.
            self.ana_seq += 1
            t0 = time.time()
            try:
                scores, nodes = self.engine.iterative_scores(self.game.copy_board())
            except Exception:
                scores, nodes = {}, 0
            dt = time.time() - t0
            if scores:
                self._show_scores(scores, nodes, dt)
            else:
                self.set_status(cfs_lang.t("status_eval_aborted"))
        else:
            self.scores_visible = False
            self._clear_scores()
            self.set_info("info_level", self._display_stufe_label())
            self.schedule_auto_analyze()

    def finish_info(self):
        w = self.board.winner()
        if w is None and not self.board.is_game_over():
            return
        if w in (None, 0):
            msg = cfs_lang.t("msg_draw")
        else:
            msg = cfs_lang.tf("msg_wins", who=cfs_lang.t(
                "color_red" if int(w) == 2 else "color_yellow"))
        self.set_status(cfs_lang.tf("status_game_end", msg=msg))
        self.set_info("info_value", msg)

    def schedule_auto_analyze(self):
        """Hintergrund-Analyse; neueste Stellung gewinnt."""
        if not self.auto_analyze or self.board.is_game_over():
            return
        snap = list(self.history)
        if self.ana_busy:
            if snap == self.ana_running_snap:
                return
            self.ana_seq += 1
            self.ana_pending = (self.ana_seq, snap)
            return
        self.ana_seq += 1
        self._start_analysis(self.ana_seq, snap)

    def _start_analysis(self, seq, snap):
        self.ana_running_snap = list(snap)
        self.ana_busy = True
        threading.Thread(target=self._auto_analyze_thread, args=(seq, snap), daemon=True).start()

    def _auto_analyze_thread(self, seq, snap):
        t0 = time.time()
        last = [None]

        def prog(depth, scores, nodes, dt):
            if seq != self.ana_seq:
                return
            last[0] = (dict(scores), nodes, dt)
            s = dict(scores)
            self._safe_after(0, lambda: self._show_scores_live(s, nodes, dt, depth, seq, snap))

        try:
            scores, nodes = self.engine.iterative_scores(
                gm.board_from_moves(snap), on_progress=prog, abort=lambda: seq != self.ana_seq)
        except Exception as e:
            err = str(e)
            self._safe_after(0, lambda: self._auto_analyze_fail(seq, err))
            return
        if not scores and last[0] is not None:
            scores, nodes, _t = last[0]
        dt = time.time() - t0
        sc = dict(scores)
        self._safe_after(0, lambda: self._auto_analyze_done(seq, list(snap), sc, nodes, dt))

    def _auto_analyze_fail(self, seq, err):
        self.ana_busy = False
        self.ana_running_snap = None
        if seq == self.ana_seq:
            self.set_status(cfs_lang.tf("status_analysis_error", err=err))
        self._drain_pending()

    def _auto_analyze_done(self, seq, snap, scores, nodes, dt):
        self.ana_busy = False
        self.ana_running_snap = None
        if seq != self.ana_seq or list(self.history) != snap or not self.auto_analyze or not scores:
            self._drain_pending()
            return
        self._show_scores(scores, nodes, dt)
        best = max(scores, key=scores.get)
        self.set_status(cfs_lang.tf("status_analysis_done", col=best + 1,
                                    score=scores[best], sec=f"{dt:.2f}"))
        self._drain_pending()

    def _drain_pending(self):
        if self.ana_pending is None:
            return
        seq, snap = self.ana_pending
        self.ana_pending = None
        if seq != self.ana_seq or list(self.history) != snap or self.board.is_game_over():
            return
        self.cancel = False
        self._start_analysis(seq, snap)

    def _show_scores_live(self, scores, nodes, dt, depth, seq, snap):
        if seq != self.ana_seq or list(self.history) != snap:
            return
        if not self.auto_analyze or self.board.is_game_over():
            return
        self._show_scores(scores, nodes, dt)
        label = cfs_lang.t("depth_full") if depth == -1 else str(depth)
        self.set_info("info_depth", f"{label}...")

    def _show_scores(self, scores, nodes, dt):
        """Bewertung farbig in der Wertungszeile + Info-Feld."""
        if not scores:
            return
        from cfs_qt.board import C_DRAW, C_LOSS, C_WIN
        self._update_turn()
        self.scores_visible = True
        m = {}
        for c in range(COLS):
            if c in scores:
                s = scores[c]
                ml = self.engine.moves_left(self.board, s)
                if s > 0:
                    top, bg = "+", C_WIN
                elif s == 0:
                    top, bg = "=", C_DRAW
                else:
                    top, bg = "-", C_LOSS
                m[c] = (top, str(ml), bg)
            else:
                m[c] = ("X", "", "#a0a0a0")
        self._set_scores(m)
        best = max(scores, key=scores.get)
        bs = scores[best]
        mover_yellow = len(self.history) % 2 == 0
        self.set_info("info_value", eng.value_text(bs, self.engine.moves_left(self.board, bs),
                                                   mover_yellow))
        n = len(self.history)
        self.set_info("info_depth", self.engine.plies_text(n))
        self.set_info("info_nodes", cfs_lang.fmt_thousands(nodes))
        self.set_info("info_time", f"{max(1, int(round(dt * 1000)))} ms")
        self.set_info("info_nodes_per_sec", eng.kns_text(nodes, dt))
        self.set_info("info_book", self.engine.book_text(n))

    def _set_auto_analyze(self, on, silent=False):
        self.auto_analyze = bool(on)
        if not on:
            self.ana_seq += 1
            self.ana_pending = None
            self.scores_visible = False
            self._clear_scores()
            if not silent:
                self.set_status(cfs_lang.t("status_autoanalysis_off"))
            return
        if not silent:
            self.set_status(cfs_lang.t("status_autoanalysis_on"))
        self.schedule_auto_analyze()

    def toggle_auto_analyze_btn(self):
        self._set_auto_analyze(not self.auto_analyze)

    # =====================================================================
    # Einstellungen: Stufe, Modus
    # =====================================================================
    def _apply_stufe(self):
        if self.level not in levels.STUFEN_ORDER:
            self.level = "perfekt"
        self._sync_level_radio()
        self.set_info("info_level", self._stufe_label())
        self._save_settings()

    def switch_depth(self, key=None):
        """Computer-Stufe waehlen; im Selbstspiel bleibt sie Perfekt.
        Stufenwechsel setzt den Spielstand der neuen Stufe auf 0-0."""
        if key is not None:
            self.level = key
        if self._selfplay_mode():
            self.level = "perfekt"
        self._apply_stufe()
        pair = self.stand.reset_to(self._stufe_key())
        if pair is not None:
            self._stand_show(pair)
        self.act_stand.setChecked(self.stand.enabled)
        if self._selfplay_mode():
            self.set_status(cfs_lang.t("status_selfplay_fixed"))
        else:
            self.set_status(cfs_lang.tf("status_hc_level", label=self._stufe_label()))
        self.refresh(all_scores=self.scores_visible)

    def _select_engine(self):
        self._selfplay_stop()
        self.two_player = False
        self._set_mode(MODE_COMPUTER)
        self.set_status(cfs_lang.tf("status_hc_mode", label=self._stufe_label()))
        if not self.board.is_game_over() and len(self.history) % 2 == 1:
            self.engine_move()
        else:
            self.refresh(all_scores=self.scores_visible)

    def toggle_two_player(self):
        self._selfplay_stop()
        self.two_player = True
        self._set_mode(MODE_TWO)
        self.set_status(cfs_lang.t("status_two_player"))
        self.schedule_auto_analyze()

    def _select_selfplay(self):
        self.two_player = False
        self.selfplay = True
        self._set_mode(MODE_SELFPLAY)
        self.level = "perfekt"
        self._apply_stufe()
        self.set_status(cfs_lang.t("status_selfplay_playing"))
        self.refresh(all_scores=self.scores_visible)
        if not self.board.is_game_over() and not self.thinking:
            self.engine_move()

    def _selfplay_stop(self):
        self.selfplay = False
        if self.mode == MODE_SELFPLAY:
            self._set_mode(MODE_COMPUTER)

    def _selfplay_next(self):
        if not self._selfplay_mode():
            return
        if self.board.is_game_over() or self.thinking:
            if self.board.is_game_over():
                self._selfplay_stop()
            return
        if self.level != "perfekt":
            self.level = "perfekt"
            self._apply_stufe()
        self.engine_move()

    # =====================================================================
    # Match
    # =====================================================================
    def match_dialog(self):
        if self._selfplay_mode() or self.thinking:
            self.set_status(cfs_lang.t("status_stop_before_match"))
            return
        if self._match_win is not None:
            self._match_win.bring_to_front()
            return
        self._match_win = MatchDialog(self)
        self._match_win.show()

    def _match_win_closed(self, dlg=None):
        if dlg is None or self._match_win is dlg:
            self._match_win = None

    def _match_refresh_win(self):
        if self._match_win is not None:
            try:
                self._match_win.refresh()
            except RuntimeError:
                self._match_win = None

    def _match_timer_start(self, ms, fn):
        self._match_timer.stop()
        self._match_timer_fn = fn
        self._match_timer.start(max(0, int(ms)))

    def _match_timer_cancel(self):
        self._match_timer.stop()
        self._match_timer_fn = None

    def _match_start(self, gelb, rot, spiele, wechsel, schnell=False, blind=False):
        self._selfplay_stop()
        self.two_player = False
        self._set_mode(MODE_COMPUTER)
        self.cancel = False
        self.ana_seq += 1
        self.ana_pending = None
        self.match = Match(gelb, rot, spiele, wechsel, schnell=schnell, blind=blind)
        self.match_stufe = None
        self._new_match_game()
        self._match_refresh_win()

    def _new_match_game(self):
        self._cancel_anim()
        self.game.reset()
        self.move_times.clear()
        self.refresh()
        self.set_status(self.match.status_line())
        self._match_refresh_win()
        self._match_trigger_next()

    def _match_trigger_next(self):
        if not self._match_mode() or self.board.is_game_over() or self.thinking:
            return
        self._match_timer_start(self.match.delay_ms(), self._match_do_move)

    def _match_do_move(self):
        self._match_timer_fn = None
        if not self._match_mode() or self.board.is_game_over() or self.thinking:
            return
        side = self._match_side_stufe()
        if side == "mensch":
            return  # Mensch-Seite: auf Klick/Taste warten
        self.engine_move(stufe=side)

    def _match_after_move(self, col, dt):
        if self.board.is_game_over():
            self.finish_info()
            self._match_finish_game()
            return
        if self._match_mode():
            if self.match.delay_ms() == 0:
                if self.thinking or self._match_side_stufe() == "mensch":
                    return
                self.engine_move(stufe=self._match_side_stufe())
                return
            self._safe_after(self.match.delay_ms(), self._match_trigger_next)

    def _match_finish_game(self):
        m = self.match
        sieger = m.record_result(self.board.winner())
        pair = self.stand.add_match_result(m.gelb, m.rot, sieger)
        if pair is not None:
            self._stand_show(pair)
        if not m.advance():
            self.match_stufe = None
            self.finish_info()
            # Nach finish_info, damit das Matchergebnis stehen bleibt.
            self.set_status(cfs_lang.tf("match_ended_status", res=m.result_text()))
            self._match_refresh_win()
            if self._match_win is not None:
                self._match_win.bring_to_front()
            return
        if m.pause_between_games():
            self.set_status(self.status_text() + cfs_lang.t("match_next_in"))
            self._match_timer_start(3000, self._match_next_game)
            return
        self._new_match_game()

    def _match_next_game(self):
        self._match_timer_fn = None
        if self._match_mode():
            self._new_match_game()

    def _match_cancelled(self):
        m = self.match
        if m is not None:
            m.stop(cancelled=True)
        self.match_stufe = None
        self._match_timer_cancel()
        self.set_status(cfs_lang.tf("match_stopped_status",
                                    res=m.result_text() if m is not None else ""))
        self._match_refresh_win()

    def _match_stop(self, cancelled=False):
        m = self.match
        if m is None or m.fertig:
            return
        m.stop(cancelled=cancelled)
        self.match_stufe = None
        self._match_timer_cancel()
        if cancelled:
            self.set_status(cfs_lang.tf("match_stopped_status", res=m.result_text()))
        self._match_refresh_win()

    # =====================================================================
    # Spielstand
    # =====================================================================
    def _stand_show(self, pair=None):
        head, big, sub, elo = self.stand.display(pair)
        self.stand_head.setText(head)
        self.stand_big.setText(big)
        self.stand_sub.setText(sub)
        self.stand_elo.setText(elo)

    def _stand_book_normal(self, sieger_mensch):
        pair = self.stand.book_normal(self._stufe_key(), sieger_mensch)
        if pair is not None:
            self._stand_show(pair)

    def _stand_toggle(self):
        self.stand.toggle(self._stufe_key())
        self.act_stand.setChecked(self.stand.enabled)
        self._stand_show()

    def toggle_stand_menu(self):
        want = self.act_stand.isChecked()
        if want != self.stand.enabled:
            self._stand_toggle()
        else:
            self.act_stand.setChecked(self.stand.enabled)

    def _stand_reset(self):
        pair = self.stand.reset(self._stufe_key())
        self._stand_show(pair)

    # =====================================================================
    # Sets / Ansicht
    # =====================================================================
    def switch_set(self, no):
        if no not in self.raw:
            return
        self.set_no = no
        a = self.set_actions.get(no)
        if a is not None:
            a.setChecked(True)
        self._do_layout()
        self.draw()
        self._update_turn()
        self.set_status(cfs_lang.tf("status_set_changed", no=no, name=sets.set_display_name(no)))
        self._save_settings()

    def cycle_set(self, direction=+1):
        ids = [s for s in sets.set_menu_order(self.raw) if s in sets._MENU_SETS]
        if not ids:
            return
        i = ids.index(self.set_no) if self.set_no in ids else 0
        self.switch_set(ids[(i + direction) % len(ids)])

    def toggle_show_last(self):
        self.show_last = self.act_show.isChecked()
        self.draw()
        self._save_settings()

    def toggle_ghost(self):
        self.ghost = self.act_ghost.isChecked()
        self.draw()
        self._save_settings()

    def toggle_anim(self):
        self.anim = self.act_anim.isChecked()
        self._save_settings()

    # =====================================================================
    # Hilfe / Info
    # =====================================================================
    def _stone_images(self):
        return {name: self.tiles.stone_image(self.set_no, name, 22) for name in ("yellow", "red")}

    def show_help(self):
        if self._help_win is not None and self._help_win.lang == cfs_lang.LANG:
            self._help_win.show()
            self._help_win.raise_()
            self._help_win.activateWindow()
            return
        if self._help_win is not None:
            self._help_win.close()
        self._help_win = HelpDialog(self, cfs_lang.LANG, self._stone_images())
        self._help_win.show()

    def show_info(self):
        if self._info_win is not None and self._info_win.lang == cfs_lang.LANG:
            self._info_win.show()
            self._info_win.raise_()
            self._info_win.activateWindow()
            return
        if self._info_win is not None:
            self._info_win.close()
        self._info_win = InfoDialog(self, cfs_lang.LANG)
        self._info_win.show()

    # =====================================================================
    # Schliessen
    # =====================================================================
    def closeEvent(self, ev):
        self._closed = True
        self.cancel = True
        self.ana_seq += 1
        self.ana_pending = None
        if isinstance(self.rand_job, dict):
            self.rand_job["stop"] = True
        self._anim_timer.stop()
        self._match_timer.stop()
        self._save_settings()
        for w in (self._match_win, self._help_win, self._info_win):
            if w is not None:
                try:
                    w.close()
                except RuntimeError:
                    pass
        super().closeEvent(ev)
