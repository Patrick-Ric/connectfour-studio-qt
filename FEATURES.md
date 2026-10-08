# ConnectFour Studio – Feature-Liste (Tk-Original → Qt-Port)

Quelle: `connectfour_studio.py`, `cfs_help.py`, `cfs_lang.py`, `cfs_levels.py`,
`cfs_sets.py` der Tkinter-Version (Stand 04.10.2026).
Status: `[ ]` offen · `[x]` in der Qt-Version vorhanden und geprüft ·
`[~]` vorhanden mit dokumentierter Abweichung (→ Abschnitt „Abweichungen“).

Geprüft am 08.10.2026 durch Code-Vergleich mit der Tk-Quelle, die Tests in
`tests/` (72 Tests, u.a. offscreen-GUI-Smoke-Test) und den Selbsttest
`CFS_SMOKE_TEST=1` der fertigen AppImage (offscreen und unter Xvfb/xcb).
Kürzel hinter einem Punkt: (T) = automatischer Test, (S) = Screenshot geprüft.

## 1. Hauptfenster / Layout

- [x] Fenstertitel „ConnectFour Studio“
- [x] Brett links (7×6 Kacheln aus dem gewählten Stein-Set), Brett klebt oben
- [x] Wertungszeile direkt unter dem Brett (44 px hoch, pixelgenau unter den Spalten, 1-px-Trennlinien)
- [x] Wertungszeile ohne Analyse: Spaltennummern 1–7 (graue Felder), volle Spalte „X“
- [x] Wertungszeile mit Analyse: oben fett `+`/`=`/`-`, darunter Steinzahl bis Ende; grün/gelb/rot (Pastell) (T, S)
- [x] Klick in die Wertungszeile führt den Spaltenzug aus (4-px-Lücke dazwischen ignoriert) (T)
- [x] Buttonleiste unter dem Brett: genau 7 gleich breite Buttons (Neu, <<, <, >, >>, Ziehen, Analyse), exakt Brettbreite (T, S)
- [x] Rechte Seite: Feld „Am Zuge“ (Stein-Icon + Name: Mensch / Stufenname inkl. (p,s,w) / Match-Seite)
- [~] Feld „Info“: Zug, Stufe, Tiefe, Wert, Knoten, Zeit, Tempo, Quelle (T, S) – A9
- [x] Feld „Spielstand“ (immer sichtbar): Kopf „Mensch vs X“, großes Ergebnis (4×), (+/=/-)·Partien, Elo (erst ab ≥0,5 Punkten je Seite), Buttons An/Aus + Reset
- [x] Statuszeile unten (eingesunken), Start „Bereit.“
- [x] Natürliche Startgröße (Zoom 0,30 der 256-px-Kacheln), danach Auto-Zoom mit der Fenstergröße (Zoom 0,08 … 4,0) (T); rechte Spalte fest breit – A9
- [x] Optionales Startargument: `.4gp`-Datei wird geladen und sofort bewertet (T)

## 2. Brett-Darstellung / Animationen

- [x] Kacheln aus HiRes-PNG (Fallback BMP), Lanczos-skaliert
- [x] Ghost-Stein (halbtransparente Vorschau über der Zielspalte, Farbe des Spielers am Zug) (T, S)
- [~] Drop-Animation (Stein fällt zeilenweise, 16 ms je Zeile) (T) – A1
- [x] Letzter Zug: weißer Ring knapp außerhalb der Steinkante (Radius je Farbe vermessen)
- [x] Gewinnreihe(n): grüner Außen- + weißer Innenring an allen Steinen der 4er(+)-Reihe (T)
- [x] Stein-Radien je Set automatisch vermessen (Floodfill, Differenz-Deckel, Ring-Test)

## 3. Menü „Datei“

- [x] Neues Spiel
- [x] Neu mit Zufallsstellung… (Dialog)
- [x] Stellung laden… (.4gp, Dateidialog)
- [x] Stellung speichern… (.4gp, Standard-Endung .4gp)
- [x] Schnell speichern (F3) – ohne Dialog in `quicksave.4gp`
- [x] Schnell laden (F4) – ohne Dialog; Meldung, wenn nichts gespeichert
- [x] Ende

## 4. Menü „Ansicht“

- [x] Ghost-Stein (Haken, Standard an)
- [x] Drop-Animation (Haken, Standard an)
- [x] letzten Zug zeigen (Haken, Standard an)
- [x] Spielstand ein/aus (Haken, synchron mit Button An/Aus)
- [x] Spielstand reset

## 5. Menü „Einstellungen“

- [x] Computer-Stufe (Untermenü, Radio): 0 Verlierer, 1 Zufall … 14 Perfekt (Standard Perfekt)
- [x] Mensch-Computer (Radio, Standard) – zieht sofort, wenn der Computer am Zug ist
- [x] 2-Spieler (beide Mensch) (Radio)
- [x] Computer-Computer (ausspielen) (Radio) – Perfekt gegen sich selbst bis Partieende, 350 ms Pause
- [x] Computer-Computer Match… (Dialog)
- [x] Stop Auto Play
- [x] vorheriges Set (Bild hoch) / nächstes Set (Bild runter) – oben im Set-Block
- [x] 20 Stein-Sets als Radio-Einträge „Stein-Set N – Name“ (lokalisierte Namen)

## 6. Menü „Kommandos“

- [x] erster Zug (Pfeil hoch)
- [x] Zug zurück (Pfeil links)
- [x] Zug vor (Pfeil rechts)
- [x] letzter Zug (Pfeil runter)
- [x] ziehen (Computer) (F5) – auch bei leerem Brett (Computer eröffnet, Mensch wird Rot)
- [~] alle Züge bewerten (1x) (F6) – Umschalter (2. Aufruf: zurück zu 1–7) (T) – A2
- [x] Dauer-Analyse (F7) – Umschalter, synchron mit Button „Analyse“

## 7. Menü „Hilfe“

- [x] Inhalt (F1) – Hilfedialog
- [x] Info – Info-Dialog (kopierbar)
- [x] Sprache (Untermenü, Radio): Deutsch, English, Français, Español, Nederlands, Italiano; Wahl wird gemerkt

## 8. Tastenkürzel (nur im Hauptfenster, nicht in Dialogen/Eingabefeldern)

- [x] 1–7 Spaltenzug (T)
- [x] Pfeil links/rechts Zug zurück/vor (T)
- [x] Pfeil hoch/runter erster/letzter Zug (T)
- [x] Bild hoch/runter Set wechseln (Wrap-around) (T)
- [x] Mausrad über dem Brett Set wechseln (hoch = vorheriges) (T)
- [x] F1 Hilfe, F3/F4 Schnell speichern/laden, F5 ziehen, F6 alle bewerten, F7 Dauer-Analyse (T)
- [~] Escape schließt ein offenes Menü (Qt-Standard) – A8
- [x] F10 öffnet kein Menü (neutralisiert)

## 9. Spielmodi / Ablauf

- [x] Mensch-Computer: nach Menschenzug antwortet der Computer automatisch (T)
- [x] Zugsperre während der Computer denkt („Computer denkt noch – bitte warten.“)
- [x] Navigation gesperrt während Denken/Selbstspiel/Match (mit Statusmeldung)
- [x] Ergebnis eines Computerzugs wird verworfen, wenn sich die Stellung inzwischen geändert hat
- [x] Stop: bricht Engine-Zug, Selbstspiel, Match und Analyse ab („Angehalten …“)
- [x] Neues Spiel / Laden während des Denkens stoppt zuerst
- [x] Partieende: Statuszeile „Spielende: Gelb/Rot gewinnt! / Unentschieden!“, Wert-Feld ebenso
- [x] Selbstspiel endet am Partieende automatisch (Modus zurück auf Mensch-Computer) (T)

## 10. KI / Stufen (BitBully-Engine)

- [x] Engine BitBully, Eröffnungsbuch fest `12-ply-dist`
- [x] Iterative Vertiefung 4, 6, 8 … 20, Voll; Live-Anzeige Tiefe/Knoten/Zeit/Tempo
- [x] 14 Stufen (p, s, w) laut Tabelle + 0 Verlierer + Zufall-Sonderfall (T)
- [x] Siegsschutz w (kurzer Gewinn ml ≤ 2w−1 geht immer vor) (T)
- [x] Verlustschutz s (Patzer tabu, wenn ml ≤ 2s; sonst längster Widerstand) (T)
- [x] Perfekt: schnellster Gewinn (≤10 Halbzüge), Remis/Gewinn-Varianz, Verluststellung: schnelle Niederlagen vermeiden
- [x] Verluststellung (andere Stufen): gewichtete Wahl Verlustlänge^8
- [x] Verlierer: zufälliger Verlustzug, sonst Remis, sonst Zufall (T)
- [x] Analyse (F6/F7) immer perfekt
- [x] Info „Quelle“: „Buch 12d“ bis 12 Steine, danach „berechnet“; „Tiefe“: letzte Iterationstiefe

## 11. Dauer-Analyse

- [x] Hintergrundanalyse nach jedem Stellungswechsel, neueste Stellung gewinnt (T)
- [~] Live-Näherung je Tiefe („Tiefe 8…“), am Ende Status „Analyse: Spalte X (+n) in t s.“ (T) – A4
- [x] Veraltete Ergebnisse werden verworfen (Sequenznummer + Stellungs-Snapshot)

## 12. Dialog „Neu mit Zufallsstellung“

- [x] Steine 1–9 (Standard 3), Ergebnis Egal/Gewinn/Unentschieden/Verlust (Standard Gewinn), Hinweis grau (T, S)
- [x] Suche im Hintergrund (bis 400 Kandidaten, Prüfung per mtdf), Status „Suche Zufallsstellung …“ (T)
- [x] Danach: Mensch spielt die Farbe des nächsten Zugs, Stellung wird sofort bewertet

## 13. Dialog „Computer-Computer Match“

- [x] Nicht-modales Fenster (470×700), erneutes Öffnen holt es nach vorn
- [x] Gelb/Rot: Mensch, Stufen 0–14, User (1)/(2) (eigene p,s,w) (T, S)
- [x] Partien 1–10000 (Standard 20), Farbwechsel nach jeder Partie (Standard an)
- [x] Tempo Normal (350 ms) / Schnell (0 ms, keine Animation) / Nur Ergebnisse (Turbo, kein Zeichnen pro Zug, TT bleibt)
- [x] User-(p,s,w)-Felder nur aktiv, wenn der jeweilige User-Key gewählt ist (p 0–100, s/w 0–9) (T)
- [x] Hinweistext zu p/s/w
- [x] Live-Stand (Partie, Status, Punkte, Elo), kopierbares Endergebnis
- [x] Buttons Start, Stop, Kopieren, Schließen (Match läuft beim Schließen weiter)
- [x] Mit Mensch-Seite: kein Turbo, Mensch zieht per Klick/Taste, 3 s Pause zwischen Partien (auch bei Tempo Normal)
- [x] Statuszeile „Computer-Computer Match n/N | Gelb (…) - Rot (…) | Stand | Elo“ (T)
- [~] Matchende: Fenster nach vorn, Ergebnis in der Statuszeile (T) – A3
- [x] Punktezählung farbwechsel-sicher; Elo = −400·log10((1−p)/p), Kappung ±2000 (T)

## 14. Spielstand (Mensch vs. Computer)

- [x] Standard aus; An/Aus aktiviert 0-0 gegen aktuelle Stufe
- [x] Zählt normale Partien Mensch-Computer (Zuletzt-Zieher-Regel, korrekt bei Computer-Eröffnung und Vorgabestellungen) (T)
- [x] Zählt Match-Partien mit Mensch-Seite (je Gegnerstufe)
- [x] Stufenwechsel setzt den Stand der neuen Stufe auf 0-0

## 15. Hilfe-Dialog

- [x] Fenster 660×560, Titel „ConnectFour Studio – Hilfe“ (lokalisiert)
- [x] Inhaltsverzeichnis mit klickbaren Links, Querverweise, Sprung an den oberen Rand (T, S)
- [x] Überschriften blau/fett, Unterüberschriften, Fettdruck, Festschrift-Tabellen (Spielstärke, Kreuztabelle 14×14 in zwei Blöcken)
- [x] Stein-Icons (gelb/rot) oben
- [x] Suchleiste: Feld + Button, Strg+F, Enter = weiter, Groß/Klein egal, Wrap, gelbe Markierung, „nichts gefunden“ (T)
- [x] Textzoom A+/A−, Strg +/−/0, Strg+Mausrad (70 %–180 %), Prozentanzeige (T)
- [x] Nur lesbar, Kopieren erlaubt
- [~] Inhalte in 6 Sprachen – Texte unverändert bis auf „Tkinter“ → „Qt 6/PySide6“ und den Quicksave-Ort (A6)

## 16. Info-Dialog

- [~] Kopierbarer Text (Engine, Suchverfahren, GUI, Lizenz) in 6 Sprachen, Buttons Kopieren/Schließen (T) – A7

## 17. Sprachen

- [x] Alle UI-Texte über `cfs_lang` (`t`/`tf`), 6 Sprachen
- [x] Sprachwechsel zur Laufzeit beschriftet Menüs, Buttons, Rahmen, Info, Spielstand, Am-Zuge, Stufen und Set-Namen neu (T)
- [x] Startsprache: gespeicherte Wahl > Systemsprache (en → Englisch, sonst Deutsch) (T)
- [x] Zahlenformat je Sprache (Tausendertrenner, Dezimalkomma)

## 18. Dateien / Nutzerdaten

- [x] `.4gp` = Ziffernkette der Spalten 1–7 (ASCII, ohne Zeilenende); Laden ignoriert Fremdzeichen, illegale Züge und Züge nach Partieende (T, kompatibel zur Tk-Version)
- [~] Quicksave `quicksave.4gp`, Sprache `lang.cfg` (T) – A5/A6
- [~] Datei-Dialoge: Start im zuletzt benutzten Ordner bzw. Home, Filter lokalisiert (T) – A6

## 19. Packaging

- [x] Linux-AppImage mit eigenem Python (T: verify_appdir.py + Smoke-Test der AppImage)
- [~] Windows-Build-Vorbereitung (PyInstaller) – Spec unter Linux verifiziert, auf Windows noch ungetestet (offener Punkt)

## Abweichungen von der Tk-Version

Bewusste Änderungen (überwiegend Fehlerkorrekturen); alles andere verhält
sich wie im Original.

- **A1 Drop-Animation:** Während der Stein fällt, ist das Zielfeld noch leer.
  In der Tk-Version stand der Stein schon am Ziel, während eine Kopie fiel.
  Tasten/Klicks während der Animation werden ignoriert (Tk nahm Tasten an und
  konnte dabei zwei Animationen gleichzeitig starten).
- **A2 F6 nach „Neu“/Zufallsstellung:** bewertet jetzt sofort. In Tk brach die
  synchrone Bewertung am noch gesetzten Stop-Flag ab („Bewertung abgebrochen.“),
  u.a. direkt nach einer Zufallsstellung.
- **A3 Matchende:** Das Matchergebnis bleibt in der Statuszeile stehen. In Tk
  wurde es sofort von „Spielende: …“ überschrieben.
- **A4 Dauer-Analyse:** läuft nach Computerzügen auch bei ausgeschalteter
  Drop-Animation (in Tk nur mit Animation). Die Live-Knotenzahl nutzt den
  Tausendertrenner der Sprache (Tk: live immer Punkt).
- **A5 Einstellungen:** Neben der Sprache werden jetzt auch Ghost-Stein,
  Drop-Animation, letzter Zug, Stein-Set, Computer-Stufe und der letzte Ordner
  der Datei-Dialoge gemerkt (`settings.json`). Tk merkte sich nur die Sprache.
- **A6 Speicherorte:** `quicksave.4gp`, `lang.cfg`, `settings.json` liegen in
  `CFS_USER_DIR` bzw. `~/.config/connectfour-studio-qt` (Windows:
  `%APPDATA%\ConnectFour Studio Qt`) statt im Programmordner/`data/`. Datei-
  Dialoge starten im zuletzt benutzten Ordner, sonst im Home-Ordner (Tk:
  Arbeitsverzeichnis). Filterbezeichnungen und Qt-eigene Dialogtexte sind
  übersetzt. Schreibfehler beim Speichern werden gemeldet (Tk: unbehandelt).
- **A7 Info/Hilfe:** Info-Text ist nur lesbar (Tk: editierbar), Kopieren geht
  weiterhin. Hilfe und Info werden beim erneuten Aufruf nach vorn geholt statt
  ein weiteres Fenster zu öffnen. Beim Text-Zoom der Hilfe wird der Text neu
  gesetzt (eine Suchmarkierung verschwindet dabei).
- **A8 Escape:** schließt Menüs wie bisher; in Dialogen schließt Escape den
  Dialog (Qt-Standard, in Tk ohne Wirkung).
- **A9 Rechte Spalte:** feste Breite, Werte werden nicht mehr auf 11 Zeichen
  abgeschnitten; lange Namen im „Am Zuge“-Feld brechen um. Optik folgt dem
  Qt-Stil des Systems statt ttk.
- **Zufallsstellung:** Ein Suchergebnis, das erst nach „Stop“ eintrifft, wird
  verworfen (Tk wendete es trotzdem an).
- **AppImage:** ca. 68 MB statt 30 MB (Qt-Bibliotheken inkl. ICU statt Tk).
