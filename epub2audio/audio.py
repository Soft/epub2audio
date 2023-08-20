import subprocess
import wave
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Final

FFMPEG_BINARY: Final[str] = "ffmpeg"

PathType = Path | str | BinaryIO


def wave_file_get_params(input_path: PathType) -> wave._wave_params:
    input_path = _normalize_path(input_path)
    with wave.open(input_path, "rb") as clip:
        return clip.getparams()


def concatenate_wave_files(
    output_path: PathType,
    first: Path,
    *others: Path | bytes,
) -> None:
    output_path = _normalize_path(output_path)
    with wave.open(output_path, "wb") as output:
        with wave.open(str(first), "rb") as clip:
            output.setparams(clip.getparams())
            output.writeframes(clip.readframes(clip.getnframes()))
        for segment in others:
            if isinstance(segment, Path):
                with wave.open(str(segment), "rb") as clip:
                    output.writeframes(clip.readframes(clip.getnframes()))
            elif isinstance(segment, bytes):
                with BytesIO(segment) as segment_input, wave.open(
                    segment_input, "rb"
                ) as clip:
                    output.writeframes(clip.readframes(clip.getnframes()))


def generate_silent_wave_file(
    output_path: PathType,
    *,
    duration_secs: float,
    framerate: int,
    sample_width: int = 2,
) -> None:
    output_path = _normalize_path(output_path)
    frame_count = int(duration_secs * framerate)
    with wave.open(output_path, "wb") as output:
        output.setnchannels(1)
        output.setframerate(framerate)
        output.setnframes(frame_count)
        output.setsampwidth(sample_width)
        output.writeframes(bytes(frame_count * sample_width))


def _normalize_path(path: PathType) -> str | BinaryIO:
    if isinstance(path, Path):
        return str(path)
    return path


def encode_audio_file(
    input_path: Path,
    output_path: Path,
    bitrate: str = "192k",
) -> None:
    subprocess.check_call(
        [
            FFMPEG_BINARY,
            "-i",
            str(input_path),
            "-ab",
            bitrate,
            str(output_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
