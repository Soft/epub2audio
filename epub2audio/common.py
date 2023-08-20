import itertools
from collections.abc import Iterable, Iterator
from typing import TypeVar

ItemType = TypeVar("ItemType")


def first(iterable: Iterable[ItemType]) -> ItemType | None:
    return next(iter(iterable), None)


SeparatorType = TypeVar("SeparatorType")


def intersperse(
    iterable: Iterable[ItemType], separator: SeparatorType
) -> Iterator[ItemType | SeparatorType]:
    return itertools.islice(
        itertools.chain.from_iterable(
            zip(
                itertools.repeat(separator),
                iterable,
            ),
        ),
        1,
        None,
    )
