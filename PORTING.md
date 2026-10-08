# Tk → Qt-Port: Entscheidungen

Kurzprotokoll der Entscheidungen beim Port (08.10.2026). Feature-Abgleich und
Verhaltensabweichungen stehen in `FEATURES.md`.

## Toolkit und Abhängigkeiten

- **PySide6-Essentials** statt des vollen `PySide6`: enthält QtCore/QtGui/
  QtWidgets, ohne die großen Add-ons (WebEngine, Multimedia, 3D …).
- Engine und Buch unverändert: `bitbully==0.0.79`, `bitbully-databases==0.0.2`,
  Pillow für das Laden/Vermessen der Stein-Sets (gleiche Bildqualität wie in Tk,
  Lanczos-Skalierung).
- Neues Programm-Icon nicht nötig: dasselbe Motiv wie das Windows-Icon der
  Tk-Version (`packaging/make_icon.py` → `data/connectfour-studio.png`).

## Struktur

- `cfs_core/` ist GUI-frei und importiert nie Qt. Die Tk-Module wurden so
  übernommen:
  - `cfs_lang.py` → `cfs_core/lang.py`: Texte und API (`t`, `tf`, `set_lang`,
    `fmt_*`) unverändert, nur `lang.cfg` liegt im Benutzerordner.
  - `cfs_levels.py` → `cfs_core/levels.py`: Tabellen/Formeln unverändert. Die
    User-(p,s,w) lagen in Tk als Klassenattribute der App; jetzt modulweit in
    `levels.USER_PSW`. Der Zufalls-Dialog ist nach `cfs_qt/dialogs.py` gewandert.
  - `cfs_sets.py` → `cfs_core/sets.py`: Laden/Vermessen unverändert; der
    Tk-PhotoImage-Cache wurde durch `cfs_qt/tiles.py` (QPixmap-LRU) ersetzt.
  - `cfs_help.py` → `cfs_core/help_content.py` (nur Daten: Inhalte, Info-Text,
    Kreuztabelle). Die Darstellung baut `cfs_qt/dialogs.py` als HTML für einen
    `QTextBrowser` (Anker/Links, Suche, Zoom).
  - Die Spiel-/Engine-Logik aus `connectfour_studio.py` wurde in `game.py`
    (Brett, Verlauf, `.4gp`), `engine.py` (Zugwahl je Stufe, iterative
    Bewertung, Zufallsstellungen) und `match.py` (Match-Zählung, Spielstand)
    aufgeteilt – Algorithmen 1:1, damit die Spielstärke-Tabellen gültig bleiben.
- `cfs_qt/main_window.py` enthält die Ablaufsteuerung (Modi, Match, Analyse)
  mit denselben Methodennamen wie in Tk (`human_move`, `engine_move`,
  `_engine_done`, `_match_finish_game` …), damit sich beide Versionen leicht
  vergleichen lassen. Die vielen Tk-Workarounds (Menü-Polling, Shrink-Veto,
  Start-Fit-Sperre, Pin-Cache) entfallen ersatzlos – Qt braucht sie nicht.

## Oberfläche

- **Spielfeld:** eigenes `QWidget` mit `QPainter` (`cfs_qt/board.py`), gleiche
  Geometrie wie der Tk-Canvas (Kacheln, Ringe, 44-px-Wertungszeile, 4-px-
  Klicklücke). Die sieben Buttons liegen pixelgenau unter den Spalten; das
  zentrale Widget setzt die Geometrie selbst (Brett oben links, rechte Spalte
  direkt daneben), weil ein Standard-Layout die Spalte nicht „ans Brett kleben“
  würde.
- **Menü-Kürzel:** Die Menüs zeigen dieselben lokalisierten Kürzeltexte wie Tk
  („Pfeil links“, „Bild hoch“, „F5“ …) über `Text\tKürzel`; ausgelöst werden die
  Tasten über `QShortcut` mit Fenster-Kontext. Dadurch wirken sie – wie in Tk
  gewollt – nur im Hauptfenster, nie in Dialogen. F1 gilt wie in Tk überall,
  F10 ist neutralisiert.
- **Sprachwechsel:** Menüleiste wird komplett neu aufgebaut (statt Tk-Einträge
  einzeln umzubenennen); Qt-eigene Texte über `qtbase_*.qm`.
- **Match-Fenster** ist wie in Tk nicht modal; Hilfe/Info werden wiederverwendet.

## Threads

- Engine-Zug, Dauer-Analyse und Zufallssuche laufen weiter in Python-Threads
  (BitBully hinter `Engine.lock`). Statt Tk-Queue + 30-ms-Poll reicht der Worker
  Callbacks über ein Qt-Signal (queued connection) in den GUI-Thread
  (`MainWindow._safe_after`). Abbruchlogik (cancel-Flag, `ana_seq`,
  Stellungs-Snapshot) ist unverändert.

## Nutzerdaten und Dateien

- Benutzerordner: `CFS_USER_DIR`, sonst `~/.config/connectfour-studio-qt`
  (XDG) bzw. `%APPDATA%\ConnectFour Studio Qt`. Eigener Ordnername, damit die
  Qt-Version die Daten der Tk-Version nicht überschreibt.
- `.4gp` bleibt byte-kompatibel (Ziffern, kein Zeilenende); Laden ignoriert wie
  bisher Fremdzeichen, illegale Züge und Züge nach Partieende.
- Datei-Dialoge: zuletzt benutzter Ordner (gemerkt), sonst Home; native Dialoge
  des Systems, wo verfügbar.

## Packaging

- **AppImage:** Basis ist eine python-appimage-Distribution (CPython 3.14,
  manylinux_2_28 – passt zur glibc-Anforderung von PySide6). Statt eines
  Generators wie linuxdeploy dünnt `prune_appdir.py` gezielt aus: nur die drei
  Python-Module, die per `DT_NEEDED` benötigten Qt-Bibliotheken, Plattform-
  Plugins xcb/wayland/offscreen/minimal, Portal/GTK-Theme, Compose/IBus,
  SVG-Icons; nur 6 qtbase-Übersetzungen; kein Tk, kein pip; vom Buch nur
  `12-ply-dist`. `verify_appdir.py` prüft den Inhalt (auch der fertigen,
  entpackten AppImage).
- **xcb-Fallback:** Qt ≥ 6.5 braucht unter X11 `libxcb-cursor.so.0`, das nicht
  überall installiert ist. Die System-Bibliothek des Build-Rechners verlangt
  GLIBC_2.38 (C23-`strtol`), daher wird sie aus dem X.org-Quelltarball mit
  `-std=gnu99` + Shim gebaut (≤ GLIBC_2.28). Zusammen mit vier xcb-util-
  Bibliotheken liegt sie in `usr/lib/xcb-fallback` und wird von `AppRun` nur
  benutzt, wenn das System sie nicht hat.
- **Windows:** keine Quell-Patches mehr nötig (`paths.py` erkennt
  `sys._MEIPASS` und `%APPDATA%`); `prepare_build.py` kopiert nur noch und
  erzeugt das Icon, die Spec baut ein Verzeichnis-Build.
- **Selbsttest:** `CFS_SMOKE_TEST=1` öffnet Hauptfenster und alle Dialoge,
  rechnet einen Zug und beendet sich mit Exit-Code 0/1 – nutzbar für Quellbaum,
  AppImage und Windows-Build.
