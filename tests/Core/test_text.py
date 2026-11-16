import pytest

import os
import sys


current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))

sys.path.insert(0, project_root)

import itertools
import pytest
from Core.text import (
    TextElement,
    PlainText,
    Link,
    Image,
    Paragraph,
    Header,
    Document,
    TextDocumentBuilder,
)


@pytest.fixture(autouse=True)
def reset_global_id_counter():
    """Resets the global document tree counter state before each test run."""
    import Core.text
    Core.text._id_counter = itertools.count(1)



def test_id_count():
    t1 = PlainText("t1", "hello")
    t2 = PlainText("t2", "World")
    
    assert t1.id == 1
    assert t2.id == 2


def test_container_child_management():

    doc = Document()
    p1 = Paragraph("p1")
    p2 = Paragraph("p2")

    doc.add_child(p1)
    doc.add_child(p2)
    assert len(doc.children) == 2
    assert p1.parent == doc

    assert doc.find_child_by_name("p1") == p1
    assert doc.find_child_by_name("non-existent") is None

    doc.remove_child(p1)
    assert len(doc.children) == 1
    assert p1.parent is None


@pytest.mark.parametrize("element, expected_render, expected_describe",
    [   (
            PlainText("txt", "text"),
            "text",
            "Text 'txt': text"
        ),
        (
            Link("lnk", "Google", "https://google.com"),
            "[Google](https://google.com)",
            "Link 'lnk': [Google](https://google.com)"
        ),
        (
            Image("img", "alt", "img.png"),
            "\nalt\nimg.png",
            "Image 'img': alt (img.png)"
        ),])
def test_leaf_elements_rendering_and_descriptions(element, expected_render, expected_describe):

    assert element.render() == expected_render
    assert element.describe() == expected_describe


def test_header_level_limits():

    h_low = Header("h1", "Title", level=0)
    h_high = Header("h2", "Title", level=10)

    assert h_low.level == 1
    assert h_high.level == 6
    assert h_low.get_toc() == " . Title"


def test_document_table_of_contents():

    doc = Document()
    doc.add_child(Header("h1", "start", level=1))
    doc.add_child(Paragraph("p1"))
    doc.add_child(Header("h2", "end", level=2))

    expected_toc = " . start\n . . end"
    assert doc.get_table_of_contents() == expected_toc


def test_document_serialization_and_deserialization_roundtrip():

    doc = Document()
    header = Header("hdr", "Main Header", level=1)
    paragraph = Paragraph("pr")
    paragraph.add_element(PlainText("txt", "text"))
    paragraph.add_element(Link("lnk", "Link", "http://test.com"))
    
    doc.add_child(header)
    doc.add_child(paragraph)

    saved_dict = doc.to_dict()

    restored_doc = TextElement.from_dict(saved_dict)

    assert isinstance(restored_doc, Document)
    assert restored_doc.id == doc.id
    assert len(restored_doc.children) == 2
    assert restored_doc.render() == doc.render()


def test_corrupted_data_unknown_type_error():

    corrupted_data = {"type": "InvalidType", "id": 9, "name": "corrupted >:)"}
    with pytest.raises(ValueError, match="Unknown text element type: 'InvalidType'"):
        TextElement.from_dict(corrupted_data)


def test_text_document_builder():

    builder = TextDocumentBuilder()
    doc = (
        builder.add_header("h1", "My Manual", level=1)
        .create_paragraph("intro")
        .add_text("Welcome to")
        .add_link("the platform", "https://platform.com")
        .end_paragraph()
        .add_image("banner", "Logo Image", "logo.jpg")
        .build()
    )

    assert len(doc.children) == 3
    assert isinstance(doc.children[0], Header)
    assert isinstance(doc.children[1], Paragraph)
    assert isinstance(doc.children[2], Image)
    
    p_elements = doc.children[1].elements
    assert len(p_elements) == 2
    assert p_elements[0].render() == "Welcome to"


def test_walk_is_preorder_and_skips_paragraph_internals():
    from Core.text import PlainText
    doc = Document()
    outer = Header("a", "A", 1)
    inner = Header("b", "B", 2)
    text = PlainText("t", "x")
    para = Paragraph("p", [PlainText("pt", "y")])
    doc.add_child(outer)
    outer.add_child(inner)
    inner.add_child(text)
    outer.add_child(para)

    assert list(doc.walk()) == [doc, outer, inner, text, para]


def test_table_of_contents_includes_nested_headers():
    doc = Document()
    outer = Header("a", "A", 1)
    outer.add_child(Header("b", "B", 2))
    doc.add_child(outer)

    assert doc.get_table_of_contents() == " . A\n . . B"


def test_tree_lines_visitor_indents_and_shows_ids():
    from Core.text import TreeLinesVisitor
    doc = Document()
    header = Header("a", "A", 1)
    doc.add_child(header)

    plain = TreeLinesVisitor()
    doc.accept(plain)
    assert plain.lines == ["Document (root)", "  Header(level=1) 'a': A"]

    with_ids = TreeLinesVisitor(show_id=True)
    doc.accept(with_ids)
    assert with_ids.lines[1] == f"  [{header.id}] Header(level=1) 'a': A"
