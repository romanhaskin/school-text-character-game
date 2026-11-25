import json
import shlex

from CLI.History import CommandHistory, WorkerCommand
from Infra.WebApi.SuperheroImporter import SuperheroImporter
from Infra.WebApi.WebCaller import WebCallerError

_FETCH_FAILED = object()
_STOP_WORDS = ("exit", "quit", "stop")


class _Snapshot:
    def __init__(self, data: dict):
        self._data = data

    def to_dict(self) -> dict:
        return self._data


class shell:
    def __init__(self, working_class, working_console, data_manager, webAPI, mode=None):
        self.console = working_console
        self.worker = self._adopt(working_class())
        self.data = data_manager
        self.web = webAPI
        self.mode = mode
        self.meta_commands = {
            "help": self._help,
            "save": self._save,
            "load": self._load,
            "fetch": self._fetch,
            "undo": self._undo,
            "history": self._history,
            "savechar": self._save_char,
            "loadchar": self._load_char,
        }
        self.history = CommandHistory()

    def _adopt(self, worker):
        worker.console = self.console
        return worker

    def _read(self):
        try:
            return self.console.get_str("> ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

    def _prompt(self, message: str):
        self.console.console_log(message)
        return self._read()

    def _help(self, args: list[str]) -> None:
        for name in self.worker.COMMANDS:
            self.console.console_log(name)

    def to_dict(self) -> dict:
        return {
            "shell": {"history": self.history.labels()},
            "worker": self.worker.to_dict(),
        }

    def load_dict(self, data: dict) -> None:
        shell_data = data.get("shell") if isinstance(data.get("shell"), dict) else {}
        worker_data = data["worker"] if "worker" in data else data
        self.worker = self._adopt(type(self.worker).from_dict(worker_data))
        history = shell_data.get("history", [])
        self.history.load_labels(history if isinstance(history, list) else [])

    def _save(self, args: list[str]) -> None:
        save_name = self.console.get_str("enter save name: ")
        try:
            self.data.save_to_json(self, save_name)
        except Exception as e:
            self.console.console_log(f"an error occured during saving, save failed: {e}")
            return
        self.console.console_log(f"saved {save_name}")

    def _load_local(self) -> None:
        save_name = self.console.get_str("enter save name: ")
        try:
            self.load_dict(self.data.read_json(save_name))
        except Exception as e:
            self.console.console_log(f"an error occured during loading, load failed: {e}")
            return
        self.console.console_log(f"loaded {save_name}")

    def _load_web(self) -> None:
        token = self._prompt("please incert token: ")
        if not token:
            self.console.console_log("please enter valid argument")
            return

        hero_id = self._prompt("please incert id: ")
        if not hero_id:
            self.console.console_log("please enter valid id")
            return

        answer = self._fetch_json(SuperheroImporter.build_url(token, hero_id))
        if answer is _FETCH_FAILED:
            return

        try:
            data = SuperheroImporter.to_save_data(answer)
            self.worker = self._adopt(self.worker.from_dict(data))
            self.history.clear()
        except ValueError as e:
            self.console.console_log(f"web load failed: {e}")
            return
        self.console.console_log(f"loaded {answer['name']} from web")

    def _save_char(self, args: list[str]) -> None:
        if not args or not hasattr(self.worker, "export_character"):
            self.console.console_log("Usage: savechar <id/name> [file name]")
            return
        character = self.worker._find(self.worker.characters, args[0])
        if character is None:
            self.console.console_log(f"No character found for '{args[0]}'.")
            return
        file_name = args[1] if len(args) > 1 else character.name
        try:
            self.data.save_to_json(_Snapshot(self.worker.export_character(character)),
                                   file_name, self.data.CHARACTERS_DIR)
        except Exception as e:
            self.console.console_log(f"an error occured during saving, save failed: {e}")
            return
        self.console.console_log(f"saved character '{character.name}' as {file_name}")

    def _import_char(self, args: list[str]) -> None:
        try:
            data = self.data.read_json(args[0], self.data.CHARACTERS_DIR)
            character = self.worker.import_character(data)
        except Exception as e:
            self.console.console_log(f"an error occured during loading, load failed: {e}")
            return
        self.console.console_log(f"loaded character '{character.name}' (id={character.id})")

    def _load_char(self, args: list[str]) -> None:
        if not args or not hasattr(self.worker, "import_character"):
            self.console.console_log("Usage: loadchar <file name>")
            return
        self._execute_worker_command("loadchar " + " ".join(args), self._import_char, args)

    def _load(self, args: list[str]) -> None:
        if self.mode != "game":
            self._load_local()
            return

        source = self._prompt("load from web or local?: ")
        if source == "web":
            self._load_web()
        elif source == "local":
            self._load_local()
        else:
            self.console.console_log("please enter valid argument")

    def _set_worker(self, worker) -> None:
        self.worker = self._adopt(worker)

    def _undo(self, args: list[str]) -> None:
        command = self.history.pop()
        if command is None:
            self.console.console_log("nothing to undo")
            return
        command.undo()
        self.console.console_log(f"undone: {command.label}")

    def _history(self, args: list[str]) -> None:
        labels = self.history.labels()
        if not labels:
            self.console.console_log("history is empty")
            return
        for number, label in enumerate(labels, 1):
            self.console.console_log(f"{number}. {label}")

    def _execute_worker_command(self, line: str, handler, args: list[str]) -> None:
        command = WorkerCommand(line, handler, args, lambda: self.worker, self._set_worker)
        command.execute()
        if command.changed_state:
            self.history.push(command)

    def _fetch_json(self, url: str):
        try:
            return self.web.fetch_json(url)
        except (WebCallerError, ValueError) as e:
            self.console.console_log(f"fetch failed: {e}")
            return _FETCH_FAILED

    def _fetch(self, args: list[str]) -> None:
        if not args:
            self.console.console_log("Usage: fetch <url>")
            return
        data = self._fetch_json(args[0])
        if data is _FETCH_FAILED:
            return
        self.console.console_log(json.dumps(data, indent=2, ensure_ascii=False))

    def _resolve(self, command: str):
        return self.meta_commands.get(command) or self.worker.COMMANDS.get(command)

    def run(self) -> None:
        while True:
            line = self._read()

            if line is None or line in _STOP_WORDS:
                break

            if not line:
                self.console.console_log("please enter something")
                continue

            try:
                command, *args = shlex.split(line)
            except ValueError as e:
                self.console.console_log(f"parse error {e}")
                continue

            handler = self._resolve(command)
            if handler is None:
                self.console.console_log(f"Unknown command: {command}")
                continue

            if command in self.meta_commands:
                handler(args)
            else:
                self._execute_worker_command(line, handler, args)
