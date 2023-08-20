from collections.abc import Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import IO, Type
from zipfile import ZipFile

from lxml import etree  # type: ignore
from lxml.etree import ElementBase  # type: ignore

from .common import first


@dataclass(frozen=True)
class Item:
    href: str
    media_type: str
    properties: str | None


@dataclass(frozen=True)
class ItemRef:
    idref: str
    linear: bool = True


@dataclass(frozen=True)
class PackageDocument:
    title: str | None
    creator: str | None
    manifest: dict[str, Item]
    spine: list[ItemRef]


_CONTAINER_NAMESPACES = {
    "con": "urn:oasis:names:tc:opendocument:xmlns:container",
}

_PACKAGE_DOCUMENT_NAMESPACES = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
}


class EPubItem:
    def __init__(self, file: "EPubFile", item: Item, linear: bool) -> None:
        self._file = file
        self.item = item
        self.linear = linear

    def open(self) -> IO[bytes]:
        return self._file._handle.open(str(self._file._root_dir_path / self.item.href))


class EPubError(Exception):
    """EPub Error"""


class EPubFile(AbstractContextManager["EPubFile"]):
    def __init__(self, path: Path | str) -> None:
        self._handle = ZipFile(path)
        self._verify_mimetype()
        self._read_container()
        self._read_package_document()

    def _parse_manifest(self, element: ElementBase) -> dict[str, Item]:
        manifest = {}
        for item in element.xpath(
            "//opf:item", namespaces=_PACKAGE_DOCUMENT_NAMESPACES
        ):
            id = item.get("id")
            if id is None:
                raise EPubError("Attribute 'id' missing from item.")
            href = item.get("href")
            if href is None:
                raise EPubError("Attribute 'href' missing from item.")
            media_type = item.get("media-type")
            if media_type is None:
                raise EPubError("Attribute 'media-type' missing from item.")
            properties = item.get("properties")
            manifest[id] = Item(
                href=href,
                media_type=media_type,
                properties=properties,
            )
        return manifest

    def _parse_spine(self, element: ElementBase) -> list[ItemRef]:
        spine = []
        for itemref in element.xpath(
            "//opf:itemref", namespaces=_PACKAGE_DOCUMENT_NAMESPACES
        ):
            idref = itemref.get("idref")
            if idref is None:
                raise EPubError("Attribute 'idref' missing from itemref.")
            linear = itemref.get("linear")
            if linear is None or linear in {"true", "yes"}:
                linear = True
            elif linear in {"false", "no"}:
                linear = False
            else:
                raise EPubError("Attribute 'linear' has an invalid value")
            spine.append(ItemRef(idref=idref, linear=linear))
        return spine

    def _read_container(self) -> None:
        with self._handle.open("META-INF/container.xml") as handle:
            root = etree.parse(handle).getroot()
            root_file = first(
                root.xpath(
                    "//con:rootfiles/con:rootfile",
                    namespaces=_CONTAINER_NAMESPACES,
                )
            )
            if root_file is None:
                raise EPubError("Missing root file")
            root_file_path = root_file.get("full-path")
            if root_file_path is None:
                raise EPubError("Missing root file path")
            self._root_file_path = Path(root_file_path)
            self._root_dir_path = self._root_file_path.parent

    def _verify_mimetype(self) -> None:
        mimetype = self._handle.read("mimetype")
        if mimetype != b"application/epub+zip":
            raise EPubError("Invalid EPub")

    def _read_package_document(self) -> None:
        with self._handle.open(str(self._root_file_path)) as handle:
            root = etree.parse(handle).getroot()
            title = first(
                root.xpath(
                    "//opf:metadata/dc:title", namespaces=_PACKAGE_DOCUMENT_NAMESPACES
                )
            )
            if title is not None:
                title = title.text
            creator = first(
                root.xpath(
                    "//opf:metadata/dc:creator", namespaces=_PACKAGE_DOCUMENT_NAMESPACES
                )
            )
            if creator is not None:
                creator = creator.text
            manifest = first(
                root.xpath("//opf:manifest", namespaces=_PACKAGE_DOCUMENT_NAMESPACES)
            )
            if manifest is None:
                raise EPubError("Missing manifest")
            manifest_dict = self._parse_manifest(manifest)
            spine = first(
                root.xpath("//opf:spine", namespaces=_PACKAGE_DOCUMENT_NAMESPACES)
            )
            if spine is None:
                raise EPubError("Missing spine")
            spine_list = self._parse_spine(spine)
            self.package_document = PackageDocument(
                title=title,
                creator=creator,
                manifest=manifest_dict,
                spine=spine_list,
            )

    def spine(self) -> Iterator[EPubItem]:
        for item_ref in self.package_document.spine:
            item = self.package_document.manifest.get(item_ref.idref)
            if item is None:
                raise EPubError("Missing item")
            yield EPubItem(self, item, item_ref.linear)

    def close(self) -> None:
        self._handle.close()

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
