import logging
from argparse import ArgumentParser, Namespace
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final

from .error import (
    AskErrorHandler,
    EditInteractivelyErrorHandler,
    ErrorHandler,
    SkipErrorHandler,
)

DEFAULT_MODEL: Final[str] = "tts_models/en/ljspeech/tacotron2-DDC_ph"

ERROR_HANDLERS: Final[Mapping[str, Callable[[], ErrorHandler]]] = {
    "ask": AskErrorHandler,
    "skip": SkipErrorHandler,
    "edit": EditInteractivelyErrorHandler,
}

LOG_LEVELS: Final[Mapping[str, int]] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Convert EPub files to audiobooks.")
    parser.add_argument(
        "input",
        metavar="PATH",
        type=Path,
        nargs="+",
        help="input EPub files",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="DIR",
        type=Path,
        default=Path.cwd(),
        help="output directory",
    )
    parser.add_argument(
        "--model",
        metavar="NAME",
        help="model name",
        default=DEFAULT_MODEL,
    )
    parser.add_argument(
        "--speaker-wav",
        metavar="PATH",
        help="speaker wav file path",
    )
    parser.add_argument(
        "--language",
        metavar="LANG",
        help="language name",
    )
    parser.add_argument(
        "--on-error",
        choices=ERROR_HANDLERS.keys(),
        default="ask",
        help="strategy for handling synthesizer errors",
    )
    parser.add_argument(
        "--log-level",
        choices=LOG_LEVELS.keys(),
        default="info",
        help="set log level",
    )
    return parser.parse_args()


def run(
    *,
    input: list[Path],
    output: Path,
    model_name: str,
    error_handler_string: str,
    speaker_wav: str | None = None,
    language_name: str | None = None,
) -> None:
    # Load lazily to allow argument parsing to happen earlier
    from .converter import EPubToAudioConverter
    from .synthesizer import Synthesizer

    synthesizer = Synthesizer(
        model_name=model_name,
        speaker_wav=speaker_wav,
        language_name=language_name,
    )
    converter = EPubToAudioConverter(
        synthesizer=synthesizer,
        error_handler=ERROR_HANDLERS[error_handler_string](),
    )
    for file in input:
        converter.convert(file, output)


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=LOG_LEVELS[args.log_level])
    run(
        input=args.input,
        output=args.output,
        model_name=args.model,
        error_handler_string=args.on_error,
        speaker_wav=args.speaker_wav,
        language_name=args.language,
    )
