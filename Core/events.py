from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, List


class EventKind(Enum):
    ATTACKER_DEAD = auto()
    TARGET_DEAD = auto()
    DAMAGED = auto()
    KILLED = auto()
    REVIVED = auto()
    HEALED = auto()
    ABILITY_UNKNOWN = auto()
    EQUIPPED = auto()
    DROPPED = auto()
    LEARNED = auto()
    FORGOT = auto()


@dataclass(frozen=True)
class CharacterEvent:
    kind: EventKind
    actor: Any
    target: Any = None
    subject: Any = None
    amount: int = 0


Listener = Callable[[CharacterEvent], None]


class EventEmitter:

    def __init__(self):
        self._listeners: List[Listener] = []

    def subscribe(self, listener: Listener) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: Listener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def emit(self, event: CharacterEvent) -> None:
        for listener in list(self._listeners):
            listener(event)
