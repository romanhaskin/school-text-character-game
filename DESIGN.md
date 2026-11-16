# Project Structure Design

## Overview

A Python command-line application with two operating modes, selected at launch:

| Mode   | Command             | Purpose                                                        |
|--------|---------------------|----------------------------------------------------------------|
| `game` | `python main.py game` | Create characters, items and abilities; fight, heal, equip.  |
| `text` | `python main.py text` | Build and navigate a structured text document as a tree.     |

Both modes run inside the same interactive shell that provides saving,
loading, undo and HTTP fetching. If no mode is given, `main.py` prompts for one.

- in future, "text" will be removed from main version.

## Architectural Layers

```
            ┌────────────────────────────────────────────┐
 main.py →  │ CLI      shell loop, undo history, console │
            └───────────────┬────────────────────────────┘
                            │ depends on
            ┌───────────────▼────────────────────────────┐
            │ Infra    mode workers, persistence, web    │
            └───────────────┬────────────────────────────┘
                            │ depends on
            ┌───────────────▼────────────────────────────┐
            │ Core    domain models                      │
            └────────────────────────────────────────────┘
```

`Core` knows nothing about `Infra` or `CLI`.
Domain events (`Core/events.py`) let `Core` report what happened without
printing, so formatting stays in `Infra`.

Workers do not import `CLI.Presenter`. `main.py` creates the `Console`, passes
it to `shell`, and the shell injects it into the active worker (see Key Contracts).

## Components

### Entry point — `main.py`
- `parse_arguments(tokens)` splits argv into positional args and `-flag [value]` options.
- `main()` resolves the mode (`game` / `text`, re-prompting on invalid input),
  then builds `shell(worker_class, Console(), DataManager(), WebWorker(), mode)`
  and runs it. It is the composition root: all collaborators are created here.

### CLI layer
**`Commands.shell`** — the REPL.
- Owns the injected `Console` and hands it to the active worker via `_adopt`
  (on startup, after `load`, and after `undo`), so workers rebuilt through
  `from_dict` still get it.
- Reads a line, tokenises with `shlex`, resolves the command.
- *Meta commands* (mode-independent): `help`, `save`, `load`, `fetch`, `undo`.
  Stop words: `exit`, `quit`, `stop`.
- *Worker commands* come from `worker.COMMANDS` (a name → bound-method dict).
- `load` in game mode can import from the web (SuperHero API) or a local file;
  in text mode it loads locally only.

**`History`** — undo support.
- `Command` (ABC) → `WorkerCommand`: wraps a worker handler call.
- `Memento`: snapshot of a worker via `to_dict()`, restored via `from_dict()`.
- `WorkerCommand.execute()` snapshots before/after; the command is pushed onto
  `CommandHistory` only if state actually changed (`changed_state`).
- Loading a save clears the history.

**`Presenter.Console`** — thin I/O wrapper (`console_log`, `get_str`, `get_int`),
making output replaceable in tests. Used by `shell` and, through it, by workers.

### Core layer
**`character.py`**
- `Character`: name, HP, armor, attack power, inventory (`Item`s), abilities.
  Actions: `attack`, `heal`, `use_ability`, `equip_item`, `remove_item`,
  `learn_ability`, `forget_ability`. Derived stats include item bonuses.
- `Item`: stat bonuses (HP / armor / attack).
- `Ability`: typed (`attack` | `heal`) with power; delegates to a **Strategy**
  (`AbilityEffect` → `AttackEffect`, `HealEffect`) looked up in `EFFECTS`.
- All classes serialise via `to_dict` / `from_dict`.

**`events.py`**
- `EventKind` enum, immutable `CharacterEvent` dataclass, and `EventEmitter`
  (**Observer**: `subscribe` / `unsubscribe` / `emit`).
- `Character` emits events (damage, kill, heal, equip, …) instead of printing.

**`text.py`**
- **Composite**: `TextElement` → `LeafElement` (`PlainText`, `Link`, `Image`,
  `Paragraph`) and `ContainerElement` (`Header`, `Document`). Each element has
  an auto-incremented id (counter advanced on load to avoid collisions).
- **Visitor**: `ElementVisitor` with `TocVisitor` (table of contents) and
  `TreeLinesVisitor` (tree printout).
- **Builder**: `TextDocumentBuilder` / `ParagraphBuilder` for fluent construction.

### Infra layer
**`Data.DataManager`** — saves/loads any `Serializable` (protocol with
`to_dict` / `from_dict`) as JSON in `saves/`.

**`Display/characterWorker.CharacterShell`** — game-mode state
(`characters`, `items`, `abilities` keyed by id) and commands:
`create`, `add`, `act`, `ls`. Subscribes to each character's events and prints
them through `characterEvents.format_event` to `self.console`.

**`Display/textWorker.DocumentShell`** — text-mode state (a `Document` plus a
`current` container cursor) and filesystem-like commands:
`pwd`, `print`, `add`, `rm`, `up`, `cd`.

**`WebApi/`** — layered HTTP access:
`WebWorker.fetch_json(url)` → `WebCaller.get` (network, `WebCallerError`) →
`WebValidator` (status / empty / JSON errors, all `WebValidationError`).
`SuperheroImporter` maps powerstats to a character save dict
(HP = intelligence + combat + speed, armor = durability, attack = strength).

## Key Contracts

**Worker contract** — any class passed to `shell` must provide:
- `COMMANDS: dict[str, Callable[[list[str]], None]]`
- `to_dict() -> dict` and `@classmethod from_dict(data) -> Self`
- a constructor callable without arguments, with an optional `console` parameter
- a `console` attribute (`console_log`, `get_str`, `get_int`), assigned by the
  shell via `_adopt`; workers use `self.console` for all input and output

This single protocol powers save/load and undo for both modes, and is the
extension point for adding a new mode.

## Data Flow

```
user input ─► shell._read ─► shlex.split ─► _resolve(command)
                                   │
              meta command? ───────┤──► handler(args)
                                   │
              worker command ──────┴──► WorkerCommand.execute
                                         ├─ Memento(before)
                                         ├─ worker.cmd_*(args) ─► Core model
                                         │        └─ emits CharacterEvent ─► format_event ─► Console
                                         ├─ Memento(after)
                                         └─ push to CommandHistory if state changed
```

## Design Patterns

| Pattern   | Where                                             |
|-----------|---------------------------------------------------|
| Command   | `CLI/History.py` (`WorkerCommand`)                |
| Memento   | `CLI/History.py` (`Memento`)                      |
| Observer  | `Core/events.py` (`EventEmitter`)                 |
| Strategy  | `Core/character.py` (`AbilityEffect` subclasses)  |
| Composite | `Core/text.py` (element tree)                     |
| Visitor   | `Core/text.py` (`ElementVisitor`)                 |
| Builder   | `Core/text.py` (`TextDocumentBuilder`)            |
| Facade    | `Infra/WebApi/WebWorker.py`                       |
| Dependency injection | `main.py` → `shell`, `WebWorker`; `shell` → worker `console` |

