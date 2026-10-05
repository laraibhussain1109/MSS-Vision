"""PyQt6 desktop front-end for the legal consultancy chatbot."""
from __future__ import annotations

import html
import re
import sys
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QFileDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from engine import LegalBot, Reply

STYLE = """
QMainWindow, QWidget#root { background: #f8fafc; }
QLabel#title { font-size: 20px; font-weight: 700; color: #0f172a; }
QLabel#subtitle { color: #64748b; font-size: 12px; }
QLabel#banner { background: #fef3c7; color: #78350f; padding: 6px 16px; font-size: 12px;
                border-top: 1px solid #fde68a; border-bottom: 1px solid #fde68a; }
QScrollArea { border: none; background: #f8fafc; }
QWidget#chatContainer { background: #f8fafc; }
QLabel#userBubble { background: #2563eb; color: white; border-radius: 14px; padding: 10px 14px; }
QLabel#botBubble { background: white; color: #0f172a; border: 1px solid #e2e8f0;
                   border-radius: 14px; padding: 10px 14px; }
QLabel#urgentBubble { background: #fef2f2; color: #7f1d1d; border: 1px solid #fecaca;
                      border-radius: 14px; padding: 10px 14px; }
QLineEdit { background: white; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 18px;
            padding: 9px 16px; font-size: 14px; }
QLineEdit:focus { border-color: #2563eb; }
QPushButton#send { background: #2563eb; color: white; border: none; border-radius: 18px;
                   padding: 10px 22px; font-weight: 600; }
QPushButton#send:hover { background: #1d4ed8; }
QPushButton#send:disabled { background: #94a3b8; }
QPushButton#chip { background: white; color: #1d4ed8; border: 1px solid #bfdbfe;
                   border-radius: 14px; padding: 6px 14px; text-align: left; }
QPushButton#chip:hover { background: #eff6ff; }
"""

BOT_STYLES = {"user": "userBubble", "bot": "botBubble", "urgent": "urgentBubble"}


def to_html(text: str) -> str:
    """Convert the bot's light markdown (**bold**, _italic_, newlines) to Qt rich text."""
    s = html.escape(text)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", s)
    return s.replace("\n", "<br>")


class Bubble(QWidget):
    """One chat message: a rounded, word-wrapped label aligned left or right."""

    def __init__(self, text: str, kind: str):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 4, 8, 4)
        self.label = QLabel(to_html(text))
        self.label.setObjectName(BOT_STYLES[kind])
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if kind == "user":
            row.addStretch()
            row.addWidget(self.label)
        else:
            row.addWidget(self.label)
            row.addStretch()

    def set_max_width(self, width: int) -> None:
        self.label.setMaximumWidth(width)


class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bot = LegalBot()
        self.history: list[tuple[str, str, str]] = []   # (time, speaker, text)
        self.bubbles: list[Bubble] = []
        self.typing: Bubble | None = None
        self.busy = False

        self.setWindowTitle("Legal Consultancy Assistant")
        self.resize(800, 720)
        self.setMinimumSize(560, 520)
        self._build_ui()
        self._build_menu()
        self.setStyleSheet(STYLE)
        self._show_reply(self.bot.greeting())

    # ---- UI construction --------------------------------------------------
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QWidget()
        hl = QVBoxLayout(header)
        hl.setContentsMargins(18, 12, 18, 10)
        hl.setSpacing(0)
        title = QLabel("Legal Consultancy Assistant")
        title.setObjectName("title")
        subtitle = QLabel("Offline legal information chatbot")
        subtitle.setObjectName("subtitle")
        hl.addWidget(title)
        hl.addWidget(subtitle)
        outer.addWidget(header)

        banner = QLabel("General legal information only, not legal advice. "
                        "No lawyer-client relationship is created by using this app.")
        banner.setObjectName("banner")
        banner.setWordWrap(True)
        outer.addWidget(banner)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        container.setObjectName("chatContainer")
        self.chat_layout = QVBoxLayout(container)
        self.chat_layout.setContentsMargins(8, 8, 8, 8)
        self.chat_layout.addStretch()
        self.scroll.setWidget(container)
        bar = self.scroll.verticalScrollBar()
        bar.rangeChanged.connect(lambda _lo, hi: bar.setValue(hi))   # stick to the bottom
        outer.addWidget(self.scroll, 1)

        self.chip_box = QWidget()
        self.chip_grid = QGridLayout(self.chip_box)
        self.chip_grid.setContentsMargins(14, 4, 14, 4)
        self.chip_grid.setColumnStretch(0, 1)
        self.chip_grid.setColumnStretch(1, 1)
        outer.addWidget(self.chip_box)

        bottom = QWidget()
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(14, 6, 14, 14)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Describe your legal question...")
        self.input.returnPressed.connect(self.send)
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("send")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self.send)
        bl.addWidget(self.input, 1)
        bl.addWidget(self.send_btn)
        outer.addWidget(bottom)

        self.setCentralWidget(root)
        self.input.setFocus()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        for label, shortcut, slot in (
            ("&New conversation", QKeySequence.StandardKey.New, self.new_conversation),
            ("&Export transcript...", QKeySequence.StandardKey.Save, self.export_transcript),
            ("&Quit", QKeySequence.StandardKey.Quit, self.close),
        ):
            action = QAction(label, self)
            action.setShortcut(shortcut)
            action.triggered.connect(slot)
            file_menu.addAction(action)

        help_menu = self.menuBar().addMenu("&Help")
        topics = QAction("Browse &topics", self)
        topics.triggered.connect(lambda: self.send("topics"))
        about = QAction("&About", self)
        about.triggered.connect(self._about)
        help_menu.addAction(topics)
        help_menu.addAction(about)

    # ---- messaging --------------------------------------------------------
    def send(self, text: str | None = None) -> None:
        if not isinstance(text, str):          # called from a signal that passes a bool
            text = self.input.text()
        text = text.strip()
        if not text or self.busy:
            return
        self.input.clear()
        self._set_chips([])
        self._add_message(text, "user")

        self._set_busy(True)
        self.typing = self._make_bubble("Typing...", "bot")
        reply = self.bot.respond(text)
        delay = min(900, 350 + 3 * len(reply.text) // 4)    # feels natural, never slow
        QTimer.singleShot(delay, lambda: self._deliver(reply))

    def _deliver(self, reply: Reply) -> None:
        if self.typing is not None:
            self._remove_bubble(self.typing)
            self.typing = None
        self._show_reply(reply)
        self._set_busy(False)

    def _show_reply(self, reply: Reply) -> None:
        if reply.notice:
            self._add_message(reply.notice, "urgent")
        self._add_message(reply.text, "bot")
        self._set_chips(reply.suggestions)

    def _add_message(self, text: str, kind: str) -> None:
        self._make_bubble(text, kind)
        speaker = "You" if kind == "user" else "Assistant"
        self.history.append((datetime.now().strftime("%H:%M"), speaker, text))

    def _make_bubble(self, text: str, kind: str) -> Bubble:
        bubble = Bubble(text, kind)
        bubble.set_max_width(self._max_bubble_width())
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self.bubbles.append(bubble)
        return bubble

    def _remove_bubble(self, bubble: Bubble) -> None:
        self.chat_layout.removeWidget(bubble)
        self.bubbles.remove(bubble)
        bubble.deleteLater()

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.input.setEnabled(not busy)
        self.send_btn.setEnabled(not busy)
        if not busy:
            self.input.setFocus()

    def _set_chips(self, suggestions: list[str]) -> None:
        while self.chip_grid.count():
            item = self.chip_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, label in enumerate(suggestions[:4]):
            chip = QPushButton(label)
            chip.setObjectName("chip")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda _checked=False, t=label: self.send(t))
            self.chip_grid.addWidget(chip, i // 2, i % 2)

    # ---- layout helpers ---------------------------------------------------
    def _max_bubble_width(self) -> int:
        return max(240, int(self.scroll.viewport().width() * 0.78))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        width = self._max_bubble_width()
        for bubble in self.bubbles:
            bubble.set_max_width(width)

    # ---- menu actions -----------------------------------------------------
    def new_conversation(self) -> None:
        if self.busy:
            return
        for bubble in list(self.bubbles):
            self._remove_bubble(bubble)
        self.history.clear()
        self.bot.reset()
        self._show_reply(self.bot.greeting())

    def export_transcript(self) -> None:
        default = f"legal_chat_{datetime.now():%Y%m%d_%H%M}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "Export transcript", default, "Text files (*.txt)")
        if not path:
            return
        plain = lambda t: re.sub(r"[*_]{1,2}", "", t)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("Legal Consultancy Assistant - transcript\n")
                fh.write("General information only, not legal advice.\n" + "=" * 60 + "\n\n")
                for stamp, speaker, text in self.history:
                    fh.write(f"[{stamp}] {speaker}:\n{plain(text)}\n\n")
        except OSError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))

    def _about(self) -> None:
        QMessageBox.about(
            self, "About",
            "<b>Legal Consultancy Assistant</b><br>An offline, retrieval-based chatbot "
            "built with Python and PyQt6.<br><br>It provides general legal information "
            "only. It is not a substitute for advice from a licensed lawyer.",
        )


def main() -> int:
    """Start the desktop application."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
