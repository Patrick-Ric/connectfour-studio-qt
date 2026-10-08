"""PIL-Kacheln -> QPixmap mit LRU-Cache (Ersatz fuer cfs_sets.SetTiles)."""

from collections import OrderedDict

from PySide6.QtGui import QImage, QPixmap

from cfs_core import sets


def pil_to_qimage(im):
    """PIL-Bild -> eigenstaendiges QImage (RGBA8888)."""
    im = im.convert("RGBA")
    w, h = im.size
    data = im.tobytes("raw", "RGBA")
    return QImage(data, w, h, 4 * w, QImage.Format.Format_RGBA8888).copy()


class TileCache:
    """Skalierte Kacheln je (Set, Art, Groesse). Nur im GUI-Thread benutzen."""

    LIMIT = 400

    def __init__(self, raw):
        self.raw = raw
        self._cache = OrderedDict()

    def _get(self, key, build):
        pm = self._cache.get(key)
        if pm is None:
            pm = QPixmap.fromImage(pil_to_qimage(build()))
            self._cache[key] = pm
            while len(self._cache) > self.LIMIT:
                self._cache.popitem(last=False)
        else:
            self._cache.move_to_end(key)
        return pm

    def tile(self, set_no, kind, size):
        """'back', 'red', 'yellow', 'red_ghost', 'yellow_ghost' (size x size)."""
        return self._get(("tile", set_no, kind, size),
                         lambda: sets.render_tile(self.raw[set_no], kind, size, size))

    def stone(self, set_no, stone, size):
        """Einzelner Stein ohne Brett (Am-Zuge-Feld, Hilfe)."""
        return self._get(("stone", set_no, stone, size),
                         lambda: sets.render_stone(self.raw[set_no], stone, size))

    def stone_image(self, set_no, stone, size):
        return pil_to_qimage(sets.render_stone(self.raw[set_no], stone, size))

    def clear(self):
        self._cache.clear()
