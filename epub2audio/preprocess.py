import re
from collections.abc import Callable, Iterator, Sequence, Set
from re import Pattern
from typing import IO, Final
from dataclasses import dataclass

from lxml import html  # type: ignore
from lxml.etree import ElementBase  # type: ignore

from .common import first

# These very ad-hoc patterns try to transform the text content into something
# that TTS can handle better.
DEFAULT_TEXT_FILTERS: Final[Sequence[tuple[Pattern[str], str]]] = (
    # Handle common abbreviations
    (re.compile(r"\bch\.(?=[\s])", re.IGNORECASE), "chapter"),
    (re.compile(r"\bpt\.(?=[\s])", re.IGNORECASE), "part"),
    # Turn & to and
    (re.compile(r"&"), " and "),
    # Turn % to percent
    (re.compile(r"%"), " percent "),
    # Sequences of punctuations seem to confuse TTS, replace them with a single period
    (re.compile(r"[!?:;.…]+"), "."),
    # Deduplicate commas
    (re.compile(r",+"), ","),
    # Remove hyphens that are not within words
    (re.compile(r"(?<![a-zA-Z0-9])-|-(?![a-zA-Z0-9])"), ""),
    # Remove single quotes that are not within words
    (re.compile(r"(?<![a-zA-Z0-0])'|'(?![a-zA-Z0-9])"), ""),
    # Discard different types of parentheses along with some other special characters
    (re.compile(r'[()\[\]{}"“”‘’*~_]'), ""),
    # Deduplicate whitespace
    (re.compile(r"\s+"), " "),
    # Turn strings consisting of only whitespace into empty strings
    (re.compile(r"^\s+$"), ""),
)

DEFAULT_BREAKING_ELEMENTS = {
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "blockquote",
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    "img",
}


def get_children(element: ElementBase) -> Iterator[str | ElementBase]:
    """Get element's children. Children are either text nodes or elements."""
    if element.text is not None:
        yield element.text
    for child in element.iterchildren():
        yield child
        if child.tail is not None:
            yield child.tail


class ElementVisitor:
    def enter_element(self, element: ElementBase) -> None:
        pass

    def exit_element(self, element: ElementBase) -> None:
        pass

    def text_node(self, text: str) -> None:
        pass


def visit(element: str | ElementBase, visitor: ElementVisitor) -> None:
    if isinstance(element, str):
        visitor.text_node(element)
    else:
        visitor.enter_element(element)
        for child in get_children(element):
            visit(child, visitor)
        visitor.exit_element(element)


class ChunkingVisitor(ElementVisitor):
    def __init__(
        self,
        sink: Callable[[str], None],
        breaking_elements: Set[str] = DEFAULT_BREAKING_ELEMENTS,
    ) -> None:
        self.sink = sink
        self.breaking_elements = breaking_elements
        self.current_chunk = ""

    def enter_element(self, element: ElementBase) -> None:
        self._maybe_emit_chunk(element)

        # We emit an artificial text node for images
        if element.tag == "img":
            alt = element.get("alt")
            if alt is not None and alt:
                self.text_node(f"Image with description {alt}")
            else:
                self.text_node("Image without a description")

    def exit_element(self, element: ElementBase) -> None:
        self._maybe_emit_chunk(element)

    def text_node(self, text: str) -> None:
        self.current_chunk += text

    def _maybe_emit_chunk(self, element: ElementBase) -> None:
        if element.tag in self.breaking_elements:
            if self.current_chunk:
                self.sink(self.current_chunk)
            self.current_chunk = ""


@dataclass(frozen=True)
class Document:
    title: str | None
    content_chunks: list[str]


class ContentPreprocessor:
    def __init__(
        self,
        text_filters: Sequence[tuple[Pattern[str], str]] = DEFAULT_TEXT_FILTERS,
    ) -> None:
        self.text_filters = text_filters

    def process(self, input: IO[bytes]) -> Document:
        root = html.parse(input).getroot()

        title = first(root.xpath("//title[1]"))
        title_text = None
        if title is not None:
            title_text = title.text

        body = first(root.xpath("//body[1]"))
        if body is None:
            raise ValueError("Missing body")

        result: list[str] = []

        def consume(chunk: str) -> None:
            filtered = self._filter_text(chunk)
            if filtered:
                result.append(filtered)

        visit(body, ChunkingVisitor(consume))

        return Document(
            title=title_text,
            content_chunks=result,
        )

    def _filter_text(self, text: str) -> str:
        text = text.strip()
        for regex, replacement in self.text_filters:
            text = regex.sub(replacement, text)
        return text.lower()
