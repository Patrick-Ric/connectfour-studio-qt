"""Programm-Icon erzeugen (Design wie packaging/windows der Tk-Version).

Aufruf: python packaging/make_icon.py [ziel.png|ziel.ico ...]
Ohne Argument: data/connectfour-studio.png (256x256).
"""
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def make_icon():
    im = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, 248, 248), radius=36, fill=(30, 80, 190, 255))
    R, Y, W = (230, 40, 40), (245, 200, 30), (235, 240, 250)
    grid = [[W, W, W, W], [W, W, Y, W], [W, R, Y, W], [R, R, Y, R]]
    for r in range(4):
        for c in range(4):
            x, y = 22 + c * 56, 22 + r * 56
            d.ellipse((x, y, x + 44, y + 44), fill=grid[r][c] + (255,))
    return im


def main(targets):
    im = make_icon()
    for t in targets or [os.path.join(ROOT, "data", "connectfour-studio.png")]:
        if t.lower().endswith(".ico"):
            im.save(t, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        else:
            im.save(t)
        print("Icon:", t)


if __name__ == "__main__":
    main(sys.argv[1:])
