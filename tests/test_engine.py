"""KI/Stufen: Zugwahl, Schutzfilter, Analyse, Zufallsstellungen, Match/Elo."""
import random

import bitbully as bb
import pytest

from cfs_core import game as gm
from cfs_core import levels
from cfs_core.match import Match, SessionScore, human_won_normal


def board(moves):
    return gm.board_from_moves(moves)


# ---------- Stufen ----------
def test_level_table():
    assert len(levels.STUFEN_ORDER) == 15
    assert levels.STUFEN_ORDER[0] == "verlierer" and levels.STUFEN_ORDER[-1] == "perfekt"
    assert levels.stufen_werte("perfekt") == ("perfekt", 0.0, None, None)
    assert levels.stufen_werte("mittel") == ("mittel", 0.5, 1, 1)
    assert levels.stufen_werte("starker_meister") == ("starker_meister", pytest.approx(0.08), 4, 4)
    assert levels.stufen_werte("verlierer") == ("verlierer", 1.0, 0, 0)
    assert levels.stufen_werte("mensch") == ("mensch", 0.0, None, None)
    assert levels.stufen_werte("unbekannt")[0] == "perfekt"


def test_user_psw_and_labels():
    levels.set_user_psw("user1", (120, 12, -3))
    assert levels.user_psw("user1") == (100, 9, 0)
    assert levels.parse_psw("70", "x", "2") == (70, 1, 2)
    levels.set_user_psw("user1", (60, 2, 1))
    assert levels.stufen_werte("user1") == ("user1", pytest.approx(0.4), 2, 1)
    assert levels.stufe_label_for("user1", mit_psw=True) == "User (1) (60,2,1)"
    assert levels.stufe_label_for("mittel", mit_psw=True) == "7 Mittel (50,1,1)"
    assert levels.stufe_label_for("perfekt", mit_psw=True) == "14 Perfekt"
    levels.set_user_psw("user1", levels.USER_PSW_DEFAULT)


def test_match_elo():
    assert levels.match_elo(0, 0) is None
    assert levels.match_elo(0, 10) == -2000.0
    assert levels.match_elo(10, 10) == 2000.0
    assert levels.match_elo(5, 10) == 0.0
    assert levels.match_elo(15, 20) == 191.0


# ---------- Engine ----------
def test_perfect_plays_immediate_win(engine):
    b = board([0, 1, 0, 1, 0, 1])          # Gelb gewinnt mit Spalte 1
    for _ in range(5):
        col, score, _d, _n = engine.pick_move(b, levels.stufen_werte("perfekt"))
        assert col == 0 and score > 0


def test_perfect_blocks_threat(engine):
    b = board([0, 1, 0, 1, 0])             # Rot muss Spalte 1 blocken
    col, _s, _d, _n = engine.pick_move(b, levels.stufen_werte("perfekt"))
    assert col == 0


@pytest.mark.parametrize("key", levels.STUFEN_ORDER + ("user1", "user2"))
def test_every_level_returns_legal_move(engine, key):
    random.seed(1)
    b = board([3, 3, 2, 4])
    col, _s, _d, nodes = engine.pick_move(b, levels.stufen_werte(key))
    assert col in b.legal_moves()
    assert nodes >= 0


def test_win_protection_takes_short_win(engine):
    random.seed(3)
    b = board([0, 1, 0, 1, 0, 1])
    # Mittel (w=1): kurzer Gewinn (ml 1) geht immer vor, auch bei Patzerquote 50 %
    for _ in range(10):
        col, *_ = engine.pick_move(b, levels.stufen_werte("mittel"))
        assert col == 0


def test_loss_protection_filter(engine):
    b = board([0, 1, 0, 1, 0])
    scores, _ = engine.iterative_scores(b)
    # s=1: Zuege, nach denen Rot sofort verliert (ml <= 2), sind tabu
    for _ in range(20):
        assert engine.filtered_blunder(b, scores, 1) == 0
    # s=0: ungefiltert, irgendein legaler Zug
    assert engine.filtered_blunder(b, scores, 0) in b.legal_moves()


def test_loser_level_prefers_losing_moves(engine):
    random.seed(5)
    b = board([0, 1, 0, 1, 0])
    scores, _ = engine.iterative_scores(b)
    losing = {c for c, s in scores.items() if s < 0}
    assert losing
    for _ in range(10):
        col, *_ = engine.pick_move(b, levels.stufen_werte("verlierer"))
        assert col in losing


def test_iterative_scores_progress_and_abort(engine):
    seen = []
    scores, nodes = engine.iterative_scores(board([3]), on_progress=lambda *a: seen.append(a[0]))
    assert set(scores) == set(range(7)) and nodes > 0
    assert seen and seen[-1] == -1          # letzte Stufe = Vollsuche
    scores, _ = engine.iterative_scores(board([3]), abort=lambda: True)
    assert scores == {}


def test_book_and_labels(engine):
    assert engine.is_book_loaded()
    assert engine.book_text(3).startswith("Buch")
    assert engine.book_text(20) == "berechnet"


@pytest.mark.parametrize("wish,sign", [("Gewinn", 1), ("Unentschieden", 0), ("Verlust", -1)])
def test_random_position_matches_wish(engine, wish, sign):
    random.seed(11)
    seq = engine.random_position(4, wish)
    assert isinstance(seq, list) and len(seq) == 4
    b = bb.Board.from_moves(seq)
    assert not b.is_game_over()
    s = engine.mtdf(b)
    assert (s > 0) - (s < 0) == sign


def test_random_position_stop(engine):
    assert engine.random_position(3, "Gewinn", stop=lambda: True) == "stopped"
    seq = engine.random_position(5, "Egal")
    assert len(seq) == 5


# ---------- Match / Spielstand ----------
def test_match_scoring_with_color_swap():
    m = Match("leicht", "mittel", 4, wechsel=True)
    assert m.gelb_beginnt() and m.side_stufe(0) == "leicht" and m.side_stufe(1) == "mittel"
    assert m.record_result(1) == "leicht"       # Partie 1: Gelb-Seite gewinnt als Gelb
    assert m.advance()
    assert not m.gelb_beginnt() and m.side_stufe(0) == "mittel"
    assert m.record_result(2) == "leicht"       # Partie 2: Gelb-Seite gewinnt als Rot
    assert m.advance()
    assert m.record_result(1) == "leicht"
    assert m.advance()
    assert m.record_result(None) is None
    assert not m.advance() and m.fertig
    assert m.done() == 4 and m.punkte_gelb == 3 and m.remis == 1
    assert m.points() == (3.5, 0.5)
    assert m.score_str(fixed=True) == "3,5-0,5 (+3/=1/-0)"
    assert "Elo" in m.status_line()
    assert "beendet" in m.result_text()


def test_match_human_disables_turbo():
    m = Match("mensch", "perfekt", 2, blind=True)
    assert not m.blind and m.pause_between_games()
    assert Match("leicht", "mittel", 2, schnell=True).delay_ms() == 0
    assert Match("leicht", "mittel", 2).delay_ms() == 350


def test_human_won_normal_rule():
    assert human_won_normal(None, 42, True) is None
    assert human_won_normal(1, 7, True) is True      # Mensch Gelb gewinnt
    assert human_won_normal(1, 7, False) is False    # Computer begann (Gelb) und gewann
    assert human_won_normal(2, 8, False) is True     # Mensch Rot gewinnt


def test_session_score():
    st = SessionScore()
    assert st.book_normal("mittel", True) is None    # aus -> nichts gebucht
    st.toggle("mittel")
    assert st.enabled and st.pairs == {"mittel": [0, 0, 0]}
    st.book_normal("mittel", True)
    head, big, sub, elo = st.display()
    assert big == "1-0" and "Mittel" in head and elo == ""   # Elo erst ab je 0,5
    st.book_normal("mittel", None)
    assert st.display()[1] == "1,5-0,5" and st.display()[3] == "Elo +191"
    st.book_normal("mittel", False)
    assert st.display()[3] == "Elo ±0"
    st.add_match_result("mensch", "schwer", "schwer")
    assert st.pairs["schwer"] == [0, 1, 0]
    assert st.add_match_result("leicht", "mittel", "leicht") is None
    st.reset_to("experte")
    assert st.pairs["experte"] == [0, 0, 0]
    st.toggle("mittel")
    assert st.display() == ("", "", "", "")
