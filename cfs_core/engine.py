"""BitBully-Engine: iterative Bewertung, Zugwahl je Stufe, Zufallsstellungen.

Logik 1:1 aus connectfour_studio.py (pick_engine_move & Co.), nur ohne
GUI-Zugriffe. Thread-Hinweis: BitBully ist nicht threadsicher -> alle
Agent-Aufrufe laufen unter self.lock. Fortschritts-Callbacks werden NACH dem
Lock im aufrufenden (Worker-)Thread abgesetzt; der Aufrufer muss sie selbst
in den GUI-Thread weiterreichen.
"""

import random
import threading
import time

import bitbully as bb

from cfs_core import lang as cfs_lang

LOSS_POWER = 8  # Gewicht = Verlustlaenge^POWER (nur wenn alles verliert)
ITER_DEPTHS = (4, 6, 8, 10, 12, 14, 16, 18, 20, -1)

BOOK_NAME = "12-ply-dist"
BOOK_SHORT = "12d"
BOOK_HORIZON = 12


class Engine:
    def __init__(self, load_book=True):
        self.agent = bb.BitBully()
        self.agent.max_depth = -1  # -1 = unbegrenzt = Perfekt
        self.lock = threading.Lock()
        self.last_depth = None  # zuletzt erreichte Iterationstiefe
        self.book_error = None
        if load_book:
            self.load_book()

    # ---------- Buch ----------
    def load_book(self):
        try:
            self.agent.load_book(BOOK_NAME)
            self.book_error = None
        except Exception as e:
            self.book_error = e

    def is_book_loaded(self):
        try:
            return bool(self.agent.is_book_loaded())
        except Exception:
            return False

    def plies_text(self, n_moves):
        """'Tiefe'-Anzeige: letzte Iterationstiefe bzw. Buch-Horizont."""
        if self.last_depth is not None:
            return cfs_lang.t("depth_full") if self.last_depth == -1 else str(self.last_depth)
        if not self.is_book_loaded():
            return "–"
        if n_moves <= BOOK_HORIZON:
            return f"{cfs_lang.t('depth_book')} {BOOK_SHORT}"
        return "–"

    def book_text(self, n_moves):
        """'Quelle'-Anzeige: 'Buch 12d' bis 12 Steine, danach 'berechnet'."""
        if not self.is_book_loaded():
            return "–"
        if n_moves <= BOOK_HORIZON:
            return f"{cfs_lang.t('book_from_book')} {BOOK_SHORT}"
        return cfs_lang.t("book_computed")

    def reset(self):
        with self.lock:
            self.agent.reset_transposition_table()
            self.agent.reset_node_counter()

    # ---------- Hilfsfunktionen ----------
    @staticmethod
    def moves_left(board, score):
        """moves_left (untere Zahl) zu einem Score oder None."""
        try:
            return bb.BitBully.score_to_moves_left(score, board)
        except Exception:
            return None

    def short_wins(self, board, scores, wschutz):
        """Siegsschutz (Variante B): '+'-Zuege mit ml <= 2*w-1."""
        try:
            w = int(wschutz) if wschutz is not None else 0
        except Exception:
            return []
        if w <= 0:
            return []
        limit = 2 * w - 1
        menge = []
        for c in board.legal_moves():
            s = scores.get(c)
            if s is None or s <= 0:
                continue
            ml = self.moves_left(board, s)
            if ml is not None and ml <= limit:
                menge.append(c)
        return menge

    def filtered_blunder(self, board, scores, cutoff, wschutz=None):
        """Gefilterter Patzer: uniform aus legalen Zuegen; Zuege, bei denen
        der Gegner in <= cutoff Zuegen mattet (ml <= 2*cutoff), sind tabu.
        Siegsschutz vorab; alles tabu -> laengster Widerstand."""
        win_menge = self.short_wins(board, scores, wschutz)
        if win_menge:
            return random.choice(win_menge)
        legal = list(board.legal_moves())
        if cutoff is None:
            cutoff = 99
        if cutoff <= 0:
            return random.choice(legal)
        limit = 2 * cutoff
        ok = []
        for c in legal:
            s = scores.get(c)
            if s is None or s >= 0:
                ok.append(c)
                continue
            ml = self.moves_left(board, s)
            if ml is None:
                ok.append(c)
                continue
            if ml <= limit:
                continue
            ok.append(c)
        if ok:
            return random.choice(ok)
        best_c, best_ml = legal[0], -1
        for c in legal:
            s = scores.get(c)
            ml = self.moves_left(board, s) if s is not None and s < 0 else None
            if ml is None:
                ml = 10 ** 9
            if ml > best_ml:
                best_c, best_ml = c, ml
        return best_c

    # ---------- Bewertung ----------
    def iterative_scores(self, board, depths=ITER_DEPTHS, on_progress=None,
                         abort=None, keep_tt=False):
        """score_all_moves in Stufen (TT bleibt zwischen den Stufen).
        on_progress(depth, scores, nodes, dt) max. 1x/200 ms + letzte Stufe,
        abgesetzt nach dem Lock. abort() -> True bricht zwischen Stufen ab."""
        t0 = time.time()
        last_cb = 0.0
        scores, nodes = {}, 0
        pending = []
        stop = abort if abort is not None else (lambda: False)
        depths = list(depths)
        with self.lock:
            self.agent.reset_node_counter()
            if not keep_tt:
                try:
                    self.agent.reset_transposition_table()
                except Exception:
                    pass
            for depth in depths:
                if stop():
                    break
                try:
                    part = self.agent.score_all_moves(board, max_depth=depth)
                except Exception:
                    break
                scores, nodes = dict(part), self.agent.get_node_counter()
                self.last_depth = depth
                dt = time.time() - t0
                if on_progress is not None and (depth == depths[-1] or dt - last_cb >= 0.2):
                    last_cb = dt
                    pending.append((depth, dict(scores), nodes, dt))
                if depth == -1:
                    break
                if stop():
                    break
        for (depth, s, n, t) in pending:
            try:
                on_progress(depth, s, n, t)
            except Exception:
                import traceback
                traceback.print_exc()
        return scores, nodes

    def mtdf(self, board):
        with self.lock:
            return self.agent.mtdf(board)

    # ---------- Zugwahl ----------
    def pick_move(self, board, stufe, on_progress=None, abort=None, keep_tt=False):
        """Engine-Zugwahl. stufe = (key, patzerquote, s, w) aus
        levels.stufen_werte(). Gibt (Spalte, Score, Verlustlaenge|None,
        Knoten) zurueck."""
        scores, nodes = self.iterative_scores(board, ITER_DEPTHS, on_progress,
                                              abort=abort, keep_tt=keep_tt)
        if not scores:
            # Abbruch vor Stufe 1: Tiefe 4 (Millisekunden), damit immer ein Zug kommt.
            with self.lock:
                self.agent.reset_node_counter()
                scores = dict(self.agent.score_all_moves(board, max_depth=4))
                nodes = self.agent.get_node_counter()
        if not scores:
            raise ValueError(cfs_lang.t("err_no_legal_move"))
        key, err, schutz, wschutz = stufe

        def result(c, dist=None):
            return c, scores.get(c, max(scores.values())), dist, nodes

        if key == "verlierer":
            legal = list(board.legal_moves())
            verl = [c for c in legal if scores.get(c) is not None and scores[c] < 0]
            if verl:
                return result(random.choice(verl))
            rem = [c for c in legal if scores.get(c) is not None and scores[c] == 0]
            if rem:
                return result(random.choice(rem))
            return result(self.filtered_blunder(board, scores, 0, None))
        if key == "zufall":
            return result(self.filtered_blunder(board, scores, 0, None))
        win = self.short_wins(board, scores, wschutz)
        if win:
            return result(random.choice(win))
        if err > 0.0 and random.random() < err:
            return result(self.filtered_blunder(board, scores, schutz, wschutz))
        best = max(scores.values())
        if best >= 0:
            cands = [c for c, v in scores.items() if v == best]
            legal = set(board.legal_moves())
            cands = [c for c in cands if c in legal] or list(legal)
            pool = list(cands)
            if best > 0:
                ml = {c: self.moves_left(board, scores.get(c)) for c in cands}
                fast = [c for c in cands if ml.get(c) is not None and ml[c] <= 10]
                if fast:
                    mn = min(ml[c] for c in fast)
                    pool = [c for c in fast if ml[c] == mn]
            col = random.choice(pool)
            return col, scores[col], None, nodes
        if key == "perfekt":
            all_ml = {c: self.moves_left(board, scores.get(c))
                      for c in board.legal_moves() if scores.get(c) is not None}
            if all_ml and all(m is not None and m > 10 for m in all_ml.values()):
                return result(random.choice(list(all_ml)))
            return result(self.filtered_blunder(board, scores, 5, None))
        dist = {col: bb.BitBully.score_to_moves_left(s, board) for col, s in scores.items()}
        if len(set(dist.values())) <= 1:
            try:
                with self.lock:
                    exact = dict(self.agent.score_all_moves(board, max_depth=-1))
                if exact and max(exact.values()) < 0:
                    dist = {col: bb.BitBully.score_to_moves_left(s, board)
                            for col, s in exact.items()}
                    scores = exact
            except Exception:
                pass
        weights = {c: float(max(1, d)) ** LOSS_POWER for c, d in dist.items()}
        r = random.random() * sum(weights.values())
        for c in sorted(weights):
            r -= weights[c]
            if r <= 0:
                return c, scores[c], dist[c], nodes
        c = max(weights, key=weights.get)
        return c, scores[c], dist[c], nodes

    # ---------- Zufallsstellung ----------
    @staticmethod
    def random_legal_seq(n):
        """n zufaellige legale Zuege, Partie darf nicht vorher enden."""
        for _ in range(60):
            seq = []
            b = bb.Board()
            ok = True
            for _ in range(n):
                legal = list(b.legal_moves())
                if not legal:
                    ok = False
                    break
                c = random.choice(legal)
                b2 = b.play_on_copy(c)
                if b2.is_game_over() and len(seq) + 1 < n:
                    ok = False
                    break
                b = b2
                seq.append(c)
            if ok and not b.is_game_over():
                return seq
        return None

    def random_position(self, n, wunsch, stop=None):
        """Zugfolge mit n Steinen und Wunsch-Ergebnis (Spieler am Zug):
        'Egal' / 'Gewinn' / 'Unentschieden' / 'Verlust'.
        Rueckgabe: Liste, None (nichts gefunden) oder 'stopped'."""
        want = {"Gewinn": 1, "Unentschieden": 0, "Verlust": -1}.get(wunsch)
        for _ in range(400):
            if stop is not None and stop():
                return "stopped"
            cand = self.random_legal_seq(n)
            if cand is None:
                continue
            if want is None:
                return cand
            try:
                s = self.mtdf(bb.Board.from_moves(cand))
            except Exception:
                continue
            sign = 1 if s > 0 else (-1 if s < 0 else 0)
            if sign == want:
                return cand
        return None


def kns_text(nodes, dt):
    """Knoten/s formatiert (Dezimalzeichen je Sprache)."""
    kns = nodes / max(dt, 1e-9)
    if kns >= 1_000_000:
        return cfs_lang.fmt_decimal(f"{kns / 1_000_000:.1f} M/s")
    if kns >= 1_000:
        return f"{kns / 1_000:.0f} k/s"
    return f"{kns:.0f} /s"


def value_text(score, ml, mover_is_yellow):
    """'Gelb (31)' / 'Rot (12)' / 'Remis (42)' aus Sicht des Ziehenden."""
    gelb, rot = cfs_lang.t("color_yellow"), cfs_lang.t("color_red")
    if score > 0:
        w = gelb if mover_is_yellow else rot
    elif score < 0:
        w = rot if mover_is_yellow else gelb
    else:
        w = cfs_lang.t("value_draw")
    if ml is None:
        return w
    return f"{w} ({int(ml)})"
