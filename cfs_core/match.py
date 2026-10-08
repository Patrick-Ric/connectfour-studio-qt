"""Computer-Computer Match und Spielstand (Mensch vs. Computer).

Reine Zustands-/Zaehllogik aus connectfour_studio.py (_match_*, _stand_*),
ohne Timer und GUI. Die Ablaufsteuerung (Zuege anstossen, Pausen) liegt im
Hauptfenster.
"""

from cfs_core import lang as cfs_lang
from cfs_core import levels


class Match:
    """Laufendes bzw. letztes Match. gelb/rot = Stufenschluessel der Seiten
    (inkl. 'mensch', 'user1', 'user2'). nr = aktuelle Partie (1-basiert)."""

    def __init__(self, gelb, rot, spiele, wechsel=True, schnell=False, blind=False):
        # Mit Mensch-Seite kein Turbo (Brett muss sichtbar bleiben).
        if "mensch" in (gelb, rot):
            blind = False
        self.gelb = gelb
        self.rot = rot
        self.spiele = max(1, min(10000, int(spiele)))
        self.wechsel = bool(wechsel)
        self.schnell = bool(schnell)
        self.blind = bool(blind)
        self.nr = 1
        self.punkte_gelb = 0
        self.remis = 0
        self.fertig = False
        self.abgebrochen = False

    # ---------- Ablauf ----------
    @property
    def running(self):
        return not self.fertig

    def gelb_beginnt(self):
        """Ohne Wechsel beginnt immer Gelb; mit Wechsel alternierend."""
        if not self.wechsel:
            return True
        return (self.nr % 2) == 1

    def side_stufe(self, n_moves):
        """Stufe der Seite am Zug bei n_moves gespielten Zuegen."""
        if self.gelb_beginnt():
            return self.gelb if n_moves % 2 == 0 else self.rot
        return self.rot if n_moves % 2 == 0 else self.gelb

    def has_human(self):
        return "mensch" in (self.gelb, self.rot)

    def delay_ms(self):
        """Pause zwischen Zuegen: Normal 350 ms, Schnell/Turbo 0."""
        return 0 if (self.schnell or self.blind) else 350

    def pause_between_games(self):
        """3 s Pause vor der naechsten Partie (Mensch dabei oder Tempo Normal)."""
        return self.has_human() or not (self.schnell or self.blind)

    def record_result(self, winner):
        """Partie werten. winner: 1 Gelb (Anziehender), 2 Rot, None/0 Remis.
        Rueckgabe: Stufenschluessel der Siegerseite oder None (Remis)."""
        if winner is None or winner == 0:
            self.remis += 1
            return None
        if int(winner) == 1:
            if self.gelb_beginnt():
                self.punkte_gelb += 1
                return self.gelb
            return self.rot
        if not self.gelb_beginnt():
            self.punkte_gelb += 1
            return self.gelb
        return self.rot

    def advance(self):
        """Naechste Partie; True wenn es eine gibt, sonst Match fertig."""
        if self.nr >= self.spiele:
            self.fertig = True
            return False
        self.nr += 1
        return True

    def stop(self, cancelled=True):
        self.fertig = True
        if cancelled:
            self.abgebrochen = True

    # ---------- Zahlen ----------
    def done(self):
        return max(0, self.nr if self.fertig else self.nr - 1)

    def points(self):
        done = self.done()
        pg = self.punkte_gelb + 0.5 * self.remis
        pr = (done - self.punkte_gelb - self.remis) + 0.5 * self.remis
        return pg, pr

    def losses(self):
        return self.done() - self.punkte_gelb - self.remis

    def elo(self):
        return levels.match_elo(self.punkte_gelb + 0.5 * self.remis, self.done())

    def score_str(self, fixed=False):
        pg, pr = self.points()
        g = self.punkte_gelb
        r = self.losses()
        if fixed:
            pg_s, pr_s = levels.short_number(pg), levels.short_number(pr)
            if pr < 0:
                pr_s = "0"
                r = max(0, r)
            return f"{pg_s}-{pr_s} (+{g}/={self.remis}/-{r})"
        return f"{pg:g} – {pr:g} (+{g}/={self.remis}/-{r})"

    # ---------- Texte ----------
    def status_line(self):
        elo = self.elo()
        elo_txt = "Elo –" if elo is None else f"Elo {elo:+.0f}"
        return cfs_lang.tf("match_status_line", nr=self.nr, games=self.spiele,
                           g=levels.stufe_label_for(self.gelb),
                           r=levels.stufe_label_for(self.rot),
                           score=self.score_str(fixed=True), elo=elo_txt)

    def live_text(self):
        elo = self.elo()
        elo_txt = "–" if elo is None else f"{elo:+.0f}"
        # Reihenfolge wie Tk: fertig (auch nach Abbruch) -> 'Beendet.'
        state = cfs_lang.t("match_state_done" if self.fertig else
                           ("match_state_aborted" if self.abgebrochen
                            else "match_state_running"))
        return cfs_lang.tf("match_live", nr=min(self.nr, self.spiele),
                           games=self.spiele, state=state,
                           g=levels.stufe_label_for(self.gelb),
                           r=levels.stufe_label_for(self.rot),
                           score=self.score_str(), elo=elo_txt)

    def result_text(self):
        gn = levels.stufe_label_for(self.gelb, mit_psw=True)
        rn = levels.stufe_label_for(self.rot, mit_psw=True)
        done = self.done()
        pg, pr = self.points()
        elo = self.elo()
        elo_txt = "–" if elo is None else f"{elo:+.0f}"
        state = cfs_lang.t("match_aborted_lc" if self.abgebrochen else "match_finished_lc")

        def seite(key, label):
            return (cfs_lang.t("level_human") if key == "mensch"
                    else cfs_lang.tf("side_computer", label=label))
        return cfs_lang.tf(
            "match_result_text", a=seite(self.gelb, gn), b=seite(self.rot, rn),
            pg=f"{pg:g}", pr=f"{pr:g}", w=self.punkte_gelb, d=self.remis,
            l=self.losses(), elo=elo_txt, done=done, games=self.spiele,
            state=state, swap=cfs_lang.t("onoff_on" if self.wechsel else "onoff_off"))


def match_result_text(match):
    if match is None:
        return cfs_lang.t("match_no_result")
    return match.result_text()


def human_won_normal(winner, n_moves, human_first):
    """Normalpartie Mensch-Computer: True = Mensch gewann, False = Computer,
    None = Remis. Regel: der Zuletzt-Zieher hat gewonnen; der Mensch zog die
    ungeraden Zuege (human_first) bzw. die geraden."""
    if winner in (None, 0):
        return None
    zuletzt_ungerade = (n_moves % 2 == 1)
    return zuletzt_ungerade == bool(human_first)


class SessionScore:
    """Spielstand Mensch vs. Computer je Gegnerstufe:
    pairs[comp_key] = [siege_mensch, siege_comp, remis]. Standard aus."""

    def __init__(self):
        self.enabled = False
        self.pairs = {}

    @staticmethod
    def pair_key_normal(comp_key):
        if comp_key == "mensch":
            return None
        if comp_key in levels.COMPUTER_KEYS:
            return comp_key
        return None

    @staticmethod
    def pair_key_match(gelb, rot):
        """Gegnerstufe fuer ein Match mit genau einer Mensch-Seite."""
        if gelb == "mensch" and rot != "mensch":
            other = rot
        elif rot == "mensch" and gelb != "mensch":
            other = gelb
        else:
            return None
        return other if other in levels.COMPUTER_KEYS else None

    def _bump(self, pair, idx):
        z = self.pairs.get(pair)
        if z is None:
            z = [0, 0, 0]
            self.pairs[pair] = z
        if idx is not None:
            z[idx] += 1

    def book_normal(self, comp_key, sieger_mensch):
        """Normalpartie einbuchen (nur wenn an). Rueckgabe: Paar oder None."""
        if not self.enabled:
            return None
        pair = self.pair_key_normal(comp_key)
        if pair is None:
            return None
        self._bump(pair, 2 if sieger_mensch is None else (0 if sieger_mensch else 1))
        return pair

    def add_match_result(self, gelb, rot, sieger_key):
        """Match-Partie mit Mensch-Seite einbuchen (nur wenn an)."""
        if not self.enabled:
            return None
        pair = self.pair_key_match(gelb, rot)
        if pair is None:
            return None
        if sieger_key is None:
            idx = 2
        elif sieger_key == "mensch":
            idx = 0
        else:
            idx = 1
        self._bump(pair, idx)
        return pair

    def reset_to(self, comp_key):
        """Stufenwechsel: Stand der neuen Gegnerstufe auf 0-0."""
        if comp_key == "mensch" or comp_key not in levels.COMPUTER_KEYS:
            return None
        self.pairs[comp_key] = [0, 0, 0]
        return comp_key

    def last_pair(self):
        return next(reversed(self.pairs)) if self.pairs else None

    def toggle(self, comp_key):
        """An/Aus. Frisch an ohne Daten -> 0-0 gegen comp_key."""
        self.enabled = not self.enabled
        if self.enabled and not self.pairs:
            if comp_key == "mensch" or (comp_key not in levels.STUFEN and comp_key != "verlierer"):
                comp_key = "perfekt"
            self.pairs.setdefault(comp_key, [0, 0, 0])
        return self.enabled

    def reset(self, comp_key):
        """Reset-Button: letztes Paar (bzw. aktuelle Stufe) auf 0-0."""
        pair = self.last_pair()
        if pair is None:
            pair = comp_key if (comp_key != "mensch" and comp_key in levels.STUFEN) else "perfekt"
        self.pairs[pair] = [0, 0, 0]
        return pair

    def display(self, pair=None):
        """(kopf, gross, unter, elo) – leer, wenn aus/keine Daten."""
        empty = ("", "", "", "")
        if not self.enabled:
            return empty
        if pair is None:
            pair = self.last_pair()
            if pair is None:
                return empty
        z = self.pairs.get(pair)
        if z is None:
            return empty
        sm, sc, rem = z
        pm = sm + 0.5 * rem
        pc = sc + 0.5 * rem
        partien = sm + sc + rem
        head = cfs_lang.tf("stand_head", x=levels.stufe_label_for(pair))
        big = f"{levels.short_number(pm)}-{levels.short_number(pc)}"
        sub = cfs_lang.tf("stand_sub", w=sm, d=rem, l=sc, n=partien)
        elo_line = ""
        if pm >= 0.5 and pc >= 0.5 and partien > 0:
            elo = levels.match_elo(pm, partien)
            if elo is None:
                elo_txt = "–"
            elif abs(elo) < 0.5:
                elo_txt = "±0"
            else:
                elo_txt = f"{elo:+.0f}"
            elo_line = f"Elo {elo_txt}"
        return head, big, sub, elo_line
