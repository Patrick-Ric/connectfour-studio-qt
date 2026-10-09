"""GUI-unabhaengiger Kern von ConnectFour Studio.

Module:
  paths         Programm-/Benutzerpfade, settings.json
  lang          UI-Texte in 6 Sprachen (bisheriges cfs_lang)
  levels        Stufen (p,s,w), Namen, Elo
  sets          Stein-Sets (PIL): Namen, Vermessung, Kachel-Rendering
  game          Brett/Verlauf, .4gp-Format, Gewinnreihen
  engine        BitBully: Bewertung, Zugwahl, Zufallsstellungen
  match         Match-Zaehlung und Spielstand Mensch vs. Computer
  help_content  Hilfe-/Info-Texte (bisheriges cfs_help, nur Daten)
"""

APP_NAME = "ConnectFour Studio"
APP_VERSION = "2.1.0"
ENGINE_NAME = "BitBully von Markus Thill"
