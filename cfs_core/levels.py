"""Stufen (p,s,w), Stufen-Namen und Elo-Formel (aus cfs_levels.py).

GUI-unabhaengig: Die Tk-Version las User-(p,s,w) ueber Klassenattribute der
App; hier liegen sie modulweit in USER_PSW (reine Python-Werte, von
Worker-Threads lesbar). Der Zufalls-Dialog wohnt in cfs_qt.dialogs.

p = % perfekte Zuege (Patzerquote = (100-p)/100);
s = Verlustschutz in Gegnerzuegen (Patzer-Zug tabu, wenn ml <= 2*s);
w = Siegsschutz (kurzer Gewinn mit ml <= 2*w-1 geht immer vor).
ml = untere Zahl (Gewinn-/Verlustdistanz aus eigener Sicht).
"""

import decimal
import math

from cfs_core import lang as cfs_lang

STUFEN_ORDER = ("verlierer", "zufall", "sehr_leicht", "leicht", "anfaenger",
                "fortgeschritten", "taktiker", "mittel", "fordernd",
                "schwer", "sehr_schwer", "experte", "meister",
                "starker_meister", "perfekt")

STUFEN = {
    "zufall": ("1 Zufall", 0, 0, 0),
    "sehr_leicht": ("2 Sehr Leicht", 25, 0, 0),
    "leicht": ("3 Leicht", 40, 0, 0),
    "anfaenger": ("4 Anfänger", 50, 0, 0),
    "fortgeschritten": ("5 Fortgeschritten", 20, 1, 1),
    "taktiker": ("6 Taktiker", 0, 3, 3),
    "mittel": ("7 Mittel", 50, 1, 1),
    "fordernd": ("8 Fordernd", 55, 1, 1),
    "schwer": ("9 Schwer", 65, 1, 1),
    "sehr_schwer": ("10 Sehr Schwer", 70, 2, 2),
    "experte": ("11 Experte", 80, 2, 2),
    "meister": ("12 Meister", 85, 3, 3),
    "starker_meister": ("13 Starker Meister", 92, 4, 4),
    "perfekt": ("14 Perfekt", 100, None, None),
}

USER_KEYS = ("user1", "user2")
USER_LABEL_1 = "User (1)"
USER_LABEL_2 = "User (2)"
USER_PSW_DEFAULT = (50, 1, 1)
# Aktuelle User-(p,s,w) je Key (Match-Dialog schreibt, Engine liest).
USER_PSW = {"user1": USER_PSW_DEFAULT, "user2": USER_PSW_DEFAULT}

MATCH_STUFEN = ("mensch",) + STUFEN_ORDER + USER_KEYS

# Gueltige Computer-Stufen (ohne Mensch)
COMPUTER_KEYS = set(STUFEN) | {"verlierer", "user1", "user2"}


def clamp_psw(p, s, w):
    """(p,s,w) klammern: p 0-100, s/w 0-9."""
    return (max(0, min(100, int(p))), max(0, min(9, int(s))),
            max(0, min(9, int(w))))


def parse_psw(p_txt, s_txt, w_txt):
    """(p,s,w) aus drei Texteingaben; Fehler -> Default je Feld (50,1,1)."""
    out = []
    for txt, default, hi in ((p_txt, 50, 100), (s_txt, 1, 9), (w_txt, 1, 9)):
        try:
            out.append(max(0, min(hi, int(str(txt).strip()))))
        except Exception:
            out.append(default)
    return tuple(out)


def user_psw(key):
    try:
        return clamp_psw(*USER_PSW.get(key, USER_PSW_DEFAULT))
    except Exception:
        return USER_PSW_DEFAULT


def set_user_psw(key, psw):
    if key in USER_KEYS:
        USER_PSW[key] = clamp_psw(*psw)


def level_label(key):
    """Stufen-Anzeigename 'Nr Name' in der aktiven Sprache (Fallback 14
    Perfekt)."""
    if key not in STUFEN_ORDER:
        key = "perfekt"
    return f"{STUFEN_ORDER.index(key)} {cfs_lang.level_name(key)}"


def normalize_key(key):
    """Unbekannte Stufen -> 'perfekt' (wie stufe_key der Tk-Version)."""
    if key == "mensch":
        return key
    return key if key in COMPUTER_KEYS else "perfekt"


def stufen_werte(key):
    """(key, patzerquote, s, w) zu einem Stufenschluessel."""
    if key == "mensch":
        return "mensch", 0.0, None, None
    if key == "verlierer":
        return "verlierer", 1.0, 0, 0
    if key in USER_KEYS:
        p, s, w = user_psw(key)
        q = (100 - p) / 100.0
        return key, max(0.0, min(1.0, q)), s, w
    dat = STUFEN.get(key)
    if not dat:
        return "perfekt", 0.0, None, None
    _label, p, s, w = dat
    q = max(0.0, min(1.0, (100 - int(p)) / 100.0))
    return key, q, s, w


def stufe_label_for(key, mit_psw=False):
    """Stufen-Anzeigename zu einem Schluessel (Match, Infobox, Spielstand)."""
    if key == "mensch":
        return cfs_lang.t("level_human")
    if key == "verlierer":
        return level_label("verlierer")
    if key in USER_KEYS:
        lbl = USER_LABEL_1 if key == "user1" else USER_LABEL_2
        if not mit_psw:
            return lbl
        p, s, w = user_psw(key)
        return f"{lbl} ({p},{s},{w})"
    name = level_label(key)
    if mit_psw and key not in ("perfekt", "verlierer", "zufall"):
        dat = STUFEN.get(key)
        if dat:
            _label, p, s, w = dat
            s_txt = "-" if s is None else str(s)
            w_txt = "-" if w is None else str(w)
            return f"{name} ({p},{s_txt},{w_txt})"
    return name


def match_elo(punkte_gelb, partien):
    """Elo-Differenz aus Gelb-Sicht (-400*log10((1-p)/p)), 0/100% -> +/-2000."""
    if partien <= 0:
        return None
    p = punkte_gelb / partien
    if p <= 0.0:
        return -2000.0
    if p >= 1.0:
        return 2000.0
    raw = -400.0 * math.log10((1.0 - p) / p)
    return float(decimal.Decimal(str(raw)).quantize(
        decimal.Decimal("1"), rounding=decimal.ROUND_HALF_UP))


def short_number(x):
    """12.0 -> '12', 12.5 -> '12,5' (Dezimalzeichen je Sprache)."""
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return cfs_lang.fmt_decimal(f"{x:.1f}")
