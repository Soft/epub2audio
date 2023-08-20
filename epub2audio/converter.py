import itertools
import logging
import re
from io import BytesIO
from pathlib import Path
from re import Pattern
from tempfile import TemporaryDirectory
from typing import IO, Final

from mutagen import id3  # type: ignore

from . import audio, common
from .epub import EPubFile, EPubItem
from .error import ErrorHandler
from .preprocess import ContentPreprocessor
from .synthesizer import Synthesizer


DIR_NAME_REGEX: Final[Pattern[str]] = re.compile(r"[^a-zA-Z0-9'\"\-_ ]")
INTER_CHUNK_SILENCE_SECS: Final[float] = 1.5


def _generate_inter_chunk_silence(duration: float) -> bytes:
    with BytesIO() as output:
        audio.generate_silent_wave_file(
            output,
            duration_secs=duration,
            framerate=24000,  # FIXME: get framerate from generated files
        )
        return output.getvalue()


INTER_CHUNK_SILENCE: Final[bytes] = _generate_inter_chunk_silence(
    INTER_CHUNK_SILENCE_SECS
)


class EPubToAudioConverter:
    def __init__(
        self,
        *,
        synthesizer: Synthesizer,
        error_handler: ErrorHandler,
    ) -> None:
        self.preprocessor = ContentPreprocessor()
        self.synthesizer = synthesizer
        self.error_handler = error_handler

    def convert(self, input_path: Path, output_directory: Path) -> None:
        logging.info(f"Processing {input_path}")
        with EPubFile(input_path) as book:
            book_directory = output_directory / _book_directory_name(
                input_path,
                book,
            )
            book_directory.mkdir()
            chapters = [item for item in book.spine() if _is_chapter(item)]
            chapter_count = len(chapters)
            for chapter_num, chapter in enumerate(chapters, start=1):
                logging.info(f"Processing chapter {chapter_num}/{chapter_count}")
                with chapter.open() as handle:
                    self._convert_chapter(
                        book_title=book.package_document.title,
                        book_creator=book.package_document.creator,
                        chapter_num=chapter_num,
                        chapter_count=chapter_count,
                        book_directory=book_directory,
                        content=handle,
                    )

    def _convert_chapter(
        self,
        *,
        book_title: str | None,
        book_creator: str | None,
        chapter_num: int,
        chapter_count: int,
        book_directory: Path,
        content: IO[bytes],
    ) -> None:
        with TemporaryDirectory(
            prefix=".epub2audio-tmp-",
            dir=book_directory,
        ) as temp:
            temp_directory = Path(temp)

            document = self.preprocessor.process(content)
            if not document.content_chunks:
                logging.warning("Empty chapter")
                return

            chunk_files: list[Path] = []
            for n, chunk in enumerate(document.content_chunks, start=1):
                logging.info(
                    f"Processing chapter {chapter_num}/{chapter_count} "
                    f"chunk {n}/{len(document.content_chunks)}"
                )
                chunk_path = temp_directory / f"{n:06}.wav"
                if self._synthesize(chunk, chunk_path):
                    chunk_files.append(chunk_path)
                else:
                    logging.warning("Processing chunk failed")

            if not chunk_files:
                logging.warning("Empty chapter")
                return

            logging.debug("Combining chunks")
            combined_path = temp_directory / "combined.wav"
            audio.concatenate_wave_files(
                combined_path,
                chunk_files[0],
                *itertools.islice(
                    common.intersperse(chunk_files, INTER_CHUNK_SILENCE),
                    1,
                    None,
                ),
            )

            output_path = book_directory / f"{chapter_num:04}.mp3"
            logging.info(f"Encoding chapter to {output_path}")
            audio.encode_audio_file(combined_path, output_path)
            _add_tags_to_file(
                output_path,
                track=(chapter_num, chapter_count),
                title=document.title,
                artist=book_creator,
                album=book_title,
            )

    def _synthesize(self, text: str, output_path: Path) -> bool:
        while True:
            try:
                self.synthesizer.generate_to_file(text, output_path)
                return True
            except Exception as err:
                logging.error(f"Failed to synthesize chunk (input {text!r})")
                logging.exception(err)
                action = self.error_handler.handle_error(text)
                if action is None:
                    return False
                else:
                    text = action


def _add_tags_to_file(
    path: Path,
    *,
    track: tuple[int, int] | None = None,
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
) -> None:
    tags = id3.ID3(path)
    if track is not None:
        tags["TRCK"] = id3.TRCK(
            encoding=id3.Encoding.UTF8,
            text=[f"{track[0]}/{track[1]}"],
        )
    if title is not None:
        tags["TIT2"] = id3.TIT2(
            encoding=id3.Encoding.UTF8,
            text=[title],
        )
    if artist is not None:
        tags["TPE1"] = id3.TPE1(
            encoding=id3.Encoding.UTF8,
            text=[artist],
        )
    if album is not None:
        tags["TALB"] = id3.TALB(
            encoding=id3.Encoding.UTF8,
            text=[album],
        )
    tags.save()


def _book_directory_name(
    input_path: Path,
    book: EPubFile,
) -> str:
    title = book.package_document.title
    if title is None:
        title = input_path.stem
    return DIR_NAME_REGEX.sub("", title)


def _is_chapter(item: EPubItem) -> bool:
    return (
        item.linear
        and item.item.media_type == "application/xhtml+xml"
        and item.item.properties != "nav"
    )
