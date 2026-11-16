import pytest

import os
import sys


current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))

sys.path.insert(0, project_root)

from Core.character import Character, Item, Ability
from Infra.Display.characterWorker import CharacterShell


@pytest.fixture
def mock_console(mocker):
    return mocker.MagicMock()


@pytest.fixture
def shell(mock_console):
    return CharacterShell(mock_console)


@pytest.fixture
def populated(shell):
    tom = Character("tom", 100, 5, 20)
    jerry = Character("jerry", 50, 0, 10)
    stick = Item("stick", 0, 0, 5)
    smack = Ability("smack", "attack", 30)
    shell._register(shell.characters, tom)
    shell._register(shell.characters, jerry)
    shell._register(shell.items, stick)
    shell._register(shell.abilities, smack)
    return shell, tom, jerry, stick, smack


def logged(mock_console):
    return [c.args[0] for c in mock_console.console_log.call_args_list]


def test_helpers(populated):
    shell, tom, jerry, stick, smack = populated
    assert (tom.id, jerry.id, stick.id, smack.id) == (1, 2, 3, 4)

    assert shell._find(shell.characters, "1") is tom
    assert shell._find(shell.characters, "jerry") is jerry
    assert shell._find(shell.characters, "99") is None
    assert shell._find(shell.characters, "null") is None

    assert CharacterShell._option(["--id", "5"], "--id") == "5"
    assert CharacterShell._option(["--id"], "--id") is None
    assert CharacterShell._option([], "--id") is None

    tom.equip_item(stick)
    assert shell._users_of("item", stick) == ["tom"]
    assert shell._users_of("ability", smack) == []


def test_create(shell, mock_console):
    mock_console.get_str.side_effect = ["tom", "stick", "smack", "ATTACK"]
    mock_console.get_int.side_effect = [100, 5, 20, 1, 2, 3, 30]

    shell.cmd_create(["char"])
    shell.cmd_create(["item"])
    shell.cmd_create(["ability"])

    tom, stick, smack = shell.characters[1], shell.items[2], shell.abilities[3]
    assert (tom.name, tom.max_hp, tom.armor, tom.attack_power) == ("tom", 100, 5, 20)
    assert (stick.hp_bonus, stick.armor_bonus, stick.attack_bonus) == (1, 2, 3)
    assert (smack.type, smack.power) == ("attack", 30)
    assert logged(mock_console)[-1] == "Created ability 'smack' (id=3)."


def test_create_errors_and_cancel(shell, mock_console):
    shell.cmd_create([])
    shell.cmd_create(["wizard"])
    assert logged(mock_console) == ["Usage: create <char|item|ability>"] * 2

    mock_console.get_str.side_effect = ["", "", "", "spell", "bogus"]
    shell.cmd_create(["char"])
    shell.cmd_create(["item"])
    shell.cmd_create(["ability"])
    shell.cmd_create(["ability"])
    assert logged(mock_console)[2:].count("Cancelled.") == 4
    assert any("Unknown ability type 'bogus'" in m for m in logged(mock_console))
    assert not (shell.characters or shell.items or shell.abilities)


def test_add(populated, mock_console):
    shell, tom, jerry, stick, smack = populated

    shell.cmd_add(["--char_id", "tom", "--id", "stick"])
    assert tom.inventory == [stick]
    assert tom.attack_power == 25

    shell.cmd_add(["--char_id", "1", "--id", "4"])
    assert tom.abilities == [smack]


def test_add_errors(populated, mock_console):
    shell, tom, *_ = populated
    shell.cmd_add(["--char_id", "tom"])
    shell.cmd_add(["--char_id", "null", "--id", "stick"])
    shell.cmd_add(["--char_id", "tom", "--id", "null"])
    assert logged(mock_console) == [
        "Usage: add --char_id <id/name> --id <id/name>",
        "No character found for 'null'.",
        "No item or ability found for 'null'.",
    ]
    assert tom.inventory == [] and tom.abilities == []


def test_act(populated, mock_console):
    shell, tom, jerry, stick, smack = populated

    shell.cmd_act(["attack", "tom", "jerry"])
    assert jerry.health == 50 - 20

    tom.base_attack_power = 8
    jerry.health = 10
    shell.cmd_act(["heal", "tom", "jerry"])
    assert jerry.health == 18

    shell.cmd_act(["ability", "tom", "jerry", "--id", "smack"])
    assert jerry.health == 18
    tom.learn_ability(smack)
    shell.cmd_act(["ability", "tom", "jerry", "--id", "smack"])
    assert jerry.health == 0 and not jerry.isalive


def test_act_errors(populated, mock_console):
    shell, *_ = populated
    shell.cmd_act(["attack", "tom"])
    shell.cmd_act(["dance", "tom", "jerry"])
    shell.cmd_act(["attack", "null", "jerry"])
    shell.cmd_act(["attack", "tom", "null"])
    shell.cmd_act(["ability", "tom", "jerry"])
    shell.cmd_act(["ability", "tom", "jerry", "--id", "null"])
    assert logged(mock_console) == [
        "Usage: act <attack|heal|ability> <actor> <target> [--id <id/name>]",
        "Usage: act <attack|heal|ability> <actor> <target> [--id <id/name>]",
        "No character found for 'null'.",
        "No character found for 'null'.",
        "Usage: act ability <actor> <target> --id <id/name>",
        "No ability found for 'null'.",
    ]


def test_ls(populated, mock_console):
    shell, tom, jerry, stick, smack = populated
    tom.equip_item(stick)
    mock_console.reset_mock()

    shell.cmd_ls(["char"])
    shell.cmd_ls(["item"])
    shell.cmd_ls(["item", "--id", "stick"])
    shell.cmd_ls(["ability", "--id", "99"])
    shell.cmd_ls([])

    assert logged(mock_console) == [
        f"[1] {tom.describe()}",
        f"[2] {jerry.describe()}",
        f"[3] {stick.describe()} - used by: tom",
        stick.describe(),
        "  Used by: tom",
        "No ability found for '99'.",
        "Usage: ls <char|item|ability> [--id <id/name>]",
    ]


def test_ls_empty(shell, mock_console):
    shell.cmd_ls(["item"])
    mock_console.console_log.assert_called_once_with("No items yet.")


def test_serialization_roundtrip(populated):
    shell, tom, jerry, stick, smack = populated
    tom.equip_item(stick)
    tom.learn_ability(smack)

    restored = CharacterShell.from_dict(shell.to_dict())

    assert restored.to_dict() == shell.to_dict()
    r_tom = restored.characters[tom.id]
    assert r_tom.inventory[0] is restored.items[stick.id]
    assert r_tom.abilities[0] is restored.abilities[smack.id]
    assert next(restored._ids) == 5
