# ConnectFour Studio – Feature-Liste (Tk-Original → Qt-Port)

Quelle: `connectfour_studio.py`, `cfs_help.py`, `cfs_lang.py`, `cfs_levels.py`,
`cfs_sets.py` der Tkinter-Version (Stand 04.10.2026).
Status: `[ ]` offen · `[x]` in der Qt-Version vorhanden und geprüft ·
`[~]` vorhanden mit dokumentierter Abweichung (siehe Spalte „Hinweis“).

## 1. Hauptfenster / Layout

- [ ] Fenstertitel „ConnectFour Studio“
- [ ] Brett links (7×6 Kacheln aus dem gewählten Stein-Set), Brett klebt oben
- [ ] Wertungszeile direkt unter dem Brett (44 px hoch, pixelgenau unter den Spalten, 1-px-Trennlinien)
- [ ] Wertungszeile ohne Analyse: Spaltennummern 1–7 (graue Felder), volle Spalte „X“
- [ ] Wertungszeile mit Analyse: oben fett `+`/`=`/`-`, darunter Steinzahl bis Ende; grün/gelb/rot (Pastell)
- [ ] Klick in die Wertungszeile führt den Spaltenzug aus (4-px-Lücke dazwischen ignoriert)
- [ ] Buttonleiste unter dem Brett: genau 7 gleich breite Buttons (Neu, <<, <, >, >>, Ziehen, Analyse), exakt Brettbreite
- [ ] Rechte Seite: Feld „Am Zuge“ (Stein-Icon + Name: Mensch / Stufenname inkl. (p,s,w) / Match-Seite)
- [ ] Feld „Info“: Zug, Stufe, Tiefe, Wert, Knoten, Zeit, Tempo, Quelle
- [ ] Feld „Spielstand“ (immer sichtbar): Kopf „Mensch vs X“, großes Ergebnis (4×), (+/=/-)·Partien, Elo (erst ab ≥0,5 Punkten je Seite), Buttons An/Aus + Reset
- [ ] Statuszeile unten (eingesunken), Start „Bereit.“
- [ ] Natürliche Startgröße (Zoom 0,30 der 256-px-Kacheln), danach Auto-Zoom mit der Fenstergröße (Zoom 0,08 … 4,0)
- [ ] Optionales Startargument: `.4gp`-Datei wird geladen und sofort bewertet

## 2. Brett-Darstellung / Animationen

- [ ] Kacheln aus HiRes-PNG (Fallback BMP), Lanczos-skaliert
- [ ] Ghost-Stein (halbtransparente Vorschau über der Zielspalte, Farbe des Spielers am Zug)
- [ ] Drop-Animation (Stein fällt zeilenweise, 16 ms je Zeile)
- [ ] Letzter Zug: weißer Ring knapp außerhalb der Steinkante (Radius je Farbe vermessen)
- [ ] Gewinnreihe(n): grüner Außen- + weißer Innenring an allen Steinen der 4er(+)-Reihe
- [ ] Stein-Radien je Set automatisch vermessen (Floodfill, Differenz-Deckel, Ring-Test)

## 3. Menü „Datei“

- [ ] Neues Spiel
- [ ] Neu mit Zufallsstellung… (Dialog)
- [ ] Stellung laden… (.4gp, Dateidialog)
- [ ] Stellung speichern… (.4gp, Standard-Endung .4gp)
- [ ] Schnell speichern (F3) – ohne Dialog in `quicksave.4gp`
- [ ] Schnell laden (F4) – ohne Dialog; Meldung, wenn nichts gespeichert
- [ ] Ende

## 4. Menü „Ansicht“

- [ ] Ghost-Stein (Haken, Standard an)
- [ ] Drop-Animation (Haken, Standard an)
- [ ] letzten Zug zeigen (Haken, Standard an)
- [ ] Spielstand ein/aus (Haken, synchron mit Button An/Aus)
- [ ] Spielstand reset

## 5. Menü „Einstellungen“

- [ ] Computer-Stufe (Untermenü, Radio): 0 Verlierer, 1 Zufall … 14 Perfekt (Standard Perfekt)
- [ ] Mensch-Computer (Radio, Standard) – zieht sofort, wenn der Computer am Zug ist
- [ ] 2-Spieler (beide Mensch) (Radio)
- [ ] Computer-Computer (ausspielen) (Radio) – Perfekt gegen sich selbst bis Partieende, 350 ms Pause
- [ ] Computer-Computer Match… (Dialog)
- [ ] Stop Auto Play
- [ ] vorheriges Set (Bild hoch) / nächstes Set (Bild runter) – oben im Set-Block
- [ ] 20 Stein-Sets als Radio-Einträge „Stein-Set N – Name“ (lokalisierte Namen)

## 6. Menü „Kommandos“

- [ ] erster Zug (Pfeil hoch)
- [ ] Zug zurück (Pfeil links)
- [ ] Zug vor (Pfeil rechts)
- [ ] letzter Zug (Pfeil runter)
- [ ] ziehen (Computer) (F5) – auch bei leerem Brett (Computer eröffnet, Mensch wird Rot)
- [ ] alle Züge bewerten (1x) (F6) – Umschalter (2. Aufruf: zurück zu 1–7)
- [ ] Dauer-Analyse (F7) – Umschalter, synchron mit Button „Analyse“

## 7. Menü „Hilfe“

- [ ] Inhalt (F1) – Hilfedialog
- [ ] Info – Info-Dialog (kopierbar)
- [ ] Sprache (Untermenü, Radio): Deutsch, English, Français, Español, Nederlands, Italiano; Wahl wird gemerkt

## 8. Tastenkürzel (nur im Hauptfenster, nicht in Dialogen/Eingabefeldern)

- [ ] 1–7 Spaltenzug
- [ ] Pfeil links/rechts Zug zurück/vor
- [ ] Pfeil hoch/runter erster/letzter Zug
- [ ] Bild hoch/runter Set wechseln (Wrap-around)
- [ ] Mausrad über dem Brett Set wechseln (hoch = vorheriges)
- [ ] F1 Hilfe, F3/F4 Schnell speichern/laden, F5 ziehen, F6 alle bewerten, F7 Dauer-Analyse
- [ ] Escape schließt ein offenes Menü
- [ ] F10 öffnet kein Menü (neutralisiert)

## 9. Spielmodi / Ablauf

- [ ] Mensch-Computer: nach Menschenzug antwortet der Computer automatisch
- [ ] Zugsperre während der Computer denkt („Computer denkt noch – bitte warten.“)
- [ ] Navigation gesperrt während Denken/Selbstspiel/Match (mit Statusmeldung)
- [ ] Ergebnis eines Computerzugs wird verworfen, wenn sich die Stellung inzwischen geändert hat
- [ ] Stop: bricht Engine-Zug, Selbstspiel, Match und Analyse ab („Angehalten …“)
- [ ] Neues Spiel / Laden während des Denkens stoppt zuerst
- [ ] Partieende: Statuszeile „Spielende: Gelb/Rot gewinnt! / Unentschieden!“, Wert-Feld ebenso
- [ ] Selbstspiel endet am Partieende automatisch (Modus zurück auf Mensch-Computer)

## 10. KI / Stufen (BitBully-Engine)

- [ ] Engine BitBully, Eröffnungsbuch fest `12-ply-dist`
- [ ] Iterative Vertiefung 4, 6, 8 … 20, Voll; Live-Anzeige Tiefe/Knoten/Zeit/Tempo
- [ ] 14 Stufen (p, s, w) laut Tabelle + 0 Verlierer + Zufall-Sonderfall
- [ ] Siegsschutz w (kurzer Gewinn ml ≤ 2w−1 geht immer vor)
- [ ] Verlustschutz s (Patzer tabu, wenn ml ≤ 2s; sonst längster Widerstand)
- [ ] Perfekt: schnellster Gewinn (≤10 Halbzüge), Remis/Gewinn-Varianz, Verluststellung: schnelle Niederlagen vermeiden
- [ ] Verluststellung (andere Stufen): gewichtete Wahl Verlustlänge^8
- [ ] Verlierer: zufälliger Verlustzug, sonst Remis, sonst Zufall
- [ ] Analyse (F6/F7) immer perfekt
- [ ] Info „Quelle“: „Buch 12d“ bis 12 Steine, danach „berechnet“; „Tiefe“: letzte Iterationstiefe

## 11. Dauer-Analyse

- [ ] Hintergrundanalyse nach jedem Stellungswechsel, neueste Stellung gewinnt
- [ ] Live-Näherung je Tiefe („Tiefe 8…“), am Ende Status „Analyse: Spalte X (+n) in t s.“
- [ ] Veraltete Ergebnisse werden verworfen (Sequenznummer + Stellungs-Snapshot)

## 12. Dialog „Neu mit Zufallsstellung“

- [ ] Steine 1–9 (Standard 3), Ergebnis Egal/Gewinn/Unentschieden/Verlust (Standard Gewinn), Hinweis grau
- [ ] Suche im Hintergrund (bis 400 Kandidaten, Prüfung per mtdf), Status „Suche Zufallsstellung …“
- [ ] Danach: Mensch spielt die Farbe des nächsten Zugs, Stellung wird sofort bewertet

## 13. Dialog „Computer-Computer Match“

- [ ] Nicht-modales Fenster (470×700), erneutes Öffnen holt es nach vorn
- [ ] Gelb/Rot: Mensch, Stufen 0–14, User (1)/(2) (eigene p,s,w)
- [ ] Partien 1–10000 (Standard 20), Farbwechsel nach jeder Partie (Standard an)
- [ ] Tempo Normal (350 ms) / Schnell (0 ms, keine Animation) / Nur Ergebnisse (Turbo, kein Zeichnen pro Zug, TT bleibt)
- [ ] User-(p,s,w)-Felder nur aktiv, wenn der jeweilige User-Key gewählt ist (p 0–100, s/w 0–9)
- [ ] Hinweistext zu p/s/w
- [ ] Live-Stand (Partie, Status, Punkte, Elo), kopierbares Endergebnis
- [ ] Buttons Start, Stop, Kopieren, Schließen (Match läuft beim Schließen weiter)
- [ ] Mit Mensch-Seite: kein Turbo, Mensch zieht per Klick/Taste, 3 s Pause zwischen Partien (auch bei Tempo Normal)
- [ ] Statuszeile „Computer-Computer Match n/N | Gelb (…) - Rot (…) | Stand | Elo“
- [ ] Matchende: Fenster nach vorn, Ergebnis in der Statuszeile
- [ ] Punktezählung farbwechsel-sicher; Elo = −400·log10((1−p)/p), Kappung ±2000

## 14. Spielstand (Mensch vs. Computer)

- [ ] Standard aus; An/Aus aktiviert 0-0 gegen aktuelle Stufe
- [ ] Zählt normale Partien Mensch-Computer (Zuletzt-Zieher-Regel, korrekt bei Computer-Eröffnung und Vorgabestellungen)
- [ ] Zählt Match-Partien mit Mensch-Seite (je Gegnerstufe)
- [ ] Stufenwechsel setzt den Stand der neuen Stufe auf 0-0

## 15. Hilfe-Dialog

- [ ] Fenster 660×560, Titel „ConnectFour Studio – Hilfe“ (lokalisiert)
- [ ] Inhaltsverzeichnis mit klickbaren Links, Querverweise, Sprung an den oberen Rand
- [ ] Überschriften blau/fett, Unterüberschriften, Fettdruck, Festschrift-Tabellen (Spielstärke, Kreuztabelle 14×14 in zwei Blöcken)
- [ ] Stein-Icons (gelb/rot) oben
- [ ] Suchleiste: Feld + Button, Strg+F, Enter = weiter, Groß/Klein egal, Wrap, gelbe Markierung, „nichts gefunden“
- [ ] Textzoom A+/A−, Strg +/−/0, Strg+Mausrad (70 %–180 %), Prozentanzeige
- [ ] Nur lesbar, Kopieren erlaubt
- [ ] Inhalte in 6 Sprachen

## 16. Info-Dialog

- [ ] Kopierbarer Text (Engine, Suchverfahren, GUI, Lizenz) in 6 Sprachen, Buttons Kopieren/Schließen

## 17. Sprachen

- [ ] Alle UI-Texte über `cfs_lang` (`t`/`tf`), 6 Sprachen
- [ ] Sprachwechsel zur Laufzeit beschriftet Menüs, Buttons, Rahmen, Info, Spielstand, Am-Zuge, Stufen und Set-Namen neu
- [ ] Startsprache: gespeicherte Wahl > Systemsprache (en → Englisch, sonst Deutsch)
- [ ] Zahlenformat je Sprache (Tausendertrenner, Dezimalkomma)

## 18. Dateien / Nutzerdaten

- [ ] `.4gp` = Ziffernkette der Spalten 1–7 (ASCII, ohne Zeilenende); Laden ignoriert Fremdzeichen, illegale Züge und Züge nach Partieende
- [ ] Quicksave `quicksave.4gp`, Sprache `lang.cfg`
- [ ] Datei-Dialoge

## 19. Packaging

- [ ] Linux-AppImage mit eigenem Python
- [ ] Windows-Build-Vorbereitung (PyInstaller)
