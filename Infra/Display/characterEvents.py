from Core.events import CharacterEvent, EventKind

_FORMATTERS = {
    EventKind.ATTACKER_DEAD: lambda e: f"{e.actor.name} cant attack, {e.actor.name} is dead",
    EventKind.TARGET_DEAD: lambda e: f"{e.target.name} is already dead",
    EventKind.DAMAGED: lambda e: f"{e.target.name} takes {e.amount} damage. ({e.target.name} HP: {e.target.health})",
    EventKind.KILLED: lambda e: f"{e.target.name} has been killed by {e.actor.name}",
    EventKind.REVIVED: lambda e: f"{e.target.name} is back from the dead!",
    EventKind.HEALED: lambda e: f"{e.actor.name} healed {e.target.name} for {e.amount} HP. ({e.target.name} HP: {e.target.health})",
    EventKind.ABILITY_UNKNOWN: lambda e: f"{e.actor.name} doesn't know the ability [{e.subject.name}].",
    EventKind.EQUIPPED: lambda e: f"{e.actor.name} equipped [{e.subject.name}].",
    EventKind.DROPPED: lambda e: f"{e.actor.name} dropped [{e.subject.name}].",
    EventKind.LEARNED: lambda e: f"{e.actor.name} learned [{e.subject.name}].",
    EventKind.FORGOT: lambda e: f"{e.actor.name} forgot [{e.subject.name}].",
}


def format_event(event: CharacterEvent) -> str:
    return _FORMATTERS[event.kind](event)
