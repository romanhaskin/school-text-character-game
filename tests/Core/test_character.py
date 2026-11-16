import pytest

import os
import sys


current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))

sys.path.insert(0, project_root)

from Core.character import Character, Item, Ability  


from Core.events import EventKind


@pytest.fixture
def events(tom, jerry):
    recorded = []
    tom.events.subscribe(recorded.append)
    jerry.events.subscribe(recorded.append)
    return recorded


def kinds(events):
    return [e.kind for e in events]

@pytest.fixture
def tom():
    return Character(name="Tom", health=100, armor=5, attack_power=15)

@pytest.fixture
def jerry():
    return Character(name="Jerry", health=30, armor=2, attack_power=5)


def test_attack_and_death_state(tom, jerry, events):
    stick = Item(name="stick", attack_bonus=17)
    tom.equip_item(stick)
    
    tom.attack(jerry)
    
    assert jerry.health == 0
    assert jerry.isalive is False

    assert EventKind.KILLED in kinds(events)

    jerry.attack(tom)

    assert kinds(events)[-1] == EventKind.ATTACKER_DEAD


def test_damage_calculation(tom, jerry, events):

    tom.attack(jerry)

    assert jerry.health == 17
    assert jerry.isalive is True
    
    assert len(events) == 1
    assert events[0].kind == EventKind.DAMAGED
    assert (events[0].actor, events[0].target, events[0].amount) == (tom, jerry, 13)


def test_invalid_ability_type_raises_error():

    with pytest.raises(ValueError, match="Unknown ability type"):
        Ability(name="Punch", type="melle", power=30)


def test_armor_items(tom):

    shield = Item(name="gloves", armor_bonus=10)
    ring = Item(name="hat", armor_bonus=3)
    
    tom.equip_item(shield)
    tom.equip_item(ring)
    
    assert tom.armor == 18


def test_abilities(tom, jerry, events):
    heal = Ability("heal", "heal", 10)
    smack = Ability("smack", "attack", 32)

    tom.learn_ability(smack)
    tom.use_ability(smack, jerry)

    assert jerry.isalive is False

    tom.learn_ability(heal)
    tom.use_ability(heal, jerry)

    assert jerry.isalive is True

    tom.forget_ability(heal)
    tom.use_ability(heal, jerry)

    assert events[-1].kind == EventKind.ABILITY_UNKNOWN
    assert events[-1].subject is heal


def test_saves(tom):
    tom.id = 10
    tom.health = 10

    stick = Item(name="stick", attack_bonus=17)
    stick.id = 12
    tom.equip_item(stick)

    smack = Ability("smack", "attack", 32)
    tom.learn_ability(smack)

    saved_tom = tom.to_dict()

    restored_tom = Character.from_dict(saved_tom)

    assert restored_tom is not saved_tom

    assert restored_tom.id == 10
    assert restored_tom.health == 10

    assert restored_tom.inventory[0].id == 12
    assert restored_tom.inventory[0].name == "stick"

    assert restored_tom.abilities[0].name == "smack"

    assert restored_tom.to_dict() == saved_tom

def test_ability_use_dispatches_to_effect(tom, jerry):
    smack = Ability("smack", "attack", 20)
    heal = Ability("heal", "heal", 5)
    jerry.health = 10

    smack.use(tom, jerry)
    assert jerry.health == 0

    heal.use(tom, jerry)
    assert jerry.health == 5


def test_unknown_ability_type_rejected():
    with pytest.raises(ValueError):
        Ability("x", "fly", 1)


def test_events_cover_equip_drop_learn_forget_and_revive(tom, jerry, events):
    stick = Item("stick")
    smack = Ability("smack", "attack", 1)
    tom.equip_item(stick)
    tom.remove_item(stick)
    tom.learn_ability(smack)
    tom.forget_ability(smack)
    jerry.health = 0
    jerry.isalive = False
    tom.heal(jerry, 5)

    assert kinds(events) == [
        EventKind.EQUIPPED, EventKind.DROPPED, EventKind.LEARNED, EventKind.FORGOT,
        EventKind.REVIVED, EventKind.HEALED,
    ]
    assert events[-1].amount == 5


def test_unsubscribed_listener_gets_nothing(tom, jerry):
    recorded = []
    tom.events.subscribe(recorded.append)
    tom.events.unsubscribe(recorded.append)
    tom.attack(jerry)
    assert recorded == []
