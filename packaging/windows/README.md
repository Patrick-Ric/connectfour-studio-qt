# Windows-Build (PyInstaller)

Auf einem Windows-Rechner mit 64-bit Python 3.10–3.14 im Projektordner:

```bat
packaging\windows\build_windows.bat
```

Das Skript

1. legt eine eigene Build-Umgebung an (`build\winvenv`) und installiert
   `requirements.txt` + PyInstaller,
2. ruft `prepare_build.py` auf: kopiert Programm und Bilder nach `build\src`
   und erzeugt das Icon `connectfour-studio-qt.ico` (gleiches Motiv wie bisher),
3. baut mit `connectfour_studio_qt.spec` ein Programmverzeichnis:
   `dist\ConnectFour Studio Qt\ConnectFour Studio Qt.exe`.

Hinweise:

- Eingebunden werden nur QtCore, QtGui und QtWidgets (plus die vom
  PySide6-Hook gesammelten Plugins) und vom Eröffnungsbuch nur `12-ply-dist`.
- Quicksave, Sprachwahl und Einstellungen landen in
  `%APPDATA%\ConnectFour Studio Qt` (oder in `CFS_USER_DIR`, falls gesetzt) –
  das Programmverzeichnis darf schreibgeschützt sein (z.B. `C:\Program Files`).
- Gegenüber der Tk-Version müssen die Quellen nicht mehr gepatcht werden;
  `cfs_core/paths.py` erkennt den gepackten Betrieb (`sys._MEIPASS`).
- Ein-Datei-Build (`--onefile`) ist möglich, entpackt aber bei jedem Start
  ~100 MB in einen Temp-Ordner; daher ist das Verzeichnis-Build Standard.
- Selbsttest des fertigen Builds: `set CFS_SMOKE_TEST=1` und die .exe starten
  (öffnet alle Dialoge, rechnet einen Zug, beendet sich; Exit-Code 0 = OK).
