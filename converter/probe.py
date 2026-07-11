"""Информация о медиафайле через ffprobe."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MediaInfo:
    duration: float  # секунды, 0 если неизвестно
    has_audio: bool
    has_video: bool
    size_bytes: int
    audio_codec: str = ""  # кодек первой аудиодорожки (mp3, aac, opus…)
    video_codec: str = ""  # кодек первой видеодорожки (h264, vp9…)


def probe(path: Path) -> MediaInfo:
    """Читает длительность и состав потоков. Не бросает исключений."""
    duration = 0.0
    has_audio = False
    has_video = False
    audio_codec = ""
    video_codec = ""
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-print_format", "json",
                "-show_format", "-show_streams", str(path),
            ],
            capture_output=True, text=True, timeout=15,
        )
        data = json.loads(out.stdout or "{}")
        fmt = data.get("format", {})
        try:
            duration = float(fmt.get("duration", 0) or 0)
        except (TypeError, ValueError):
            duration = 0.0
        for stream in data.get("streams", []):
            codec_type = stream.get("codec_type")
            if codec_type == "audio":
                if not has_audio:
                    audio_codec = stream.get("codec_name", "") or ""
                has_audio = True
            elif codec_type == "video":
                if not has_video:
                    video_codec = stream.get("codec_name", "") or ""
                has_video = True
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        pass

    try:
        size = path.stat().st_size
    except OSError:
        size = 0

    return MediaInfo(duration=duration, has_audio=has_audio,
                     has_video=has_video, size_bytes=size,
                     audio_codec=audio_codec, video_codec=video_codec)


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("Б", "КБ", "МБ", "ГБ", "ТБ"):
        if value < 1024 or unit == "ТБ":
            if unit == "Б":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} ТБ"


def human_duration(seconds: float) -> str:
    if seconds <= 0:
        return ""
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
