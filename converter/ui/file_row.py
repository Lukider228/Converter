"""Строка файла в списке конвертации."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
)

from ..formats import CATEGORY_AUDIO, CATEGORY_IMAGE, CATEGORY_VIDEO
from ..jobs import (
    STATE_CANCELLED, STATE_DONE, STATE_ERROR, STATE_INCOMPATIBLE,
    STATE_QUEUED, STATE_RUNNING,
)
from ..probe import MediaInfo, human_duration, human_size
from . import theme

_CATEGORY_ICON = {
    CATEGORY_AUDIO: "\U0001f3b5",   # 🎵
    CATEGORY_VIDEO: "\U0001f3ac",   # 🎬
    CATEGORY_IMAGE: "\U0001f5bc",   # 🖼
}

_STATE_TEXT = {
    STATE_QUEUED: ("В очереди", theme.TEXT_DIM),
    STATE_RUNNING: ("Конвертация…", theme.ACCENT),
    STATE_DONE: ("Готово", theme.OK),
    STATE_ERROR: ("Ошибка", theme.ERR),
    STATE_CANCELLED: ("Отменено", theme.WARN),
    STATE_INCOMPATIBLE: ("Несовместимо", theme.WARN),
}


class FileRow(QFrame):
    """Карточка файла: имя, метаданные, статус, прогресс, кнопка удаления."""

    remove_requested = Signal(object)  # self

    def __init__(self, path: Path, category: str, info: MediaInfo) -> None:
        super().__init__()
        self.setObjectName("fileRow")
        self.path = path
        self.category = category
        self.info = info
        self.state = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 10, 10)
        layout.setSpacing(12)

        icon = QLabel(_CATEGORY_ICON.get(category, "\U0001f4c4"))
        icon.setStyleSheet("font-size: 22px;")
        layout.addWidget(icon)

        center = QVBoxLayout()
        center.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.name_label = QLabel(path.name)
        self.name_label.setStyleSheet("font-weight: 600;")
        self.name_label.setToolTip(str(path))
        top.addWidget(self.name_label, 1)

        self.status_label = QLabel()
        top.addWidget(self.status_label)
        center.addLayout(top)

        meta_parts = [human_size(info.size_bytes)]
        duration = human_duration(info.duration)
        if duration:
            meta_parts.append(duration)
        self.meta_label = QLabel("  ·  ".join(meta_parts))
        self.meta_label.setObjectName("dim")
        center.addWidget(self.meta_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setFixedHeight(6)
        self.progress.setVisible(False)
        center.addWidget(self.progress)

        layout.addLayout(center, 1)

        self.remove_btn = QPushButton("✕")  # ✕
        self.remove_btn.setObjectName("rowRemove")
        self.remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_btn.setToolTip("Убрать из списка")
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(self.remove_btn)

        self.set_state(STATE_QUEUED)

    def set_state(self, state: str, detail: str = "") -> None:
        self.state = state
        text, color = _STATE_TEXT[state]
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 12px;")
        self.status_label.setToolTip(detail)
        if detail and state in (STATE_ERROR, STATE_INCOMPATIBLE):
            self.meta_label.setText(detail)
            self.meta_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        self.progress.setVisible(state == STATE_RUNNING)
        if state == STATE_RUNNING:
            if self.info.duration <= 0 or self.category == CATEGORY_IMAGE:
                self.progress.setRange(0, 0)  # «бегущая» полоса
            else:
                self.progress.setRange(0, 1000)
                self.progress.setValue(0)
        # Во время работы удалять строку можно — это отменит её задачу.
        self.remove_btn.setToolTip(
            "Отменить и убрать" if state == STATE_RUNNING else "Убрать из списка"
        )

    def set_progress(self, fraction: float) -> None:
        if self.progress.maximum() > 0:
            self.progress.setValue(int(fraction * 1000))

    def reset_for_restart(self) -> None:
        meta_parts = [human_size(self.info.size_bytes)]
        duration = human_duration(self.info.duration)
        if duration:
            meta_parts.append(duration)
        self.meta_label.setText("  ·  ".join(meta_parts))
        self.meta_label.setStyleSheet("")
        self.meta_label.setObjectName("dim")
        self.set_state(STATE_QUEUED)
