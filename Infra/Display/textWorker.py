from Core.text import *

CONTAINER_TYPES = ("header",)
LEAF_TYPES = ("text", "link", "image", "paragraph")


class DocumentShell:
    """Interactive cmd navigator/editor over a Document tree."""

    def __init__(self, console=None):
        self.console = console
        self.save_name = "text"
        self.document = Document()
        self.current: ContainerElement = self.document
        
        self.COMMANDS = {
                "pwd": self.cmd_pwd,
                "print": self.cmd_print,
                "add": self.cmd_add,
                "rm": self.cmd_rm,
                "up": self.cmd_up,
                "cd": self.cmd_cd,
        }


    def _find_by_id(self, node: TextElement, target_id: int) -> Optional[TextElement]:
        return next((n for n in node.walk() if n.id == target_id), None)

    def _path_of(self, node: TextElement) -> str:
        parts = []
        while node is not None and node.parent is not None:
            parts.append(node.name)
            node = node.parent
        return "/" + "/".join(reversed(parts))

    def to_dict(self) -> dict:
        return {
            "document": self.document.to_dict(),
            "current_id": self.current.id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DocumentShell':
        
        shell = cls()
        shell.document = Document.from_dict(data["document"])
        current = shell._find_by_id(shell.document, data["current_id"])
        shell.current = current if isinstance(current, ContainerElement) else shell.document
        return shell

    def _print_tree(self, node: TextElement, show_id: bool) -> None:
        visitor = TreeLinesVisitor(show_id)
        node.accept(visitor)
        for line in visitor.lines:
            self.console.console_log(line)


    def cmd_pwd(self, args: List[str]) -> None:
        self.console.console_log(self._path_of(self.current))

    def cmd_print(self, args: List[str]) -> None:
        show_whole = "--whole" in args
        show_id = "--id" in args
        target: TextElement = self.document if show_whole else self.current

        if show_id:
            self._print_tree(target, show_id=True)
        else:
            self.console.console_log(f"{target.render()} ")

    def cmd_up(self, args: List[str]) -> None:
        if self.current.parent is None:
            self.console.console_log("Already at the root of the document.")
            return
        self.current = self.current.parent

    def cmd_cd(self, args: List[str]) -> None:
        if not args:
            self.console.console_log("Usage: cd <path> | cd --id <container_id>")
            return

        if args[0] == "--id":
            if len(args) < 2:
                self.console.console_log("Usage: cd --id <container_id>")
                return
            try:
                target_id = int(args[1])
            except ValueError:
                self.console.console_log(f"Invalid id: {args[1]}")
                return
            node = self._find_by_id(self.document, target_id)
            if node is None or not isinstance(node, ContainerElement):
                self.console.console_log(f"No container found with id {target_id}")
                return
            self.current = node
            return

        path = args[0]
        node: ContainerElement = self.document if path.startswith("/") else self.current
        segments = [seg for seg in path.split("/") if seg]
        for segment in segments:
            child = node.find_child_by_name(segment)
            if child is None or not isinstance(child, ContainerElement):
                self.console.console_log(f"No such container: {segment}")
                return
            node = child
        self.current = node

    def cmd_rm(self, args: List[str]) -> None:
        if args:
            name = args[0]
            target = self.current.find_child_by_name(name)
            if target is None:
                self.console.console_log(f"No element named '{name}' here.")
                return
            move_to_parent = False
        else:
            if self.current.parent is None:
                self.console.console_log("Cannot remove the document root.")
                return
            target = self.current
            move_to_parent = True

        confirm = self.console.get_str(f"Delete '{target.name}' ({target.describe()})? [y/N] ")
        if confirm.lower() != "y":
            self.console.console_log("Cancelled.")
            return

        parent = target.parent
        parent.remove_child(target)
        if move_to_parent:
            self.current = parent
        self.console.console_log(f"Removed '{target.name}'.")

    def cmd_add(self, args: List[str]) -> None:
        if len(args) < 2:
            self.console.console_log("Usage: add <container|leaf> <type>")
            return

        kind, element_type = args[0], args[1].lower()

        if kind == "container":
            if element_type not in CONTAINER_TYPES:
                self.console.console_log(f"Unknown container type '{element_type}'. Available: {', '.join(CONTAINER_TYPES)}")
                return
            element = self._dialog_create_header()
        elif kind == "leaf":
            if element_type not in LEAF_TYPES:
                self.console.console_log(f"Unknown leaf type '{element_type}'. Available: {', '.join(LEAF_TYPES)}")
                return
            element = self._dialog_create_leaf(element_type)
        else:
            self.console.console_log("First argument must be 'container' or 'leaf'.")
            return

        if element is None:
            self.console.console_log("Cancelled.")
            return

        self.current.add_child(element)
        self.console.console_log(f"Added {element.describe()} (id={element.id}).")


    def _dialog_create_header(self) -> Optional[Header]:
        name = self.console.get_str("Name (used for cd/rm): ")
        if not name:
            return None
        text = self.console.get_str("Heading text: ")
        level_raw = self.console.get_str("Level [1-6, default 1]: ")
        level = int(level_raw) if level_raw.isdigit() else 1
        return Header(name, text, level)

    def _dialog_create_leaf(self, element_type: str) -> Optional[LeafElement]:
        name = self.console.get_str("Name (used for rm): ")
        if not name:
            return None

        if element_type == "text":
            text = self.console.get_str("Text: ")
            return PlainText(name, text)

        if element_type == "link":
            text = self.console.get_str("Link text: ")
            url = self.console.get_str("URL: ")
            return Link(name, text, url)

        if element_type == "image":
            alt = self.console.get_str("Alt text: ")
            src = self.console.get_str("Source: ")
            return Image(name, alt, src)

        if element_type == "paragraph":
            paragraph = Paragraph(name)
            self.console.console_log("Enter paragraph parts. Blank line to finish.")
            index = 0
            while True:
                line = self.console.get_str("Text (or blank to stop): ")
                if not line:
                    break
                index += 1
                paragraph.add_element(PlainText(f"{name}_text{index}", line))
                add_link = self.console.get_str("Add a link after this text? Y/N ")
                if add_link.lower() == "y":
                    link_text = self.console.get_str("Link text: ")
                    link_url = self.console.get_str("URL: ")
                    paragraph.add_element(Link(f"{name}_link{index}", link_text, link_url))
            return paragraph

        return None

