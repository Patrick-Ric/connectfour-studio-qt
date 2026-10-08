"""Taste mit deutlicher Hover-Anzeige (wie die aktiven Tk-Tasten).

Der Qt-Stil "Fusion" zeichnet Tasten bereits fast weiss und zeigt beim
Ueberfahren kaum einen Unterschied. HoverButton legt deshalb unter die
Beschriftung eine helle Toenung in der Hervorhebungsfarbe des Systems und
zieht den Rand in dieser Farbe nach. Die Tastengrafik des Stils bleibt
erhalten; gedrueckt/deaktiviert zeichnet der Stil wie gewohnt.
"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QPushButton, QStyle, QStyleOptionButton, QStylePainter

HOVER_FILL_ALPHA = 45     # Deckkraft der Toenung (0-255)
HOVER_BORDER_ALPHA = 200  # Deckkraft des Randes


class HoverButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hovered = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def enterEvent(self, ev):
        self.hovered = True
        self.update()
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        self.hovered = False
        self.update()
        super().leaveEvent(ev)

    def paintEvent(self, ev):
        p = QStylePainter(self)
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        p.drawControl(QStyle.ControlElement.CE_PushButtonBevel, opt)
        if self.hovered and self.isEnabled() and not self.isDown():
            hl = QColor(self.palette().highlight().color())
            fill = QColor(hl)
            fill.setAlpha(HOVER_FILL_ALPHA)
            border = QColor(hl)
            border.setAlpha(HOVER_BORDER_ALPHA)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setPen(QPen(border, 1))
            p.setBrush(fill)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 2.5, 2.5)
        label = QStyleOptionButton(opt)
        label.rect = self.style().subElementRect(QStyle.SubElement.SE_PushButtonContents, opt, self)
        p.drawControl(QStyle.ControlElement.CE_PushButtonLabel, label)
