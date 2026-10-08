"""Programm- und Benutzerpfade.

Programmdaten (Bilder) liegen neben dem Paket in data/; bei einer
PyInstaller-.exe im Entpack-Ordner (sys._MEIPASS).

Benutzerdaten (quicksave.4gp, lang.cfg, settings.json):
  1. Umgebungsvariable CFS_USER_DIR (gesetzt z.B. von der AppImage), sonst
  2. Windows: %APPDATA%\\ConnectFour Studio Qt
  3. sonst:   $XDG_CONFIG_HOME/connectfour-studio-qt (Standard ~/.config/...)
"""

import json
import os
import sys

APP_DIR_NAME = "connectfour-studio-qt"
APP_DIR_NAME_WIN = "ConnectFour Studio Qt"


def base_dir():
    """Ordner mit data/ (Quellbaum bzw. PyInstaller-Entpackordner)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return meipass
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE = base_dir()
DATA_DIR = os.path.join(BASE, "data")
IMAGE_DIR = os.path.join(DATA_DIR, "images")


def user_dir(create=True):
    """Beschreibbarer Benutzerordner (wird bei Bedarf angelegt)."""
    d = os.environ.get("CFS_USER_DIR")
    if not d:
        if sys.platform.startswith("win"):
            root = os.environ.get("APPDATA") or os.path.expanduser("~")
            d = os.path.join(root, APP_DIR_NAME_WIN)
        else:
            root = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
                os.path.expanduser("~"), ".config")
            d = os.path.join(root, APP_DIR_NAME)
    if create:
        try:
            os.makedirs(d, exist_ok=True)
        except OSError:
            pass
    return d


def quicksave_path():
    return os.path.join(user_dir(), "quicksave.4gp")


def settings_path():
    return os.path.join(user_dir(), "settings.json")


# Gespeicherte Einstellungen (Qt-Port): Ansicht-Haken, Set, Stufe und der
# zuletzt benutzte Ordner der Datei-Dialoge.
SETTINGS_DEFAULTS = {
    "ghost": True,
    "anim": True,
    "show_last": True,
    "set_no": 1,
    "level": "perfekt",
    "last_dir": "",
}


def load_settings():
    data = dict(SETTINGS_DEFAULTS)
    try:
        with open(settings_path(), encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            for k, default in SETTINGS_DEFAULTS.items():
                v = raw.get(k, default)
                if isinstance(v, type(default)):
                    data[k] = v
    except Exception:
        pass
    return data


def save_settings(data):
    try:
        out = {k: data.get(k, v) for k, v in SETTINGS_DEFAULTS.items()}
        tmp = settings_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        os.replace(tmp, settings_path())
    except Exception:
        pass


def start_dir(last_dir):
    """Startordner fuer Datei-Dialoge: zuletzt benutzt, sonst Home."""
    if last_dir and os.path.isdir(last_dir):
        return last_dir
    return os.path.expanduser("~")
