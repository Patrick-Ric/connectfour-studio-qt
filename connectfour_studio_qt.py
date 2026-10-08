#!/usr/bin/env python3
"""ConnectFour Studio (Qt 6 / PySide6 + BitBully-Engine).

Rechenmotor: BitBully von Markus Thill (Python-Modul bitbully, C++-Kern).
Lizenz: GNU AGPL v3.

Start:  python3 connectfour_studio_qt.py [stellung.4gp]
"""

import sys

from cfs_qt.app import main

if __name__ == "__main__":
    sys.exit(main())
