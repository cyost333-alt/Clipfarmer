"""Reformats a downloaded clip to vertical (9:16) and burns in
auto-generated captions."""

import json
import subprocess
from pathlib import Path

from faster_whisper import WhisperModel

_model = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel("base", compute_type="int8")
    return _model


def transcribe(video_path: str) -> list[dict]:
    """Returns a list of {start, end, text} caption segments."""
    model = _get_model()
    segments, _ = model.transcribe(video_path, word_timestamps=False)
    return [
        {"start": seg.start, "end": seg.end, "text": seg.text.strip()}
        for seg in segments
    ]


def _srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments: list[dict], srt_path: str) -> None:
    lines = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{_srt_timestamp(seg['start'])} --> {_srt_timestamp(seg['end'])}")
        lines.append(seg["text"])
        lines.append("")
    Path(srt_path).write_text("\n".join(lines), encoding="utf-8")


def to_vertical_with_captions(input_path: str, output_path: str, srt_path: str) -> None:
    """Crops/pads to 1080x1920 and burns in the given .srt as captions."""
    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        f"subtitles={srt_path}:force_style='FontSize=20,Outline=2,Bold=1'"
        "[v]"
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", input_path,
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "0:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac",
            output_path,
        ],
        check=True,
    )


def process(input_path: str, output_path: str) -> None:
    srt_path = str(Path(output_path).with_suffix(".srt"))
    segments = transcribe(input_path)
    write_srt(segments, srt_path)
    to_vertical_with_captions(input_path, output_path, srt_path)
