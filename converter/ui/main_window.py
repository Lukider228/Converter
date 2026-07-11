"""Главное окно конвертера."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from .. import formats
from ..jobs import (
    STATE_CANCELLED, STATE_DONE, STATE_ERROR, STATE_INCOMPATIBLE,
    STATE_QUEUED, STATE_RUNNING, ConversionJob, JobQueue,
)
from ..probe import probe
from . import theme
from .file_row import FileRow

QUALITY_OPTIONS = [
    (
        "Без потерь", formats.QUALITY_LOSSLESS,
        "Где возможно — дорожка копируется без перекодирования:\n"
        "мгновенно и байт-в-байт (например, mp4 → mkv или opus из webm).\n"
        "Если копировать нельзя — максимальные настройки кодека:\n"
        "аудио 320 кбит/с, видео CRF 16.",
    ),
    (
        "Высокое", formats.QUALITY_HIGH,
        "Аудио 320 кбит/с, видео CRF 18 (16 для VP9-эквивалента).\n"
        "На слух и на глаз неотличимо от оригинала, файлы крупнее.",
    ),
    (
        "Среднее", formats.QUALITY_MEDIUM,
        "Аудио 192 кбит/с, видео CRF 23.\n"
        "Золотая середина: хорошее качество при умеренном размере.",
    ),
    (
        "Низкое", formats.QUALITY_LOW,
        "Аудио 128 кбит/с, видео CRF 28, GIF мельче и реже кадры.\n"
        "Минимальный размер файла, потери качества заметны.",
    ),
]



class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Converter")
        self.resize(860, 640)
        self.setAcceptDrops(True)

        self.rows: list[FileRow] = []
        self.jobs: dict[FileRow, ConversionJob] = {}
        self.queue = JobQueue(max_parallel=2, parent=self)
        self.queue.all_finished.connect(self._on_all_finished)
        self.output_dir: Path | None = None  # None — рядом с исходником
        self.settings = QSettings("Converter", "Converter")

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 12)
        root.setSpacing(12)

        root.addLayout(self._build_header())
        root.addWidget(self._build_controls())
        root.addWidget(self._build_file_area(), 1)
        root.addLayout(self._build_actions())

        self.status_label = QLabel("Добавьте файлы для конвертации")
        self.statusBar().addWidget(self.status_label)
        self._restore_settings()
        self._connect_persistence()
        self._refresh_ui()

    # ---------- построение интерфейса ----------

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        title = QLabel("⚡ Converter")
        title.setObjectName("appTitle")
        header.addWidget(title)
        subtitle = QLabel("аудио · видео · изображения")
        subtitle.setObjectName("dim")
        header.addWidget(subtitle)
        header.addStretch(1)
        return header

    def _build_controls(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("controlsBar")
        controls = QHBoxLayout(bar)
        controls.setContentsMargins(14, 10, 14, 10)
        controls.setSpacing(10)

        controls.addWidget(QLabel("Конвертировать в:"))
        self.format_combo = QComboBox()
        self.format_combo.setFixedWidth(110)
        model = QStandardItemModel()
        for group_name, targets in formats.TARGET_GROUPS:
            group_item = QStandardItem(f"— {group_name} —")
            group_item.setFlags(Qt.ItemFlag.NoItemFlags)
            model.appendRow(group_item)
            for target in targets:
                model.appendRow(QStandardItem(target.upper()))
        self.format_combo.setModel(model)
        self.format_combo.setCurrentIndex(1)  # mp3
        self.format_combo.view().setMinimumWidth(170)  # чтобы заголовки групп не резались
        controls.addWidget(self.format_combo)

        controls.addWidget(QLabel("Качество:"))
        self.quality_combo = QComboBox()
        self.quality_combo.setFixedWidth(130)
        for i, (label, _value, tooltip) in enumerate(QUALITY_OPTIONS):
            self.quality_combo.addItem(label)
            self.quality_combo.setItemData(i, tooltip, Qt.ItemDataRole.ToolTipRole)
        self.quality_combo.setCurrentIndex(0)  # Без потерь по умолчанию
        self.quality_combo.currentIndexChanged.connect(self._update_quality_tooltip)
        self._update_quality_tooltip(0)
        controls.addWidget(self.quality_combo)

        controls.addWidget(QLabel("Потоков:"))
        self.parallel_spin = QSpinBox()
        self.parallel_spin.setFixedWidth(72)
        self.parallel_spin.setRange(1, 8)
        self.parallel_spin.setValue(2)
        self.parallel_spin.setToolTip("Сколько файлов конвертировать одновременно")
        controls.addWidget(self.parallel_spin)

        controls.addStretch(1)

        controls.addWidget(QLabel("Сохранять в:"))
        self.output_btn = QPushButton()
        self.output_btn.setObjectName("outputField")
        self.output_btn.setFixedWidth(230)
        self.output_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.output_btn.clicked.connect(self._choose_output_dir)
        controls.addWidget(self.output_btn)

        self.output_reset_btn = QPushButton("✕")
        self.output_reset_btn.setObjectName("rowRemove")
        self.output_reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.output_reset_btn.setToolTip("Снова сохранять рядом с исходником")
        self.output_reset_btn.clicked.connect(lambda: self._set_output_dir(None))
        # Скрытый крестик продолжает занимать место — панель не дёргается.
        policy = self.output_reset_btn.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self.output_reset_btn.setSizePolicy(policy)
        controls.addWidget(self.output_reset_btn)

        self._set_output_dir(None, save=False)
        return bar

    def _build_file_area(self) -> QWidget:
        self.drop_zone = QFrame()
        self.drop_zone.setObjectName("dropZone")
        zone_layout = QVBoxLayout(self.drop_zone)
        zone_layout.setContentsMargins(8, 8, 8, 8)

        self.hint_label = QLabel(
            "\U0001f4e5\n\nПеретащите файлы сюда\nили нажмите «Добавить файлы»"
        )
        self.hint_label.setObjectName("hint")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_layout.addWidget(self.hint_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        list_host = QWidget()
        self.list_layout = QVBoxLayout(list_host)
        self.list_layout.setContentsMargins(2, 2, 6, 2)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch(1)
        scroll.setWidget(list_host)
        zone_layout.addWidget(scroll)
        self.scroll = scroll
        scroll.setVisible(False)
        return self.drop_zone

    def _build_actions(self) -> QHBoxLayout:
        actions = QHBoxLayout()
        actions.setSpacing(10)

        self.add_btn = QPushButton("+ Добавить файлы")
        self.add_btn.clicked.connect(self._add_files_dialog)
        actions.addWidget(self.add_btn)

        self.clear_btn = QPushButton("Очистить список")
        self.clear_btn.setObjectName("danger")
        self.clear_btn.clicked.connect(self._clear_list)
        actions.addWidget(self.clear_btn)

        actions.addStretch(1)

        self.cancel_btn = QPushButton("Отменить")
        self.cancel_btn.setObjectName("danger")
        self.cancel_btn.clicked.connect(self._cancel_all)
        self.cancel_btn.setVisible(False)
        actions.addWidget(self.cancel_btn)

        self.start_btn = QPushButton("▶ Конвертировать")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._start_conversion)
        actions.addWidget(self.start_btn)
        return actions

    # ---------- drag & drop ----------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_zone.setProperty("dragActive", True)
            self._repolish_drop_zone()

    def dragLeaveEvent(self, event) -> None:
        self.drop_zone.setProperty("dragActive", False)
        self._repolish_drop_zone()

    def dropEvent(self, event: QDropEvent) -> None:
        self.drop_zone.setProperty("dragActive", False)
        self._repolish_drop_zone()
        paths: list[Path] = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.is_dir():
                    paths.extend(p for p in sorted(path.iterdir()) if p.is_file())
                elif path.is_file():
                    paths.append(path)
        self._add_files(paths)

    def _repolish_drop_zone(self) -> None:
        self.drop_zone.style().unpolish(self.drop_zone)
        self.drop_zone.style().polish(self.drop_zone)

    # ---------- работа со списком ----------

    def _add_files_dialog(self) -> None:
        patterns = " ".join(
            f"*.{ext}"
            for ext in sorted(formats.AUDIO_EXTS | formats.VIDEO_EXTS | formats.IMAGE_EXTS)
        )
        files, _selected_filter = QFileDialog.getOpenFileNames(
            self, "Выберите файлы", str(Path.home()),
            f"Медиафайлы ({patterns});;Все файлы (*)",
        )
        self._add_files([Path(f) for f in files])

    def _add_files(self, paths: list[Path]) -> None:
        existing = {row.path for row in self.rows}
        added = 0
        skipped = 0
        for path in paths:
            if path in existing:
                continue
            category = formats.category_of(path)
            if category is None:
                skipped += 1
                continue
            info = probe(path)
            row = FileRow(path, category, info)
            row.remove_requested.connect(self._remove_row)
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)
            self.rows.append(row)
            existing.add(path)
            added += 1
        if skipped:
            self.status_label.setText(
                f"Добавлено: {added}, пропущено неподдерживаемых: {skipped}"
            )
        elif added:
            self.status_label.setText(f"Добавлено файлов: {added}")
        self._refresh_ui()

    def _remove_row(self, row: FileRow) -> None:
        job = self.jobs.pop(row, None)
        if job is not None and row.state in (STATE_QUEUED, STATE_RUNNING):
            self.queue.cancel_job(job)
        if row in self.rows:
            self.rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        self._refresh_ui()

    def _clear_list(self) -> None:
        self._cancel_all()
        for row in self.rows[:]:
            self._remove_row(row)
        self.status_label.setText("Список очищен")

    # ---------- конвертация ----------

    def _current_target(self) -> str:
        return self.format_combo.currentText().lower()

    def _current_quality(self) -> str:
        return QUALITY_OPTIONS[self.quality_combo.currentIndex()][1]

    def _update_quality_tooltip(self, index: int) -> None:
        self.quality_combo.setToolTip(QUALITY_OPTIONS[index][2])

    # ---------- папка назначения ----------

    def _display_dir(self, path: str) -> str:
        home = str(Path.home())
        display = path
        if display == home:
            display = "~"
        elif display.startswith(home + "/"):
            display = "~" + display[len(home):]
        # Обрезаем по реальной ширине поля, конец пути важнее начала.
        metrics = self.output_btn.fontMetrics()
        available = self.output_btn.width() - 46  # padding + значок папки
        return metrics.elidedText(display, Qt.TextElideMode.ElideLeft, available)

    def _choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Папка для результатов",
            str(self.output_dir or Path.home()),
        )
        if directory:  # отмена диалога не сбрасывает текущий выбор
            self._set_output_dir(Path(directory).resolve())

    def _set_output_dir(self, path: Path | None, save: bool = True) -> None:
        self.output_dir = path
        if path is None:
            self.output_btn.setText("\U0001f4c1 Рядом с исходником")
            self.output_btn.setToolTip(
                "Результат сохраняется в папку исходного файла.\n"
                "Нажмите, чтобы выбрать другую папку."
            )
        else:
            self.output_btn.setText("\U0001f4c2 " + self._display_dir(str(path)))
            self.output_btn.setToolTip(str(path))
        self.output_reset_btn.setVisible(path is not None)
        if save:
            self._save_settings()

    # ---------- настройки ----------

    def _restore_settings(self) -> None:
        s = self.settings
        geometry = s.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

        s.remove("recent_dirs")  # осталось от старой версии с историей папок

        target = str(s.value("target", "") or "")
        if target:
            index = self.format_combo.findText(target.upper())
            if index >= 0:
                self.format_combo.setCurrentIndex(index)

        quality = str(s.value("quality", "") or "")
        for i, (_label, value, _tooltip) in enumerate(QUALITY_OPTIONS):
            if value == quality:
                self.quality_combo.setCurrentIndex(i)
                break

        try:
            self.parallel_spin.setValue(int(s.value("parallel", 2)))
        except (TypeError, ValueError):
            pass

        output = str(s.value("output_dir", "") or "")
        if output and Path(output).is_dir():
            self._set_output_dir(Path(output), save=False)

    def _save_settings(self) -> None:
        s = self.settings
        s.setValue("target", self._current_target())
        s.setValue("quality", self._current_quality())
        s.setValue("parallel", self.parallel_spin.value())
        s.setValue("output_dir", str(self.output_dir) if self.output_dir else "")

    def _connect_persistence(self) -> None:
        self.format_combo.currentIndexChanged.connect(lambda *_: self._save_settings())
        self.quality_combo.currentIndexChanged.connect(lambda *_: self._save_settings())
        self.parallel_spin.valueChanged.connect(lambda *_: self._save_settings())

    def _start_conversion(self) -> None:
        target = self._current_target()
        quality = self._current_quality()
        self.queue.max_parallel = self.parallel_spin.value()

        started = 0
        for row in self.rows:
            if row.state == STATE_RUNNING:
                continue
            row.reset_for_restart()
            error = formats.is_compatible(
                row.category, row.info.has_audio, row.info.has_video, target,
            )
            if row.path.suffix.lstrip(".").lower() == target:
                error = error or "Файл уже в этом формате"
            if error:
                row.set_state(STATE_INCOMPATIBLE, error)
                continue

            out_dir = self.output_dir or row.path.parent
            dst = formats.unique_destination(out_dir, row.path.stem, target)
            plan = formats.build_plan(
                row.path, dst, target, quality, row.category, row.info,
            )
            job = ConversionJob(plan, row.info.duration, dst, parent=self)
            self.jobs[row] = job
            job.started.connect(lambda r=row: self._on_job_started(r))
            job.progress.connect(lambda f, r=row: self._on_job_progress(r, f))
            job.finished.connect(
                lambda ok, err, r=row: self._on_job_finished(r, ok, err)
            )
            self.queue.add(job)
            started += 1

        if started:
            self.status_label.setText(f"Конвертация {started} файл(ов)…")
        else:
            self.status_label.setText("Нет файлов для конвертации")
        self._refresh_ui()

    def _on_job_started(self, row: FileRow) -> None:
        if row in self.rows:
            row.set_state(STATE_RUNNING)

    def _on_job_progress(self, row: FileRow, fraction: float) -> None:
        if row in self.rows:
            row.set_progress(fraction)

    def _on_job_finished(self, row: FileRow, ok: bool, error: str) -> None:
        self.jobs.pop(row, None)
        if row in self.rows:
            if ok:
                row.set_state(STATE_DONE)
            elif error == "Отменено":
                row.set_state(STATE_CANCELLED)
            else:
                row.set_state(STATE_ERROR, error)
        self._update_status_counts()
        self._refresh_ui()

    def _on_all_finished(self) -> None:
        self._update_status_counts(final=True)
        self._refresh_ui()

    def _cancel_all(self) -> None:
        if self.queue.active:
            self.queue.cancel_all()
            self.status_label.setText("Конвертация отменена")

    def _update_status_counts(self, final: bool = False) -> None:
        done = sum(1 for r in self.rows if r.state == STATE_DONE)
        errors = sum(1 for r in self.rows if r.state == STATE_ERROR)
        skipped = sum(
            1 for r in self.rows
            if r.state in (STATE_INCOMPATIBLE, STATE_CANCELLED)
        )
        parts = [f"Готово: {done}"]
        if errors:
            parts.append(f"ошибок: {errors}")
        if skipped:
            parts.append(f"пропущено: {skipped}")
        prefix = "✅ Завершено. " if final else ""
        self.status_label.setText(prefix + ", ".join(parts))

    # ---------- состояние интерфейса ----------

    def _refresh_ui(self) -> None:
        has_files = bool(self.rows)
        busy = self.queue.active
        self.hint_label.setVisible(not has_files)
        self.scroll.setVisible(has_files)
        self.start_btn.setEnabled(has_files and not busy)
        self.cancel_btn.setVisible(busy)
        self.clear_btn.setEnabled(has_files)
        self.format_combo.setEnabled(not busy)
        self.quality_combo.setEnabled(not busy)
        self.parallel_spin.setEnabled(not busy)
        self.output_btn.setEnabled(not busy)
        self.output_reset_btn.setEnabled(not busy)

    def closeEvent(self, event) -> None:
        self.settings.setValue("geometry", self.saveGeometry())
        self._save_settings()
        self.queue.cancel_all()
        super().closeEvent(event)
