import os
import sys

import pytest

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "../..")))

from CLI.Commands import shell
from Infra.WebApi.SuperheroImporter import SuperheroImporter
from Infra.WebApi.WebCaller import WebCallerError
from Infra.WebApi.WebValidator import HttpStatusError


class FakeWorker:
    def __init__(self):
        self.calls = []
        self.COMMANDS = {"echo": lambda args: self.calls.append(args), "noop": lambda args: None}

    def to_dict(self):
        return {"calls": [list(c) for c in self.calls]}

    @classmethod
    def from_dict(cls, data):
        worker = cls()
        worker.calls = [list(c) for c in data["calls"]]
        return worker


@pytest.fixture
def console(mocker):
    return mocker.MagicMock()

@pytest.fixture
def data(mocker):
    return mocker.MagicMock()

@pytest.fixture
def web(mocker):
    return mocker.MagicMock()

def run(console, *lines, data=None, web=None, mode=None):
    console.get_str.side_effect = list(lines) + ["exit"]
    cli = shell(FakeWorker, console, data, web, mode)
    cli.run()
    return cli


def logged(console):
    return [c.args[0] for c in console.console_log.call_args_list]


def test_dispatch_help_and_errors(console):
    cli = run(console, "echo a 'b c'", "help", "nope", "", "   ")
    assert cli.worker.calls == [["a", "b c"]]
    assert logged(console) == ["echo", "noop", "Unknown command: nope", "please enter something", "please enter something"]


def test_parse_error_is_reported_and_loop_continues(console):
    cli = run(console, "echo 'unclosed", "echo ok")
    assert logged(console)[0].startswith("parse error")
    assert cli.worker.calls == [["ok"]]


def test_stop_on_eof(console):
    console.get_str.side_effect = EOFError
    shell(FakeWorker, console, data, web).run()


def test_save_and_load(console, data):
    worker = FakeWorker()
    console.get_str.side_effect = ["save", "slot", "load", "slot", "exit"]
    cli = shell(FakeWorker, console, data, web)
    cli.worker = worker
    cli.run()
    data.save_to_json.assert_called_once_with(cli, "slot")
    data.read_json.assert_called_once_with("slot")
    assert isinstance(cli.worker, FakeWorker) and cli.worker is not worker
    assert logged(console) == ["saved slot", "loaded slot"]


def test_save_load_failures_are_reported(console, data):
    data.save_to_json.side_effect = OSError("disk")
    data.read_json.side_effect = OSError("missing")
    cli = run(console, "save", "slot", "load", "slot", data=data)
    assert isinstance(cli.worker, FakeWorker)
    assert [m for m in logged(console) if "failed" in m] == [
        "an error occured during saving, save failed: disk",
        "an error occured during loading, load failed: missing",
    ]


def test_fetch(console, web):
    web.fetch_json.return_value = {"a": 1}
    run_web(console, web, "fetch http://x", "fetch")
    web.fetch_json.assert_called_once_with("http://x")
    assert logged(console) == ['{\n  "a": 1\n}', "Usage: fetch <url>"]


def test_fetch_failure_is_reported(console, web):
    web.fetch_json.side_effect = ValueError("bad")
    run_web(console, web, "fetch http://x")
    assert logged(console) == ["fetch failed: bad"]


def test_fetch_caller_error_is_reported(console, web):
    web.fetch_json.side_effect = WebCallerError("down")
    run_web(console, web, "fetch http://x")
    assert logged(console) == ["fetch failed: down"]


def test_load_from_web_ignored_outside_game_mode(console, web, data):
    run(console, "load", "slot", data=data, web=web, mode="text")
    web.fetch_json.assert_not_called()
    data.read_json.assert_called_once_with("slot")
    assert logged(console) == ["loaded slot"]


def test_load_asks_web_or_local_in_game_mode(console, web, data):
    run(console, "load", "local", "slot", data=data, web=web, mode="game")
    web.fetch_json.assert_not_called()
    assert logged(console) == ["load from web or local?: ", "loaded slot"]


def test_load_from_web_failure_is_reported(console, web):
    web.fetch_json.side_effect = HttpStatusError(404, "http://x")
    run_web(console, web, "load", "web", "tok", "1")
    assert "fetch failed: GET http://x returned http status 404" in logged(console)


A_BOMB = {"response": "success", "id": "1", "name": "A-Bomb", "intelligence": "38",
          "strength": "100", "speed": "17", "durability": "80", "power": "24", "combat": "64"}


def test_prepare_load_maps_stats(console):
    data = SuperheroImporter.to_save_data(A_BOMB)
    assert data["items"] == [] and data["abilities"] == []
    char = data["characters"][0]
    assert (char["name"], char["base_attack_power"], char["base_armor"]) == ("A-Bomb", 100, 80)
    assert char["max_hp"] == char["hp"] == 38 + 64 + 17


@pytest.mark.parametrize("answer", [
    {"response": "error", "error": "bad"},
    {**A_BOMB, "strength": "null"},
    {k: v for k, v in A_BOMB.items() if k != "combat"},
    [],
])
def test_prepare_load_rejects_bad_response(console, answer):
    with pytest.raises(ValueError):
        SuperheroImporter.to_save_data(answer)


def test_load_from_web_replaces_worker(console, web):
    from Infra.Display.characterWorker import CharacterShell
    web.fetch_json.return_value = A_BOMB
    console.get_str.side_effect = ["load", "web", "tok", "1", "exit"]
    cli = shell(CharacterShell, console, None, web, "game")
    cli.run()
    char = cli.worker.characters[1]
    assert (char.name, char.max_hp, char.base_armor, char.base_attack_power) == ("A-Bomb", 119, 80, 100)
    web.fetch_json.assert_called_once_with("https://superheroapi.com/api/tok/1/powerstats")
    assert logged(console)[-1] == "loaded A-Bomb from web"


def test_load_from_web_api_error_is_reported(console, web):
    web.fetch_json.return_value = {"response": "error", "error": "invalid token"}
    run_web(console, web, "load", "web", "tok", "1")
    assert logged(console)[-1] == "web load failed: invalid token"


def run_web(console, web, *lines):
    console.get_str.side_effect = list(lines) + ["exit"]
    shell(FakeWorker, console, None, web, "game").run()


def test_undo_reverts_last_state_changing_command(console):
    cli = run(console, "echo a", "echo b", "undo")
    assert cli.worker.calls == [["a"]]
    assert logged(console) == ["undone: echo b"]


def test_undo_walks_back_through_history(console):
    cli = run(console, "echo a", "echo b", "undo", "undo")
    assert cli.worker.calls == []
    assert len(cli.history) == 0


def test_undo_with_empty_history(console):
    run(console, "undo")
    assert logged(console) == ["nothing to undo"]


def test_commands_that_change_nothing_are_not_recorded(console):
    cli = run(console, "noop", "undo")
    assert len(cli.history) == 0
    assert logged(console) == ["nothing to undo"]


def test_undo_itself_is_not_recorded(console):
    cli = run(console, "echo a", "undo", "undo")
    assert logged(console) == ["undone: echo a", "nothing to undo"]


def test_loading_keeps_saved_history_read_only(console, data):
    data.read_json.return_value = {"shell": {"history": ["echo x", "echo y"], "future_key": 1},
                                   "worker": {"calls": []}}
    cli = run(console, "echo a", "load", "slot", "history", "undo", data=data)
    assert logged(console) == ["loaded slot", "1. echo x", "2. echo y", "nothing to undo"]


def test_load_legacy_bare_worker_save(console, data):
    data.read_json.return_value = {"calls": [["a"]]}
    cli = run(console, "load", "slot", "history", data=data)
    assert cli.worker.calls == [["a"]]
    assert logged(console) == ["loaded slot", "history is empty"]


def test_shell_to_dict_contains_history_and_worker(console):
    cli = run(console, "echo a")
    assert cli.to_dict() == {"shell": {"history": ["echo a"]}, "worker": {"calls": [["a"]]}}


def test_undo_restores_real_character_shell(console):
    from Core.character import Character
    from Infra.Display.characterWorker import CharacterShell
    cli = shell(CharacterShell, console, None, None, "game")
    cli.worker._register(cli.worker.characters, Character("tom", 10, 0, 1))
    console.get_str.side_effect = ["act attack tom tom", "undo", "exit"]

    cli.run()

    assert cli.worker.characters[1].health == 10
    assert logged(console)[-1] == "undone: act attack tom tom"
    assert any("takes" in m for m in logged(console))


def test_history_lists_state_changing_steps_in_order(console):
    run(console, "echo a", "noop", "echo b", "history")
    assert logged(console) == ["1. echo a", "2. echo b"]


def test_history_drops_undone_steps(console):
    run(console, "echo a", "echo b", "undo", "history")
    assert logged(console) == ["undone: echo b", "1. echo a"]


def test_history_empty(console):
    run(console, "history")
    assert logged(console) == ["history is empty"]


def test_savechar_and_loadchar_round_trip(console, tmp_path):
    from Core.character import Character, Item
    from Infra.Data import DataManager
    from Infra.Display.characterWorker import CharacterShell
    dm = DataManager(tmp_path)

    first = shell(CharacterShell, console, dm, None, "game")
    hero = Character("hero", 10, 0, 1)
    first.worker._register(first.worker.characters, hero)
    sword = Item("sword", attack_bonus=2)
    first.worker._register(first.worker.items, sword)
    hero.inventory.append(sword)
    console.get_str.side_effect = ["savechar hero", "exit"]
    first.run()
    assert (tmp_path / "characters" / "hero.json").exists()

    second = shell(CharacterShell, console, dm, None, "game")
    console.get_str.side_effect = ["loadchar hero", "history", "undo", "exit"]
    second.run()
    assert second.worker.characters == {}
    assert "1. loadchar hero" in logged(console)
