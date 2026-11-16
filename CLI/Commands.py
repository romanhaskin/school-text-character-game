import json
import shlex

from CLI.History import CommandHistory, WorkerCommand
from Infra.WebApi.SuperheroImporter import SuperheroImporter
from Infra.WebApi.WebCaller import WebCallerError

_FETCH_FAILED = object()
_STOP_WORDS = ("exit", "quit", "stop")


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

    def _save(self, args: list[str]) -> None:
        save_name = self.console.get_str("enter save name: ")
        try:
            self.data.save_to_json(self.worker, save_name)
        except Exception as e:
            self.console.console_log(f"an error occured during saving, save failed: {e}")
            return
        self.console.console_log(f"saved {save_name}")

    def _load_local(self) -> None:
        save_name = self.console.get_str("enter save name: ")
        try:
            self.worker = self._adopt(self.data.load_from_json(type(self.worker), save_name))
            self.history.clear()
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
