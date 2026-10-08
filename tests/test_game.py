"""Spiellogik: Gewinnerkennung, gueltige Zuege, Navigation, .4gp-Format."""
import os

import pytest

from cfs_core import game as gm

DATA = os.path.join(os.path.dirname(__file__), "data")


def play_all(moves):
    g = gm.Game()
    for m in moves:
        g.play(m)
    return g


# ---------- Gewinnerkennung ----------
@pytest.mark.parametrize("moves,winner", [
    ([0, 1, 0, 1, 0, 1, 0], 1),                 # Gelb senkrecht
    ([0, 0, 1, 1, 2, 2, 3], 1),                 # Gelb waagerecht
    ([6, 0, 6, 1, 5, 2, 5, 3], 2),              # Rot waagerecht
    ([0, 1, 1, 2, 2, 3, 2, 3, 3, 6, 3], 1),     # Gelb diagonal /
    ([3, 2, 2, 1, 1, 0, 1, 0, 0, 6, 0], 1),     # Gelb diagonal \
])
def test_winner_detection(moves, winner):
    g = play_all(moves)
    assert g.is_game_over()
    assert g.winner() == winner
    cells = g.win_cells()
    assert len(cells) >= 4
    # Gewinnfelder gehoeren alle dem Sieger
    arr = g.to_array()
    for (r_top, c) in cells:
        assert arr[c][gm.ROWS - 1 - r_top] == winner


def test_no_winner_midgame():
    g = play_all([3, 3, 2, 4])
    assert not g.is_game_over()
    assert g.win_cells() == set()
    assert g.winner() in (None, 0)


def test_win_cells_long_row():
    # Fuenferreihe: alle fuenf Steine markiert
    arr = [[0] * 6 for _ in range(7)]
    for c in range(5):
        arr[c][0] = 2
    assert gm.win_cells(arr) == {(5, c) for c in range(5)}


def test_draw_full_board():
    # Volles Brett ohne Viererreihe (Remis)
    moves = gm.parse_4gp("455714637617614767242476316455122212535333")
    assert gm.legal_prefix(moves) == moves
    g = gm.Game()
    g.set_moves(moves)
    assert len(g.history) == 42
    assert g.is_game_over()
    assert g.winner() in (None, 0)
    assert g.win_cells() == set()
    assert not any(g.is_legal(c) for c in range(7))


# ---------- gueltige Zuege ----------
def test_legal_moves_and_full_column():
    g = gm.Game()
    for c in range(7):
        assert g.is_legal(c)
    for _ in range(6):
        g.play(0)
    assert not g.is_legal(0)
    assert g.column_height(0) == 6
    assert all(g.is_legal(c) for c in range(1, 7))


def test_current_player_and_stone():
    g = gm.Game()
    assert g.current_player_no() == 1 and g.stone_to_move() == "yellow"
    g.play(3)
    assert g.current_player_no() == 2 and g.stone_to_move() == "red"


def test_last_move_position():
    g = play_all([3, 3])
    assert g.last_move == (4, 3)   # zweiter Stein in Spalte 4 -> Reihe 4 von oben
    assert gm.Game().last_move is None


def test_navigation_undo_redo_first_last():
    g = play_all([3, 2, 4])
    assert g.undo() and g.history == [3, 2] and g.future == [4]
    assert g.redo() and g.history == [3, 2, 4] and g.future == []
    g.goto_first()
    assert g.history == [] and g.future == [4, 2, 3]
    g.goto_last()
    assert g.history == [3, 2, 4]
    g.undo()
    g.play(6)            # neuer Zug loescht den Zug-vor-Stapel
    assert g.future == [] and g.history == [3, 2, 6]
    assert gm.Game().undo() is False


# ---------- .4gp-Format ----------
def test_parse_and_format_roundtrip():
    assert gm.parse_4gp("4433221") == [3, 3, 2, 2, 1, 1, 0]
    assert gm.format_4gp([3, 3, 2, 2, 1, 1, 0]) == "4433221"
    assert gm.parse_4gp("") == []


def test_write_matches_old_format(tmp_path):
    p = tmp_path / "x.4gp"
    gm.write_4gp(str(p), [3, 3, 2, 6])
    assert p.read_bytes() == b"4437"     # wie Tk: reine Ziffern, kein Zeilenende


@pytest.mark.parametrize("name,expected", [
    ("legacy_simple.4gp", [3, 3, 2, 2, 1, 1, 0]),
    ("legacy_crlf.4gp", [3, 3, 4, 4]),
    ("legacy_noise.4gp", [0, 1, 2, 3]),
    ("legacy_digits.4gp", [0, 1, 2, 3, 4, 5, 6]),
])
def test_read_legacy_files(name, expected):
    assert gm.read_4gp(os.path.join(DATA, name)) == expected


def test_legacy_load_stops_after_win_and_skips_illegal():
    moves = gm.read_4gp(os.path.join(DATA, "legacy_after_win.4gp"))
    assert gm.legal_prefix(moves) == [0, 1, 0, 1, 0, 1, 0]   # Zug nach dem Sieg entfaellt
    moves = gm.read_4gp(os.path.join(DATA, "legacy_illegal.4gp"))
    assert gm.legal_prefix(moves) == [0] * 6                 # 7. Stein passt nicht


def test_save_load_roundtrip(tmp_path):
    g = play_all([3, 3, 4, 2, 5])
    p = str(tmp_path / "r.4gp")
    gm.write_4gp(p, g.history)
    g2 = gm.Game()
    g2.set_moves(gm.read_4gp(p))
    assert g2.history == g.history
    assert g2.to_array() == g.to_array()
