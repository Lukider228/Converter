"""Определения форматов и построение аргументов ffmpeg."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .probe import MediaInfo

AUDIO_EXTS = {
    "mp3", "wav", "flac", "ogg", "oga", "opus", "m4a", "aac", "wma",
    "alac", "aiff", "aif", "amr", "ac3", "mka",
}
VIDEO_EXTS = {
    "mp4", "mkv", "webm", "avi", "mov", "wmv", "flv", "m4v", "mpg",
    "mpeg", "ts", "m2ts", "3gp", "ogv", "vob",
}
IMAGE_EXTS = {
    "png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif", "gif", "avif",
    "heic", "ico",
}

CATEGORY_AUDIO = "audio"
CATEGORY_VIDEO = "video"
CATEGORY_IMAGE = "image"

# Целевые форматы, сгруппированные для выпадающего списка.
TARGET_GROUPS: list[tuple[str, list[str]]] = [
    ("Аудио", ["mp3", "wav", "flac", "ogg", "opus", "m4a", "aac"]),
    ("Видео", ["mp4", "mkv", "webm", "mov", "avi", "gif"]),
    ("Изображения", ["png", "jpg", "webp", "bmp", "tiff"]),
]

QUALITY_LOSSLESS = "lossless"
QUALITY_HIGH = "high"
QUALITY_MEDIUM = "medium"
QUALITY_LOW = "low"

_AUDIO_BITRATE = {
    QUALITY_LOSSLESS: "320k", QUALITY_HIGH: "320k",
    QUALITY_MEDIUM: "192k", QUALITY_LOW: "128k",
}
_OPUS_BITRATE = {
    QUALITY_LOSSLESS: "256k", QUALITY_HIGH: "256k",
    QUALITY_MEDIUM: "160k", QUALITY_LOW: "96k",
}
_X264_CRF = {
    QUALITY_LOSSLESS: "16", QUALITY_HIGH: "18",
    QUALITY_MEDIUM: "23", QUALITY_LOW: "28",
}
_VP9_CRF = {
    QUALITY_LOSSLESS: "20", QUALITY_HIGH: "24",
    QUALITY_MEDIUM: "32", QUALITY_LOW: "38",
}
_JPG_Q = {
    QUALITY_LOSSLESS: "1", QUALITY_HIGH: "2",
    QUALITY_MEDIUM: "5", QUALITY_LOW: "10",
}
_WEBP_Q = {
    QUALITY_LOSSLESS: "100", QUALITY_HIGH: "95",
    QUALITY_MEDIUM: "80", QUALITY_LOW: "60",
}
_GIF_FPS = {
    QUALITY_LOSSLESS: "15", QUALITY_HIGH: "15",
    QUALITY_MEDIUM: "12", QUALITY_LOW: "8",
}
_GIF_WIDTH = {
    QUALITY_LOSSLESS: "640", QUALITY_HIGH: "640",
    QUALITY_MEDIUM: "480", QUALITY_LOW: "320",
}

# Какие кодеки можно скопировать (-c copy) в целевой аудиоформат без
# перекодирования. Совпадение кодека = конвертация без потерь и мгновенно.
_AUDIO_COPY_CODECS: dict[str, set[str]] = {
    "mp3": {"mp3"},
    "ogg": {"vorbis"},
    "opus": {"opus"},
    "m4a": {"aac", "alac"},
    "aac": {"aac"},
    "flac": {"flac"},
    "wav": {"pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le", "pcm_u8"},
}

# Какие кодеки допустимы в целевом видеоконтейнере при копировании потока.
# None = контейнер принимает практически всё (mkv).
_CONTAINER_VIDEO_CODECS: dict[str, set[str] | None] = {
    "mkv": None,
    "mp4": {"h264", "hevc", "av1"},
    "mov": {"h264", "hevc", "prores"},
    "webm": {"vp8", "vp9", "av1"},
    "avi": {"mpeg4", "mjpeg"},
}
_CONTAINER_AUDIO_CODECS: dict[str, set[str] | None] = {
    "mkv": None,
    "mp4": {"aac", "mp3", "ac3"},
    "mov": {"aac", "mp3", "pcm_s16le"},
    "webm": {"opus", "vorbis"},
    "avi": {"mp3", "ac3", "pcm_s16le"},
}

# Форматы изображений, которые сами по себе без потерь.
_LOSSLESS_IMAGE_TARGETS = {"png", "bmp", "tiff"}


def category_of(path: Path) -> str | None:
    ext = path.suffix.lstrip(".").lower()
    if ext in AUDIO_EXTS:
        return CATEGORY_AUDIO
    if ext in VIDEO_EXTS:
        return CATEGORY_VIDEO
    if ext in IMAGE_EXTS:
        return CATEGORY_IMAGE
    return None


def target_category(target: str) -> str:
    for group, targets in TARGET_GROUPS:
        if target in targets:
            return {
                "Аудио": CATEGORY_AUDIO,
                "Видео": CATEGORY_VIDEO,
                "Изображения": CATEGORY_IMAGE,
            }[group]
    raise ValueError(f"Неизвестный целевой формат: {target}")


@dataclass
class ConversionPlan:
    """Готовые аргументы ffmpeg для одной задачи."""

    args: list[str]  # полный список аргументов после "ffmpeg"
    has_progress: bool  # можно ли считать прогресс по времени


def is_compatible(src_category: str, has_audio: bool, has_video: bool, target: str) -> str | None:
    """Возвращает текст ошибки, если конвертация невозможна, иначе None."""
    tcat = target_category(target)
    if tcat == CATEGORY_AUDIO:
        if src_category == CATEGORY_IMAGE:
            return "Из изображения нельзя получить аудио"
        if not has_audio:
            return "В файле нет звуковой дорожки"
    elif tcat == CATEGORY_VIDEO:
        if src_category == CATEGORY_IMAGE and target == "gif":
            return None  # картинку в gif можно
        if src_category == CATEGORY_IMAGE:
            return "Из одиночного изображения нельзя получить видео"
    elif tcat == CATEGORY_IMAGE:
        if src_category == CATEGORY_AUDIO or not has_video:
            return "В файле нет изображения или видеоряда"
    return None


def _can_copy_audio_into(target: str, codec: str) -> bool:
    allowed = _CONTAINER_AUDIO_CODECS.get(target)
    return bool(codec) and (allowed is None or codec in allowed)


def _can_copy_video_into(target: str, codec: str) -> bool:
    allowed = _CONTAINER_VIDEO_CODECS.get(target)
    return bool(codec) and (allowed is None or codec in allowed)


def build_plan(
    src: Path,
    dst: Path,
    target: str,
    quality: str,
    src_category: str,
    info: MediaInfo,
) -> ConversionPlan:
    """Строит аргументы ffmpeg для конвертации src -> dst."""
    tcat = target_category(target)
    lossless = quality == QUALITY_LOSSLESS
    has_audio, has_video = info.has_audio, info.has_video
    pre: list[str] = ["-hide_banner", "-nostdin", "-y"]
    post: list[str] = []
    has_progress = True

    if tcat == CATEGORY_AUDIO:
        post += ["-vn", "-map_metadata", "0"]
        if lossless and info.audio_codec in _AUDIO_COPY_CODECS.get(target, set()):
            # Кодек уже совпадает с целевым — копируем дорожку как есть.
            post += ["-c:a", "copy"]
            if target == "mp3":
                post += ["-id3v2_version", "3"]
        elif target == "mp3":
            post += ["-c:a", "libmp3lame", "-b:a", _AUDIO_BITRATE[quality], "-id3v2_version", "3"]
        elif target == "wav":
            post += ["-c:a", "pcm_s16le"]
        elif target == "flac":
            post += ["-c:a", "flac"]
        elif target == "ogg":
            post += ["-c:a", "libvorbis", "-b:a", _AUDIO_BITRATE[quality]]
        elif target == "opus":
            post += ["-c:a", "libopus", "-b:a", _OPUS_BITRATE[quality]]
        elif target in ("m4a", "aac"):
            post += ["-c:a", "aac", "-b:a", _AUDIO_BITRATE[quality]]

    elif tcat == CATEGORY_VIDEO:
        if target == "gif":
            # GIF через палитру — иначе цвета ужасны.
            post += [
                "-filter_complex",
                f"[0:v]fps={_GIF_FPS[quality]},"
                f"scale={_GIF_WIDTH[quality]}:-1:flags=lanczos,"
                f"split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                "-an",
            ]
            if src_category == CATEGORY_IMAGE:
                has_progress = False
        elif src_category == CATEGORY_AUDIO or not has_video:
            # Аудио -> видео: рисуем волну звука.
            post += [
                "-filter_complex",
                "[0:a]showwaves=s=1280x720:mode=cline:rate=25:"
                "colors=#5865f2|#4dd0e1,format=yuv420p[v]",
                "-map", "[v]", "-map", "0:a",
            ]
            post += _video_codec_args(target, quality)
            if lossless and _can_copy_audio_into(target, info.audio_codec):
                post += ["-c:a", "copy"]
            else:
                post += _audio_for_video_args(target, quality)
            post += ["-shortest"]
        else:
            post += ["-map", "0:v:0"]
            if lossless and _can_copy_video_into(target, info.video_codec):
                post += ["-c:v", "copy"]
            else:
                post += _video_codec_args(target, quality)
            if has_audio:
                post += ["-map", "0:a:0"]
                if lossless and _can_copy_audio_into(target, info.audio_codec):
                    post += ["-c:a", "copy"]
                else:
                    post += _audio_for_video_args(target, quality)
            post += ["-map_metadata", "0"]
            if target in ("mp4", "mov"):
                post += ["-movflags", "+faststart"]

    else:  # изображение
        has_progress = False
        if src_category == CATEGORY_VIDEO:
            # Кадр с первой секунды видео.
            pre += ["-ss", "1"]
        post += ["-frames:v", "1"]
        if target == "jpg":
            post += ["-q:v", _JPG_Q[quality], "-pix_fmt", "yuvj420p"]
        elif target == "webp":
            if lossless:
                post += ["-lossless", "1"]
            else:
                post += ["-quality", _WEBP_Q[quality]]
        # png/bmp/tiff без потерь по своей природе — параметры не нужны.

    args = pre + ["-i", str(src)] + post + [str(dst)]
    return ConversionPlan(args=args, has_progress=has_progress)


def _video_codec_args(target: str, quality: str) -> list[str]:
    if target == "webm":
        return [
            "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", _VP9_CRF[quality],
            "-row-mt", "1", "-cpu-used", "4",
        ]
    return ["-c:v", "libx264", "-crf", _X264_CRF[quality], "-preset", "fast",
            "-pix_fmt", "yuv420p"]


def _audio_for_video_args(target: str, quality: str) -> list[str]:
    if target == "webm":
        return ["-c:a", "libopus", "-b:a", _OPUS_BITRATE[quality]]
    if target == "avi":
        return ["-c:a", "libmp3lame", "-b:a", _AUDIO_BITRATE[quality]]
    return ["-c:a", "aac", "-b:a", _AUDIO_BITRATE[quality]]


def unique_destination(directory: Path, stem: str, target: str) -> Path:
    """Подбирает свободное имя файла: name.ext, name (1).ext, ..."""
    candidate = directory / f"{stem}.{target}"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem} ({counter}).{target}"
        counter += 1
    return candidate
