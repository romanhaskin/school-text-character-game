import pytest

import os
import sys


current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))

sys.path.insert(0, project_root)

from Core.text import Document, Header, PlainText, Link, Image, Paragraph
from Infra.Display.textWorker import DocumentShell


@pytest.fixture
def mock_console(mocker):
    return mocker.MagicMock()


@pytest.fixture
def shell(mock_console):
    return DocumentShell(mock_console)


@pytest.fixture
def simple_doc(shell):
    chapter = Header("chapter", "Chapter", 1)
    section = Header("section", "Section", 2)
    intro = PlainText("intro", "hello")
    shell.document.add_child(intro)
    shell.document.add_child(chapter)
    chapter.add_child(section)
    return shell, intro, chapter, section


def logged(mock_console):
    return [c.args[0] for c in mock_console.console_log.call_args_list]


def feed(mock_console, *answers):
    mock_console.get_str.side_effect = list(answers)


def test_helpers_and_pwd(simple_doc, mock_console):
    shell, intro, chapter, section = simple_doc
    assert shell._find_by_id(shell.document, section.id) is section
    assert shell._find_by_id(shell.document, intro.id) is intro
    assert shell._find_by_id(shell.document, shell.document.id) is shell.document
    assert shell._find_by_id(shell.document, 987654) is None

    assert shell._path_of(shell.document) == "/"
    assert shell._path_of(chapter) == "/chapter"
    assert shell._path_of(section) == "/chapter/section"

    shell.current = section
    shell.cmd_pwd([])
    mock_console.console_log.assert_called_once_with("/chapter/section")


def test_up_and_cd(simple_doc, mock_console):
    shell, intro, chapter, section = simple_doc

    shell.cmd_up([])
    assert logged(mock_console) == ["Already at the root of the document."]
    assert shell.current is shell.document

    shell.cmd_cd(["chapter/section"])
    assert shell.current is section
    shell.cmd_up([])
    assert shell.current is chapter
    shell.cmd_cd(["/"])
    assert shell.current is shell.document
    shell.cmd_cd(["/chapter"])
    assert shell.current is chapter

    shell.cmd_cd(["/"])
    shell.cmd_cd(["--id", str(section.id)])
    assert shell.current is section


def test_cd_errors_keep_current(simple_doc, mock_console):
    shell, intro, *_ = simple_doc

    shell.cmd_cd(["ghost"])
    shell.cmd_cd(["intro"])
    shell.cmd_cd(["--id"])
    shell.cmd_cd(["--id", "abc"])
    shell.cmd_cd(["--id", "987654"])
    shell.cmd_cd(["--id", str(intro.id)])

    assert logged(mock_console) == [
        "No such container: ghost",
        "No such container: intro",
        "Usage: cd --id <container_id>",
        "Invalid id: abc",
        "No container found with id 987654",
        f"No container found with id {intro.id}",
    ]
    assert shell.current is shell.document


def test_print(simple_doc, mock_console):
    shell, intro, chapter, section = simple_doc
    shell.current = chapter

    shell.cmd_print([])
    shell.cmd_print(["--whole"])
    shell.cmd_print(["--id"])
    shell.cmd_print(["--whole", "--id"])

    assert logged(mock_console) == [
        f"{chapter.render()} ",
        f"{shell.document.render()} ",
        f"[{chapter.id}] {chapter.describe()}",
        f"  [{section.id}] {section.describe()}",
        f"[{shell.document.id}] Document (root)",
        f"  [{intro.id}] {intro.describe()}",
        f"  [{chapter.id}] {chapter.describe()}",
        f"    [{section.id}] {section.describe()}",
    ]


def test_rm(simple_doc, mock_console):
    shell, intro, chapter, section = simple_doc

    shell.cmd_rm(["ghost"])
    assert logged(mock_console)[-1] == "No element named 'ghost' here."
    mock_console.get_str.assert_not_called()

    feed(mock_console, "n")
    shell.cmd_rm(["intro"])
    assert intro in shell.document.children
    assert logged(mock_console)[-1] == "Cancelled."

    feed(mock_console, "y")
    shell.cmd_rm(["intro"])
    assert intro not in shell.document.children
    assert intro.parent is None
    assert logged(mock_console)[-1] == "Removed 'intro'."

    shell.current = chapter
    feed(mock_console, "y")
    shell.cmd_rm(["section"])
    assert shell.current is chapter
    assert chapter.children == []


def test_rm_without_args(simple_doc, mock_console):
    shell, _, chapter, section = simple_doc

    shell.cmd_rm([])
    assert logged(mock_console)[-1] == "Cannot remove the document root."
    mock_console.get_str.assert_not_called()

    shell.current = section
    feed(mock_console, "Y")
    shell.cmd_rm([])
    assert shell.current is chapter
    assert section not in chapter.children


def test_add_errors_and_cancel(shell, mock_console):
    shell.cmd_add(["leaf"])
    shell.cmd_add(["blob", "text"])
    shell.cmd_add(["container", "text"])
    shell.cmd_add(["leaf", "header"])
    feed(mock_console, "", "")
    shell.cmd_add(["container", "header"])
    shell.cmd_add(["leaf", "text"])

    msgs = logged(mock_console)
    assert "Usage: add" in msgs[0]
    assert msgs[1] == "First argument must be 'container' or 'leaf'."
    assert msgs[2].startswith("Unknown container type 'text'. Available: header")
    assert msgs[3].startswith("Unknown leaf type 'header'. Available: text, link, image, paragraph")
    assert msgs[4:] == ["Cancelled.", "Cancelled."]
    assert shell.document.children == []


def test_add_elements(simple_doc, mock_console):
    shell, _, chapter, _ = simple_doc
    shell.document.children.clear()

    feed(mock_console, "h", "Welcome", "3")
    shell.cmd_add(["container", "header"])
    feed(mock_console, "h2", "Welcome", "x")
    shell.cmd_add(["container", "header"])
    feed(mock_console, "t", "hi")
    shell.cmd_add(["leaf", "TEXT"])
    feed(mock_console, "l", "click", "http://x.y")
    shell.cmd_add(["leaf", "link"])
    feed(mock_console, "i", "a cat", "cat.png")
    shell.cmd_add(["leaf", "image"])

    header, header2, text, link, image = shell.document.children
    assert isinstance(header, Header)
    assert (header.name, header.text, header.level) == ("h", "Welcome", 3)
    assert header.parent is shell.document
    assert header2.level == 1
    assert isinstance(text, PlainText) and (text.name, text.text) == ("t", "hi")
    assert logged(mock_console)[-1].startswith("Added ")
    assert isinstance(link, Link) and (link.text, link.url) == ("click", "http://x.y")
    assert isinstance(image, Image) and (image.alt_text, image.src) == ("a cat", "cat.png")

    shell.current = chapter
    feed(mock_console, "inner", "x")
    shell.cmd_add(["leaf", "text"])
    assert chapter.children[-1].name == "inner"


def test_add_paragraph(shell, mock_console):
    feed(mock_console, "p", "first", "y", "here", "http://a", "second", "n", "")
    shell.cmd_add(["leaf", "paragraph"])
    paragraph = shell.document.children[0]
    assert isinstance(paragraph, Paragraph)
    assert [e.name for e in paragraph.elements] == ["p_text1", "p_link1", "p_text2"]
    assert paragraph.render() == "first[here](http://a)second\n"

    feed(mock_console, "empty", "")
    shell.cmd_add(["leaf", "paragraph"])
    assert shell.document.children[1].elements == []


def test_commands_and_serialization(simple_doc):
    shell, intro, _, section = simple_doc
    assert set(shell.COMMANDS) == {"pwd", "print", "add", "rm", "up", "cd"}
    assert shell.COMMANDS["pwd"] == shell.cmd_pwd

    shell.current = section
    restored = DocumentShell.from_dict(shell.to_dict())
    assert restored.document.render() == shell.document.render()
    assert restored.current.id == section.id
    assert restored.current is not section
    assert restored._path_of(restored.current) == "/chapter/section"

    data = shell.to_dict()
    data["current_id"] = intro.id
    assert DocumentShell.from_dict(data).current.parent is None
    data["current_id"] = 987654
    restored = DocumentShell.from_dict(data)
    assert restored.current is restored.document
