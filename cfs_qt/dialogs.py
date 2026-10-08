"""Dialoge: Zufallsstellung, Computer-Computer Match, Info, Hilfe."""

import html

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import (QColor, QFontDatabase, QKeySequence, QShortcut,
                           QTextCharFormat, QTextCursor)
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox,
                               QComboBox, QDialog, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPlainTextEdit, QPushButton,
                               QRadioButton, QSpinBox, QTextBrowser,
                               QTextEdit, QVBoxLayout)

from cfs_core import help_content as hc
from cfs_core import lang as cfs_lang
from cfs_core import levels


def _button(text, slot):
    b = QPushButton(text)
    b.setAutoDefault(False)
    b.clicked.connect(slot)
    return b


# ---------------------------------------------------------------------------
# Neu mit Zufallsstellung
# ---------------------------------------------------------------------------
class RandomDialog(QDialog):
    """Steinzahl (1-9) + Wunsch-Ergebnis. result_value = (n, schluessel) mit
    internem deutschem Schluessel Egal/Gewinn/Unentschieden/Verlust."""

    WISH_KEYS = (("Egal", "new_random_any"), ("Gewinn", "new_random_win"),
                 ("Unentschieden", "new_random_draw"), ("Verlust", "new_random_loss"))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(cfs_lang.t("new_random_title"))
        self.result_value = None
        lay = QGridLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.addWidget(QLabel(cfs_lang.t("new_random_stones")), 0, 0)
        self.n_spin = QSpinBox()
        self.n_spin.setRange(1, 9)
        self.n_spin.setValue(3)
        lay.addWidget(self.n_spin, 0, 1, Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(QLabel(cfs_lang.t("new_random_result")), 1, 0)
        self.w_combo = QComboBox()
        for key, lab in self.WISH_KEYS:
            self.w_combo.addItem(cfs_lang.t(lab), key)
        self.w_combo.setCurrentIndex(1)  # Gewinn
        lay.addWidget(self.w_combo, 1, 1, Qt.AlignmentFlag.AlignLeft)
        hint = QLabel(cfs_lang.t("new_random_hint"))
        hint.setStyleSheet("color: grey;")
        lay.addWidget(hint, 2, 0, 1, 2)
        row = QHBoxLayout()
        row.addStretch(1)
        ok = QPushButton(cfs_lang.t("btn_ok"))
        ok.setDefault(True)
        ok.clicked.connect(self._ok)
        row.addWidget(ok)
        row.addWidget(_button(cfs_lang.t("btn_cancel"), self.reject))
        row.addStretch(1)
        lay.addLayout(row, 3, 0, 1, 2)

    def _ok(self):
        self.result_value = (self.n_spin.value(), self.w_combo.currentData())
        self.accept()


# ---------------------------------------------------------------------------
# Computer-Computer Match
# ---------------------------------------------------------------------------
class MatchDialog(QDialog):
    """Nicht-modales Match-Fenster: Einstellungen, Live-Stand, Endergebnis."""

    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.setWindowTitle(cfs_lang.t("match_title"))
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(470, 700)
        lay = QGridLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setVerticalSpacing(6)

        self.names = [("mensch", cfs_lang.t("level_human"))]
        self.names += [(k, levels.stufe_label_for(k)) for k in levels.STUFEN_ORDER]
        self.names += [("user1", levels.USER_LABEL_1 + cfs_lang.t("user_own_psw")),
                       ("user2", levels.USER_LABEL_2 + cfs_lang.t("user_own_psw"))]

        pre_g, pre_r, n_txt, wechsel, tempo = "leicht", "mittel", "20", True, "normal"
        m = main.match
        if m is not None and m.running:
            pre_g, pre_r = m.gelb, m.rot
            n_txt, wechsel = str(m.spiele), m.wechsel
            tempo = "turbo" if m.blind else ("schnell" if m.schnell else "normal")

        lay.addWidget(QLabel(cfs_lang.t("label_yellow")), 0, 0)
        lay.addWidget(QLabel(cfs_lang.t("label_red")), 1, 0)
        lay.addWidget(QLabel(cfs_lang.t("match_games")), 2, 0)
        self.cb_g = self._combo(pre_g)
        self.cb_r = self._combo(pre_r)
        lay.addWidget(self.cb_g, 0, 1, Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(self.cb_r, 1, 1, Qt.AlignmentFlag.AlignLeft)
        self.n_edit = QLineEdit(n_txt)
        self.n_edit.setFixedWidth(self.fontMetrics().horizontalAdvance("0") * 10)
        lay.addWidget(self.n_edit, 2, 1, Qt.AlignmentFlag.AlignLeft)
        self.swap = QCheckBox(cfs_lang.t("match_swap"))
        self.swap.setChecked(wechsel)
        lay.addWidget(self.swap, 3, 0, 1, 2)
        lay.addWidget(QLabel(cfs_lang.t("match_tempo")), 4, 0)
        tbox = QHBoxLayout()
        self.tempo_group = QButtonGroup(self)
        self.tempo_buttons = {}
        for key, lab in (("normal", "tempo_normal"), ("schnell", "tempo_fast"),
                         ("turbo", "tempo_turbo")):
            rb = QRadioButton(cfs_lang.t(lab))
            self.tempo_group.addButton(rb)
            self.tempo_buttons[key] = rb
            tbox.addWidget(rb)
        tbox.addStretch(1)
        self.tempo_buttons[tempo].setChecked(True)
        lay.addLayout(tbox, 4, 1)

        u1 = levels.user_psw("user1")
        u2 = levels.user_psw("user2")
        self.psw1 = self._psw_row(lay, 5, "User (1) p,s,w:", u1)
        self.psw2 = self._psw_row(lay, 6, "User (2) p,s,w:", u2)
        hint = QLabel(cfs_lang.t("match_hint"))
        hint.setWordWrap(True)
        lay.addWidget(hint, 7, 0, 1, 2)
        self.stand_label = QLabel("")
        self.stand_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.stand_label, 8, 0, 1, 2)
        lay.addWidget(QLabel(cfs_lang.t("match_result_label")), 9, 0, 1, 2)
        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        self.result.setFixedHeight(self.fontMetrics().lineSpacing() * 5 + 12)
        lay.addWidget(self.result, 10, 0, 1, 2)
        brow = QHBoxLayout()
        brow.addStretch(1)
        brow.addWidget(_button(cfs_lang.t("btn_start"), self._start))
        brow.addWidget(_button(cfs_lang.t("btn_stop"), main.stop))
        brow.addWidget(_button(cfs_lang.t("btn_copy"), self._copy))
        brow.addWidget(_button(cfs_lang.t("btn_close"), self.close))
        brow.addStretch(1)
        lay.addLayout(brow, 11, 0, 1, 2)
        lay.setRowStretch(12, 1)
        lay.setColumnStretch(1, 1)

        self.cb_g.currentIndexChanged.connect(self._umode_flip)
        self.cb_r.currentIndexChanged.connect(self._umode_flip)
        self._umode_flip()
        self.refresh()

    def _combo(self, pre):
        cb = QComboBox()
        cb.setMaxVisibleItems(19)
        for key, name in self.names:
            cb.addItem(name, key)
        idx = cb.findData(pre)
        cb.setCurrentIndex(idx if idx >= 0 else 0)
        cb.setMinimumContentsLength(26)
        return cb

    def _psw_row(self, lay, row, label, psw):
        lay.addWidget(QLabel(label), row, 0)
        box = QHBoxLayout()
        edits = []
        for v in psw:
            e = QLineEdit(str(v))
            e.setFixedWidth(self.fontMetrics().horizontalAdvance("0") * 6)
            box.addWidget(e)
            edits.append(e)
        box.addStretch(1)
        lay.addLayout(box, row, 1)
        return edits

    def side_keys(self):
        return self.cb_g.currentData(), self.cb_r.currentData()

    def _umode_flip(self, *_a):
        """User-Felder je KEY aktivieren: Feld (1) <-> 'user1', (2) <-> 'user2'."""
        g, r = self.side_keys()
        for e in self.psw1:
            e.setEnabled("user1" in (g, r))
        for e in self.psw2:
            e.setEnabled("user2" in (g, r))

    def _start(self):
        m = self.main.match
        if m is not None and m.running:
            return
        g, r = self.side_keys()
        if "user1" in (g, r):
            levels.set_user_psw("user1", levels.parse_psw(*(e.text() for e in self.psw1)))
        if "user2" in (g, r):
            levels.set_user_psw("user2", levels.parse_psw(*(e.text() for e in self.psw2)))
        try:
            n = max(1, min(10000, int(self.n_edit.text().strip())))
        except ValueError:
            n = 20
        tempo = next(k for k, b in self.tempo_buttons.items() if b.isChecked())
        self.main._match_start(g, r, n, self.swap.isChecked(),
                               schnell=(tempo == "schnell"), blind=(tempo == "turbo"))

    def _copy(self):
        QApplication.clipboard().setText(self.result.toPlainText())

    def refresh(self):
        """Live-Stand + Endergebnis aus main.match."""
        m = self.main.match
        if m is None:
            self.stand_label.setText(cfs_lang.t("match_none"))
            self.result.setPlainText(cfs_lang.t("match_no_result"))
            return
        self.stand_label.setText(m.live_text())
        self.result.setPlainText(m.result_text())

    def bring_to_front(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.raise_()
        self.activateWindow()

    def closeEvent(self, ev):
        self.main._match_win_closed(self)
        super().closeEvent(ev)


# ---------------------------------------------------------------------------
# Info
# ---------------------------------------------------------------------------
class InfoDialog(QDialog):
    def __init__(self, parent, lang):
        super().__init__(parent)
        lang = lang if lang in hc.HELP_LANGS else "de"
        self.lang = lang
        self.setWindowTitle(cfs_lang.t("info_title", lang))
        self.resize(560, 260)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)  # markierbar + kopierbar
        self.text.setPlainText(hc.INFO_TEXT[lang])
        lay.addWidget(self.text)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(_button(hc.ui_text("copy", lang),
                              lambda: QApplication.clipboard().setText(self.text.toPlainText())))
        row.addWidget(_button(hc.ui_text("close", lang), self.close))
        row.addStretch(1)
        lay.addLayout(row)


# ---------------------------------------------------------------------------
# Hilfe
# ---------------------------------------------------------------------------
def mono_family():
    fams = set(QFontDatabase.families())
    for name in ("DejaVu Sans Mono", "Liberation Mono", "Courier New", "Courier"):
        if name in fams:
            return name
    return QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()


def build_help_html(lang, factor=1.0, mono=None):
    """HELP_CONTENT einer Sprache als HTML (Anker = <a name>, Links = #ziel)."""
    items = hc.HELP_CONTENT.get(lang, hc.HELP_CONTENT["de"])
    mono = mono or "DejaVu Sans Mono"
    sz = {k: max(lo, round(base * factor)) for k, (base, lo) in
          {"body": (10, 7), "h": (13, 8), "sh": (11, 8), "mono": (9, 7)}.items()}
    esc = html.escape
    out = [f'<html><body style="font-size:{sz["body"]}pt;">',
           '<p><img src="cfs:yellow" width="22" height="22">&nbsp;&nbsp;'
           '<img src="cfs:red" width="22" height="22"></p>']

    def pre(text):
        return (f'<pre style="font-family:\'{mono}\'; font-size:{sz["mono"]}pt;">'
                f'{esc(text)}</pre>')

    for kind, *rest in items:
        if kind in ("head", "sub"):
            name, title = rest
            size = sz["h"] if kind == "head" else sz["sh"]
            out.append(f'<p style="margin-top:12px; margin-bottom:4px;"><a name="{esc(name)}"></a>'
                       f'<span style="font-size:{size}pt; font-weight:bold; color:#1e3a8a;">'
                       f'{esc(title)}</span></p>')
        elif kind == "para":
            parts = []
            for p in rest:
                if isinstance(p, tuple):
                    if len(p) == 3 and p[0] == "LINK":
                        _, text, target = p
                        parts.append(f'<a href="#{esc(target)}" style="color:blue; '
                                     f'text-decoration:underline;">{esc(text)}</a>')
                    elif len(p) == 2:
                        text, tag = p
                        tags = tag if isinstance(tag, (list, tuple)) else (tag,)
                        t = esc(text)
                        if "b" in tags:
                            t = f"<b>{t}</b>"
                        parts.append(t)
                    else:
                        parts.append(esc(str(p)))
                else:
                    parts.append(esc(p))
            out.append("<p>" + "".join(parts) + "</p>")
        elif kind == "mono":
            out.append(pre(rest[0] if rest else ""))
        elif kind == "table":
            if rest and rest[0] == "kreuz14":
                out.append(pre(hc.kreuz_block([1, 2, 3, 4, 5, 6, 7], lang)))
                out.append(pre(hc.kreuz_block([8, 9, 10, 11, 12, 13, 14], lang)))
            else:
                out.append(pre(str(rest[0] if rest else "")))
    out.append("</body></html>")
    return "\n".join(out)


class HelpBrowser(QTextBrowser):
    """QTextBrowser mit eingebetteten Stein-Bildern (cfs:yellow/red) und
    Strg+Mausrad -> Zoom-Callback."""

    def __init__(self, images, on_zoom, parent=None):
        super().__init__(parent)
        self._images = images
        self._on_zoom = on_zoom

    def loadResource(self, rtype, url):
        if url.scheme() == "cfs" and url.path() in self._images:
            return self._images[url.path()]
        return super().loadResource(rtype, url)

    def wheelEvent(self, ev):
        if ev.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._on_zoom(+1 if ev.angleDelta().y() > 0 else -1)
            ev.accept()
            return
        super().wheelEvent(ev)


class HelpDialog(QDialog):
    def __init__(self, parent, lang, images):
        super().__init__(parent)
        self.lang = lang if lang in hc.HELP_LANGS else "de"
        self.setWindowTitle(hc.ui_text("help_title", self.lang))
        self.resize(660, 560)
        self.factor = 1.0
        self.mono = mono_family()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        bar = QHBoxLayout()
        bar.addWidget(QLabel(hc.ui_text("find_label", self.lang)))
        self.find_edit = QLineEdit()
        self.find_edit.setFixedWidth(self.fontMetrics().horizontalAdvance("x") * 30)
        self.find_edit.returnPressed.connect(self.find_next)
        bar.addWidget(self.find_edit)
        self.find_info = QLabel("")
        bar.addWidget(self.find_info)
        bar.addWidget(_button(hc.ui_text("find_btn", self.lang), self.find_next))
        b_in = _button("A+", lambda: self.zoom(+1))
        b_out = _button("A-", lambda: self.zoom(-1))
        for b in (b_in, b_out):
            b.setFixedWidth(self.fontMetrics().horizontalAdvance("A+") + 24)
        bar.addSpacing(8)
        bar.addWidget(b_in)
        bar.addWidget(b_out)
        self.zoom_info = QLabel("100%")
        self.zoom_info.setMinimumWidth(self.fontMetrics().horizontalAdvance("180%") + 6)
        bar.addWidget(self.zoom_info)
        bar.addStretch(1)
        lay.addLayout(bar)
        self.text = HelpBrowser(images, self.zoom)
        self.text.setOpenLinks(False)
        self.text.anchorClicked.connect(self.goto)
        lay.addWidget(self.text)
        for seq, fn in (("Ctrl+F", self.focus_find),
                        ("Ctrl++", lambda: self.zoom(+1)), ("Ctrl+=", lambda: self.zoom(+1)),
                        ("Ctrl+-", lambda: self.zoom(-1)), ("Ctrl+0", lambda: self.zoom(0))):
            QShortcut(QKeySequence(seq), self, activated=fn)
        self._render()

    def _render(self, keep_pos=False):
        sb = self.text.verticalScrollBar()
        frac = (sb.value() / sb.maximum()) if (keep_pos and sb.maximum() > 0) else 0.0
        self.text.setHtml(build_help_html(self.lang, self.factor, self.mono))
        self.zoom_info.setText(f"{round(self.factor * 100)}%")
        if keep_pos:
            sb.setValue(int(frac * sb.maximum()))

    def zoom(self, direction):
        """+1 / -1 in 10-%-Schritten (70-180 %), 0 = 100 %."""
        if direction > 0:
            self.factor = min(1.8, round(self.factor + 0.1, 2))
        elif direction < 0:
            self.factor = max(0.7, round(self.factor - 0.1, 2))
        else:
            self.factor = 1.0
        self._render(keep_pos=True)

    def goto(self, url):
        name = url.fragment() if isinstance(url, QUrl) else str(url)
        if name:
            self.text.scrollToAnchor(name)

    def focus_find(self):
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def find_next(self):
        """Vorwaerts ab Cursor suchen (Gross/Klein egal), Wrap, gelb markieren."""
        needle = self.find_edit.text()
        self.text.setExtraSelections([])
        if not needle:
            self.find_info.setText("")
            return
        doc = self.text.document()
        hit = doc.find(needle, self.text.textCursor())
        if hit.isNull():
            hit = doc.find(needle, 0)
        if hit.isNull():
            self.find_info.setText(hc.ui_text("not_found", self.lang))
            return
        sel = QTextEdit.ExtraSelection()
        sel.cursor = hit
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("yellow"))
        sel.format = fmt
        self.text.setExtraSelections([sel])
        cur = QTextCursor(hit)
        cur.setPosition(hit.selectionEnd())
        self.text.setTextCursor(cur)
        self.text.ensureCursorVisible()
        self.find_info.setText("")
        self.find_edit.setFocus()
