"""Очередь задач конвертации поверх QProcess."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

from .formats import ConversionPlan

STATE_QUEUED = "queued"
STATE_RUNNING = "running"
STATE_DONE = "done"
STATE_ERROR = "error"
STATE_CANCELLED = "cancelled"
STATE_INCOMPATIBLE = "incompatible"


class ConversionJob(QObject):
    """Одна конвертация: запускает ffmpeg и парсит прогресс."""

    started = Signal()
    progress = Signal(float)  # 0..1
    finished = Signal(bool, str)  # успех, текст ошибки

    def __init__(self, plan: ConversionPlan, duration: float, dst: Path,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._plan = plan
        self._duration = duration
        self._dst = dst
        self._process: QProcess | None = None
        self._stderr_tail: list[str] = []
        self._cancelled = False

    @property
    def destination(self) -> Path:
        return self._dst

    def start(self) -> None:
        process = QProcess(self)
        self._process = process
        args = list(self._plan.args)
        if self._plan.has_progress and self._duration > 0:
            args = ["-progress", "pipe:1", "-nostats"] + args
        process.readyReadStandardOutput.connect(self._read_progress)
        process.readyReadStandardError.connect(self._read_stderr)
        process.finished.connect(self._on_finished)
        process.errorOccurred.connect(self._on_process_error)
        self.started.emit()
        process.start("ffmpeg", args)

    def cancel(self) -> None:
        self._cancelled = True
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
        else:
            self.finished.emit(False, "Отменено")

    def _read_progress(self) -> None:
        if not self._process:
            return
        text = bytes(self._process.readAllStandardOutput()).decode("utf-8", "replace")
        for line in text.splitlines():
            if line.startswith("out_time_us=") and self._duration > 0:
                try:
                    seconds = int(line.split("=", 1)[1]) / 1_000_000
                except ValueError:
                    continue
                self.progress.emit(min(seconds / self._duration, 0.995))

    def _read_stderr(self) -> None:
        if not self._process:
            return
        text = bytes(self._process.readAllStandardError()).decode("utf-8", "replace")
        for line in text.splitlines():
            line = line.strip()
            if line:
                self._stderr_tail.append(line)
        self._stderr_tail = self._stderr_tail[-8:]

    def _on_process_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self.finished.emit(False, "Не удалось запустить ffmpeg")

    def _on_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        if self._cancelled:
            self._cleanup_partial()
            self.finished.emit(False, "Отменено")
            return
        if exit_code == 0:
            self.progress.emit(1.0)
            self.finished.emit(True, "")
        else:
            self._cleanup_partial()
            detail = self._stderr_tail[-1] if self._stderr_tail else f"код {exit_code}"
            self.finished.emit(False, detail)

    def _cleanup_partial(self) -> None:
        try:
            if self._dst.exists():
                self._dst.unlink()
        except OSError:
            pass


class JobQueue(QObject):
    """Запускает задачи пачками по max_parallel штук."""

    all_finished = Signal()

    def __init__(self, max_parallel: int = 2, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.max_parallel = max_parallel
        self._pending: list[ConversionJob] = []
        self._running: set[ConversionJob] = set()

    @property
    def active(self) -> bool:
        return bool(self._pending or self._running)

    def add(self, job: ConversionJob) -> None:
        self._pending.append(job)
        job.finished.connect(lambda *_: self._on_job_finished(job))
        self._pump()

    def cancel_all(self) -> None:
        pending = self._pending[:]
        self._pending.clear()
        for job in pending:
            job.finished.emit(False, "Отменено")
        for job in list(self._running):
            job.cancel()

    def cancel_job(self, job: ConversionJob) -> None:
        if job in self._pending:
            self._pending.remove(job)
            job.finished.emit(False, "Отменено")
        elif job in self._running:
            job.cancel()

    def _on_job_finished(self, job: ConversionJob) -> None:
        self._running.discard(job)
        self._pump()
        if not self.active:
            self.all_finished.emit()

    def _pump(self) -> None:
        while self._pending and len(self._running) < self.max_parallel:
            job = self._pending.pop(0)
            self._running.add(job)
            job.start()
