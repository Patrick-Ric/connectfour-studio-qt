"""Spielzustand (Brett, Verlauf, Zug vor/zurueck) und .4gp-Format.

BitBully: to_array()[spalte][zeile], Zeile 0 = unten;
0 = leer, 1 = Gelb (Anziehender), 2 = Rot (Nachziehender).
Bildkoordinaten (r_top, c): r_top 0 = oberste Reihe.
"""

import bitbully as bb

COLS, ROWS = 7, 6


# ---------- .4gp (Spalten-Notation) ----------
def parse_4gp(text):
    """Ziffernkette -> Spalten 0..6 (Fremdzeichen werden ignoriert)."""
    return [int(c) - 1 for c in text if c in "1234567"]


def format_4gp(history):
    """Spalten 0..6 -> Ziffernkette '4433221' (ohne Zeilenende)."""
    return "".join(str(m + 1) for m in history)


def read_4gp(path):
    with open(path, encoding="ascii", errors="ignore") as f:
        return parse_4gp(f.read().strip())


def write_4gp(path, history):
    with open(path, "w", encoding="ascii") as f:
        f.write(format_4gp(history))


def legal_prefix(moves):
    """Nur legale Zuege bis zum Partieende uebernehmen (wie _load_moves der
    Tk-Version: illegale Zuege werden uebersprungen, nach einer Viererreihe
    ist Schluss)."""
    b = bb.Board()
    out = []
    for m in moves:
        if b.is_game_over():
            break
        if 0 <= m < COLS and b.is_legal_move(m):
            b.play(m)
            out.append(m)
    return out


def win_cells(arr):
    """Alle Felder, die zu einer 4er-Reihe (oder laenger) gehoeren.
    arr: to_array()[spalte][zeile]; Rueckgabe {(r_top, c)}."""
    grid = [[arr[c][r] for c in range(COLS)] for r in range(ROWS)]
    found = set()
    for r in range(ROWS):
        for c in range(COLS):
            v = grid[r][c]
            if v == 0:
                continue
            for dc, dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
                cells = [(r, c)]
                nr, nc = r + dr, c + dc
                while 0 <= nr < ROWS and 0 <= nc < COLS and grid[nr][nc] == v:
                    cells.append((nr, nc))
                    nr += dr
                    nc += dc
                nr, nc = r - dr, c - dc
                while 0 <= nr < ROWS and 0 <= nc < COLS and grid[nr][nc] == v:
                    cells.append((nr, nc))
                    nr -= dr
                    nc -= dc
                if len(cells) >= 4:
                    for (rr, cc) in cells:
                        found.add((ROWS - 1 - rr, cc))
    return found


def stone_for_move_no(n):
    """Zugnummer n (0-basiert): Gelb beginnt -> gerade = Gelb."""
    return "yellow" if n % 2 == 0 else "red"


def board_from_moves(moves):
    b = bb.Board()
    for m in moves:
        b.play(m)
    return b


class Game:
    """Brett + Verlauf (history) + Zug-vor-Stapel (future)."""

    def __init__(self):
        self.board = bb.Board()
        self.history = []
        self.future = []

    def rebuild(self):
        self.board = board_from_moves(self.history)

    def reset(self):
        self.board = bb.Board()
        self.history.clear()
        self.future.clear()

    def set_moves(self, moves):
        """Stellung aus Zugliste (legaler Praefix bis Partieende)."""
        self.reset()
        self.history.extend(legal_prefix(moves))
        self.rebuild()

    # Abfragen
    def is_game_over(self):
        return self.board.is_game_over()

    def is_legal(self, col):
        return self.board.is_legal_move(col)

    def winner(self):
        """1 = Gelb, 2 = Rot, None/0 = keiner bzw. Remis."""
        return self.board.winner()

    def current_player_no(self):
        return 1 if len(self.history) % 2 == 0 else 2

    def stone_to_move(self):
        return stone_for_move_no(len(self.history))

    def column_height(self, col):
        return self.board.get_column_height(col)

    def to_array(self):
        return self.board.to_array()

    @property
    def last_move(self):
        """(r_top, c) des zuletzt gespielten Steins oder None."""
        if not self.history:
            return None
        col = self.history[-1]
        h = self.board.get_column_height(col)
        if h <= 0:
            return None
        return (ROWS - h, col)

    def win_cells(self):
        if not self.board.is_game_over():
            return set()
        return win_cells(self.board.to_array())

    def copy_board(self):
        return board_from_moves(self.history)

    # Aenderungen
    def play(self, col):
        """Zug ausfuehren (Spalte 0..6), Zug-vor-Stapel leeren."""
        self.history.append(col)
        self.future.clear()
        self.rebuild()

    def undo(self):
        if not self.history:
            return False
        self.future.append(self.history.pop())
        self.rebuild()
        return True

    def redo(self):
        if not self.future:
            return False
        self.history.append(self.future.pop())
        self.rebuild()
        return True

    def goto_first(self):
        while self.history:
            self.future.append(self.history.pop())
        self.rebuild()

    def goto_last(self):
        while self.future:
            self.history.append(self.future.pop())
        self.rebuild()
