from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional


class Command(ABC):

    @abstractmethod
    def execute(self) -> None:
        pass

    @abstractmethod
    def undo(self) -> None:
        pass


class Memento:

    def __init__(self, owner: Any):
        self._type = type(owner)
        self._state = owner.to_dict()

    @property
    def state(self) -> dict:
        return self._state

    def restore(self) -> Any:
        return self._type.from_dict(self._state)


class WorkerCommand(Command):

    def __init__(self, label: str, handler: Callable[[List[str]], None], args: List[str],
                 get_worker: Callable[[], Any], set_worker: Callable[[Any], None]):
        self.label = label
        self._handler = handler
        self._args = args
        self._get_worker = get_worker
        self._set_worker = set_worker
        self._before: Optional[Memento] = None
        self._after: Optional[Memento] = None

    def execute(self) -> None:
        self._before = Memento(self._get_worker())
        self._handler(self._args)
        self._after = Memento(self._get_worker())

    @property
    def changed_state(self) -> bool:
        return self._before.state != self._after.state

    def undo(self) -> None:
        self._set_worker(self._before.restore())


class CommandHistory:

    def __init__(self):
        self._stack: List[Command] = []

    def push(self, command: Command) -> None:
        self._stack.append(command)

    def pop(self) -> Optional[Command]:
        return self._stack.pop() if self._stack else None

    def clear(self) -> None:
        self._stack.clear()

    def __len__(self) -> int:
        return len(self._stack)
