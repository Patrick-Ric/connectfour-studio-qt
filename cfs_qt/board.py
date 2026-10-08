"""Spielfeld als QWidget mit QPainter (Brett + Wertungszeile).

Ersetzt den Tk-Canvas: zeichnet die Kacheln des Stein-Sets, Ghost-Stein,
fallenden Stein, Letzter-Zug-Ring, Sieg-Doppelringe und die Wertungszeile
(44 px) pixelgenau unter den Spalten. Der Zustand kommt aus dem Hauptfenster
(BoardView-Protokoll: game, set_no, raw, tiles, show_last, ghost, hover_col,
falling, last_scores).
"""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from cfs_core.game import COLS, ROWS

SCORE_H = 44          # Hoehe der Wertungszeile (fest, nicht zoom-abhaengig)
SCORE_GAP = 4         # Klick-Luecke zwischen Brett und Wertungszeile
C_WIN = "#b8e6b8"     # gruen pastell: Gewinn
C_DRAW = "#fff3a0"    # gelb pastell: Unentschieden
C_LOSS = "#f5b8b8"    # rot pastell: Verlust
C_BASE = "#d9d9d9"    # Spaltennummern
C_FULL = "#a0a0a0"    # volle Spalte ('X')
BOARD_BG = "#1e3a8a"


class BoardCanvas(QWidget):
    columnClicked = Signal(int)
    hoverChanged = Signal(object)   # Spalte oder None
    setWheel = Signal(int)          # -1 = vorheriges Set, +1 = naechstes

    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.view = view
        self.cell = 77
        self._wheel_acc = 0
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    # ---------- Geometrie ----------
    def board_w(self):
        return COLS * self.cell

    def board_h(self):
        return ROWS * self.cell

    def canvas_h(self):
        return self.board_h() + SCORE_H

    def set_cell(self, cell):
        self.cell = max(8, int(cell))
        self.setFixedSize(self.board_w(), self.canvas_h())
        self.update()

    def col_from_x(self, x):
        col = int(x // self.cell)
        return col if 0 <= col < COLS else None

    # ---------- Maus ----------
    def mouseMoveEvent(self, ev):
        self.hoverChanged.emit(self.col_from_x(ev.position().x()))

    def leaveEvent(self, ev):
        self.hoverChanged.emit(None)

    def mousePressEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        y = ev.position().y()
        bh = self.board_h()
        if bh <= y < bh + SCORE_GAP:
            return  # Luecke zwischen Brett und Wertungszeile
        col = self.col_from_x(ev.position().x())
        if col is not None:
            self.columnClicked.emit(col)

    def wheelEvent(self, ev):
        # Mausrad ueber dem Brett: Rad hoch = vorheriges, runter = naechstes Set.
        self._wheel_acc += ev.angleDelta().y()
        while self._wheel_acc >= 120:
            self._wheel_acc -= 120
            self.setWheel.emit(-1)
        while self._wheel_acc <= -120:
            self._wheel_acc += 120
            self.setWheel.emit(+1)
        ev.accept()

    # ---------- Zeichnen ----------
    def paintEvent(self, ev):
        v = self.view
        p = QPainter(self)
        try:
            self._paint(p, v)
        finally:
            p.end()

    def _paint(self, p, v):
        cell = self.cell
        game = v.game
        raw = v.raw[v.set_no]
        tiles = v.tiles
        falling = v.falling
        p.fillRect(0, 0, self.board_w(), self.board_h(), QColor(BOARD_BG))
        arr = game.to_array()
        win = game.win_cells() if falling is None else set()
        last = game.last_move if (v.show_last and falling is None) else None
        hide = None
        if falling is not None:
            # Waehrend der Animation steht der Stein noch nicht im Ziel.
            col = falling[0]
            hide = (ROWS - game.column_height(col), col)
        back = tiles.tile(v.set_no, "back", cell)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for c in range(COLS):
            for row in range(ROWS):
                r_top = ROWS - 1 - row
                x0, y0 = c * cell, r_top * cell
                val = arr[c][row]
                if val == 0 or (r_top, c) == hide:
                    p.drawPixmap(x0, y0, back)
                    continue
                p.drawPixmap(x0, y0, tiles.tile(v.set_no, "yellow" if val == 1 else "red", cell))
                if (r_top, c) in win:
                    sr = raw.get("stone_r", 0.39)
                    wgreen = max(3, cell // 16)
                    pad = cell * (0.5 - sr) - 2 - wgreen // 2
                    self._ring(p, x0, y0, pad, "#00ff00", wgreen)
                    wwhite = max(1, cell // 40)
                    pad2 = cell * (0.5 - sr) + 1 + wwhite // 2
                    self._ring(p, x0, y0, pad2, "#ffffff", wwhite)
                elif last == (r_top, c):
                    sr = raw.get("stone_r_r" if val == 2 else "stone_r_y",
                                 raw.get("stone_r", 0.39))
                    wlast = max(2, cell // 25)
                    pad = cell * (0.5 - sr) - 2 - wlast // 2
                    self._ring(p, x0, y0, pad, "#ffffff", wlast)
        # Ghost-Stein (Vorschau) ueber der Zielspalte
        hc = v.hover_col
        if (v.ghost and hc is not None and falling is None
                and not game.is_game_over() and game.is_legal(hc)):
            stone = game.stone_to_move()
            r_top = ROWS - 1 - game.column_height(hc)
            p.drawPixmap(hc * cell, r_top * cell, tiles.tile(v.set_no, stone + "_ghost", cell))
        if falling is not None:
            col, ypix, stone = falling
            p.drawPixmap(col * cell, int(round(ypix)), tiles.tile(v.set_no, stone, cell))
        self._paint_scores(p, v)

    def _ring(self, p, x0, y0, pad, color, width):
        p.setPen(QPen(QColor(color), width))
        p.setBrush(Qt.BrushStyle.NoBrush)
        cell = self.cell
        p.drawEllipse(QRectF(x0 + pad, y0 + pad, cell - 2 * pad, cell - 2 * pad))

    def _paint_scores(self, p, v):
        """Wertungszeile: ohne Analyse Spaltennummern, mit Analyse oben
        +/=/- (fett) und unten die Steinzahl bis zum Ende."""
        cell = self.cell
        y0 = self.board_h()
        h = SCORE_H
        zoom = cell / 256.0
        f_big = QFont(self.font())
        f_big.setPointSize(max(9, min(16, int(round(13 * zoom)))))
        f_big.setBold(True)
        f_val = QFont(self.font())
        f_val.setPointSize(max(8, min(12, int(round(9 * zoom)))))
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        scores = v.last_scores
        for c in range(COLS):
            x0 = c * cell
            if scores is None:
                top, sub, bg = str(c + 1), "", C_BASE
            else:
                top, sub, bg = scores[c]
            p.fillRect(x0, y0, cell, h, QColor(bg))
            p.setPen(QPen(QColor("#888888"), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(x0, y0, cell - 1, h - 1)
            p.setPen(QColor("black"))
            if sub:
                p.setFont(f_big)
                self._center_text(p, x0 + cell / 2, y0 + h * 0.28, top)
                p.setFont(f_val)
                self._center_text(p, x0 + cell / 2, y0 + h * 0.72, sub)
            else:
                p.setFont(f_val)
                self._center_text(p, x0 + cell / 2, y0 + h / 2, top)

    @staticmethod
    def _center_text(p, cx, cy, text):
        fm = p.fontMetrics()
        w = fm.horizontalAdvance(text)
        base = cy + (fm.ascent() - fm.descent()) / 2
        p.drawText(QPointF(cx - w / 2, base), text)
