import itertools
from abc import ABC, abstractmethod
from typing import Iterator, List, Optional




_id_counter = itertools.count(1)


def _advance_id_counter(max_id: int) -> None:
    global _id_counter
    next_id = next(_id_counter)
    _id_counter = itertools.count(max(next_id, max_id + 1))

class TextElement(ABC):
    """Base class for every node in the document tree."""

    def __init__(self, name: str):
        self.id: int = next(_id_counter)
        self.name = name
        self.parent: Optional['ContainerElement'] = None

    def to_dict(self) -> dict:
        return {"type": type(self).__name__, "id": self.id, "name": self.name}

    @classmethod
    def from_dict(cls, data: dict) -> 'TextElement':
        tag = data.get("type")
        element_class = _TYPE_REGISTRY.get(tag)
        if element_class is None:
            raise ValueError(f"Unknown text element type: {tag!r}")
        return element_class.from_dict(data)

    def _restore_id(self, data: dict) -> None:
        self.id = data["id"]
        _advance_id_counter(self.id)

    @abstractmethod
    def render(self) -> str:
        pass

    @abstractmethod
    def accept(self, visitor: 'ElementVisitor'):
        pass

    def walk(self) -> Iterator['TextElement']:
        yield self

    def describe(self) -> str:
        return f"{self.__class__.__name__}: {self.name}"

    def get_toc(self) -> str:
        return ""


class LeafElement(TextElement):
    """Marker base class for elements that cannot contain children."""


class ContainerElement(TextElement):
    """Base class for elements that hold children and can be navigated into."""

    def __init__(self, name: str):
        super().__init__(name)
        self.children: List[TextElement] = []

    def add_child(self, element: TextElement) -> None:
        element.parent = self
        self.children.append(element)

    def find_child_by_name(self, name: str) -> Optional[TextElement]:
        for child in self.children:
            if child.name == name:
                return child
        return None

    def remove_child(self, element: TextElement) -> None:
        if element in self.children:
            self.children.remove(element)
            element.parent = None

    def walk(self) -> Iterator[TextElement]:
        yield self
        for child in self.children:
            yield from child.walk()

    def render_children(self) -> str:
        return "".join(child.render() for child in self.children)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["children"] = [child.to_dict() for child in self.children]
        return data

    def _restore_children(self, data: dict) -> None:
        for child_data in data["children"]:
            self.add_child(TextElement.from_dict(child_data))



class PlainText(LeafElement):
    """Contains raw text."""

    def __init__(self, name: str, text: str):
        super().__init__(name)
        self.text = text

    def render(self) -> str:
        return self.text

    def accept(self, visitor: 'ElementVisitor'):
        return visitor.visit_plain_text(self)

    def describe(self) -> str:
        return f"Text '{self.name}': {self.text}"

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["text"] = self.text
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'PlainText':
        element = cls(data["name"], data["text"])
        element._restore_id(data)
        return element


class Link(LeafElement):
    """Contains a single link."""

    def __init__(self, name: str, text: str, url: str):
        super().__init__(name)
        self.text = text
        self.url = url

    def render(self) -> str:
        return f"[{self.text}]({self.url})"

    def accept(self, visitor: 'ElementVisitor'):
        return visitor.visit_link(self)

    def describe(self) -> str:
        return f"Link '{self.name}': [{self.text}]({self.url})"

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update(text=self.text, url=self.url)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Link':
        element = cls(data["name"], data["text"], data["url"])
        element._restore_id(data)
        return element


class Image(LeafElement):
    """Contains a single image."""

    def __init__(self, name: str, alt: str, src: str):
        super().__init__(name)
        self.alt_text = alt
        self.src = src

    def render(self) -> str:
        return f"\n{self.alt_text}\n{self.src}"

    def accept(self, visitor: 'ElementVisitor'):
        return visitor.visit_image(self)

    def describe(self) -> str:
        return f"Image '{self.name}': {self.alt_text} ({self.src})"

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update(alt_text=self.alt_text, src=self.src)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Image':
        element = cls(data["name"], alt=data["alt_text"], src=data["src"])
        element._restore_id(data)
        return element


class Paragraph(LeafElement):
    """Paragraph made of plain text sentences and links, rendered together."""

    def __init__(self, name: str, elements: List[TextElement] = None):
        super().__init__(name)
        self.elements = elements if elements is not None else []

    def add_element(self, element: TextElement) -> 'Paragraph':
        self.elements.append(element)
        return self

    def render(self) -> str:
        return "".join(element.render() for element in self.elements) + "\n"

    def accept(self, visitor: 'ElementVisitor'):
        return visitor.visit_paragraph(self)

    def describe(self) -> str:
        preview = "".join(e.render() for e in self.elements)
        return f"Paragraph '{self.name}': {preview}"

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["elements"] = [element.to_dict() for element in self.elements]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Paragraph':
        element = cls(data["name"])
        for element_data in data["elements"]:
            element.add_element(TextElement.from_dict(element_data))
        element._restore_id(data)
        return element



class Header(ContainerElement):
    """A heading that also acts as a section holding nested content."""

    def __init__(self, name: str, text: str, level: int = 1):
        super().__init__(name)
        self.text = text
        self.level = max(1, min(level, 6))

    def render(self) -> str:
        return f"{' .' * self.level} {self.text}\n" + self.render_children()

    def accept(self, visitor: 'ElementVisitor'):
        return visitor.visit_header(self)

    def describe(self) -> str:
        return f"Header(level={self.level}) '{self.name}': {self.text}"

    def get_toc(self) -> str:
        indent = " ." * self.level
        return f"{indent} {self.text}"

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update(text=self.text, level=self.level)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Header':
        element = cls(data["name"], data["text"], data["level"])
        element._restore_id(data)
        element._restore_children(data)
        return element


class Document(ContainerElement):
    """Root container of the whole document."""

    def __init__(self):
        super().__init__(name="")

    def render(self) -> str:
        return self.render_children()

    def accept(self, visitor: 'ElementVisitor'):
        return visitor.visit_document(self)

    def describe(self) -> str:
        return "Document (root)"

    def get_table_of_contents(self) -> str:
        visitor = TocVisitor()
        self.accept(visitor)
        return "\n".join(visitor.lines)

    def to_dict(self) -> dict:
        return {**super().to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> 'Document':
        document = cls()
        document.name = data["name"]
        document._restore_id(data)
        document._restore_children(data)
        return document


class ElementVisitor(ABC):

    @abstractmethod
    def visit_leaf(self, element: LeafElement):
        pass

    @abstractmethod
    def visit_container(self, element: ContainerElement):
        pass

    def visit_plain_text(self, element: PlainText):
        return self.visit_leaf(element)

    def visit_link(self, element: Link):
        return self.visit_leaf(element)

    def visit_image(self, element: Image):
        return self.visit_leaf(element)

    def visit_paragraph(self, element: Paragraph):
        return self.visit_leaf(element)

    def visit_header(self, element: Header):
        return self.visit_container(element)

    def visit_document(self, element: Document):
        return self.visit_container(element)


class TocVisitor(ElementVisitor):

    def __init__(self):
        self.lines: List[str] = []

    def visit_leaf(self, element: LeafElement) -> None:
        pass

    def visit_container(self, element: ContainerElement) -> None:
        for child in element.children:
            child.accept(self)

    def visit_header(self, element: Header) -> None:
        self.lines.append(element.get_toc())
        self.visit_container(element)


class TreeLinesVisitor(ElementVisitor):

    def __init__(self, show_id: bool = False):
        self.show_id = show_id
        self.lines: List[str] = []
        self._depth = 0

    def _add_line(self, element: TextElement) -> None:
        prefix = f"[{element.id}] " if self.show_id else ""
        self.lines.append(f"{'  ' * self._depth}{prefix}{element.describe()}")

    def visit_leaf(self, element: LeafElement) -> None:
        self._add_line(element)

    def visit_container(self, element: ContainerElement) -> None:
        self._add_line(element)
        self._depth += 1
        for child in element.children:
            child.accept(self)
        self._depth -= 1


_TYPE_REGISTRY = {
    "PlainText": PlainText,
    "Link": Link,
    "Image": Image,
    "Paragraph": Paragraph,
    "Header": Header,
    "Document": Document,
}



class TextDocumentBuilder:

    def __init__(self):
        self._document = Document()

    def add_header(self, name: str, text: str, level: int = 1) -> 'TextDocumentBuilder':
        self._document.add_child(Header(name, text, level))
        return self

    def add_image(self, name: str, alt_text: str, src: str) -> 'TextDocumentBuilder':
        self._document.add_child(Image(name, alt_text, src))
        return self

    def create_paragraph(self, name: str) -> 'ParagraphBuilder':
        return ParagraphBuilder(self, name)

    def build(self) -> Document:
        return self._document


class ParagraphBuilder:
    """Tools for building paragraphs."""

    def __init__(self, parent_builder: TextDocumentBuilder, name: str):
        self._parent_builder = parent_builder
        self._paragraph = Paragraph(name)

    def add_text(self, text: str) -> 'ParagraphBuilder':
        self._paragraph.add_element(PlainText(f"{self._paragraph.name}_text", text))
        return self

    def add_link(self, text: str, url: str) -> 'ParagraphBuilder':
        self._paragraph.add_element(Link(f"{self._paragraph.name}_link", text, url))
        return self

    def end_paragraph(self) -> TextDocumentBuilder:
        self._parent_builder._document.add_child(self._paragraph)
        return self._parent_builder