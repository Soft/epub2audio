import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import Final

DEFAULT_EDITOR: Final[str] = "vi"


class ErrorHandler(ABC):
    @abstractmethod
    def handle_error(self, text: str) -> str | None:
        """
        Error handler receives the problematic input and returns the modified
        input or None if the input should be ignored.
        """


class SkipErrorHandler(ErrorHandler):
    def handle_error(self, text: str) -> str | None:
        logging.info("Skipping chunk")
        return None


class EditInteractivelyErrorHandler(ErrorHandler):
    def __init__(self) -> None:
        self.editor = os.environ.get("EDITOR", DEFAULT_EDITOR)

    def handle_error(self, text: str) -> str | None:
        logging.info("Opening editor")
        with TemporaryDirectory() as temp:
            temp_file = Path(temp) / "input.txt"
            temp_file.write_text(text)
            check_call([self.editor, str(temp_file)])
            return temp_file.read_text()


class AskErrorHandler(ErrorHandler):
    def handle_error(self, text: str) -> str | None:
        while True:
            choice = input("[s]kip, [e]dit: ").lower()
            if choice == "s":
                return SkipErrorHandler().handle_error(text)
            if choice == "e":
                return EditInteractivelyErrorHandler().handle_error(text)
