from Core.character import *
import itertools
from typing import Dict, List, Optional
from Core.events import CharacterEvent
from Infra.Display.characterEvents import format_event


class CharacterShell:

    def __init__(self, console=None):
        self.console = console
        self.save_name = "char"
        self.characters: Dict[int, Character] = {}
        self.items: Dict[int, Item] = {}
        self.abilities: Dict[int, Ability] = {}
        self._ids = itertools.count(1)

        self.COMMANDS = {
                    "create": self.cmd_create,
                    "add": self.cmd_add,
                    "act": self.cmd_act,
                    "ls": self.cmd_ls,
        }
    @staticmethod
    def _find(store: Dict[int, object], id_or_name: str):
        try:
            return store.get(int(id_or_name))
        except ValueError:
            for obj in store.values():
                if obj.name == id_or_name:
                    return obj
        return None
    
    @staticmethod
    def _option(args: List[str], flag: str) -> Optional[str]:
        if flag in args:
            idx = args.index(flag)
            if idx + 1 < len(args):
                return args[idx + 1]
        return None

    def _on_event(self, event: CharacterEvent) -> None:
        self.console.console_log(format_event(event))

    def _observe(self, character: Character) -> None:
        character.events.subscribe(self._on_event)

    def _register(self, store: Dict[int, object], obj) -> int:
        obj_id = next(self._ids)
        obj.id = obj_id
        store[obj_id] = obj
        if isinstance(obj, Character):
            self._observe(obj)
        return obj_id

    def _users_of(self, type: str, obj) -> List[str]:
        collection_name = "inventory" if type == "item" else "abilities"
        return [c.name for c in self.characters.values() if obj in getattr(c, collection_name)]

    def to_dict(self) -> dict:
        return {
            "characters": [c.to_dict() for c in self.characters.values()],
            "items": [i.to_dict() for i in self.items.values()],
            "abilities": [a.to_dict() for a in self.abilities.values()],
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CharacterShell':

        shell = cls()
        for item_data in data["items"]:
            item = Item.from_dict(item_data)
            shell.items[item.id] = item
        for ability_data in data["abilities"]:
            ability = Ability.from_dict(ability_data)
            shell.abilities[ability.id] = ability
        for character_data in data["characters"]:
            character = Character.from_dict(character_data)
            character.inventory = [shell.items.get(i.id, i) for i in character.inventory]
            character.abilities = [shell.abilities.get(a.id, a) for a in character.abilities]
            shell._observe(character)
            shell.characters[character.id] = character

        all_ids = [*shell.characters, *shell.items, *shell.abilities]
        shell._ids = itertools.count(max(all_ids, default=0) + 1)
        return shell


    def _dialog_create_char(self) -> Optional[Character]:
        name = self.console.get_str("Name: ")
        if not name:
            return None
        health = self.console.get_int("Health: ")
        armor = self.console.get_int("Armor: ")
        attack_power = self.console.get_int("Attack power: ")
        return Character(name, health, armor, attack_power)

    def _dialog_create_item(self) -> Optional[Item]:
        name = self.console.get_str("Name: ")
        if not name:
            return None
        hp_bonus = self.console.get_int("HP bonus: ")
        armor_bonus = self.console.get_int("Armor bonus: ")
        attack_bonus = self.console.get_int("Attack bonus: ")
        return Item(name, hp_bonus, armor_bonus, attack_bonus)

    def _dialog_create_ability(self) -> Optional[Ability]:
        name = self.console.get_str("Name: ")
        if not name:
            return None
        type = self.console.get_str(f"Kind [{'/'.join(Ability.TYPE)}]: ").lower()
        if type not in Ability.TYPE:
            self.console.console_log(f"Unknown ability type '{type}'. Available: {', '.join(Ability.TYPE)}")
            return None
        power = self.console.get_int("Power: ")
        return Ability(name, type, power)


    def cmd_create(self, args: List[str]) -> None:
        if not args or args[0] not in ("char", "item", "ability"):
            self.console.console_log("Usage: create <char|item|ability>")
            return

        type = args[0]
        if type == "char":
            obj, store = self._dialog_create_char(), self.characters
        elif type == "item":
            obj, store = self._dialog_create_item(), self.items
        else:
            obj, store = self._dialog_create_ability(), self.abilities

        if obj is None:
            self.console.console_log("Cancelled.")
            return

        obj_id = self._register(store, obj)
        self.console.console_log(f"Created {type} '{obj.name}' (id={obj_id}).")

    def cmd_add(self, args: List[str]) -> None:
        char_id = self._option(args, "--char_id")
        obj_id = self._option(args, "--id")
        if not char_id or not obj_id:
            self.console.console_log("Usage: add --char_id <id/name> --id <id/name>")
            return

        character = self._find(self.characters, char_id)
        if character is None:
            self.console.console_log(f"No character found for '{char_id}'.")
            return

        item = self._find(self.items, obj_id)
        if item is not None:
            character.equip_item(item)
            return

        ability = self._find(self.abilities, obj_id)
        if ability is not None:
            character.learn_ability(ability)
            return

        self.console.console_log(f"No item or ability found for '{obj_id}'.")

    def cmd_act(self, args: List[str]) -> None:
        if len(args) < 3 or args[0] not in ("attack", "heal", "ability"):
            self.console.console_log("Usage: act <attack|heal|ability> <actor> <target> [--id <id/name>]")
            return

        action, actor_id, target_id = args[0], args[1], args[2]

        actor = self._find(self.characters, actor_id)
        if actor is None:
            self.console.console_log(f"No character found for '{actor_id}'.")
            return

        target = self._find(self.characters, target_id)
        if target is None:
            self.console.console_log(f"No character found for '{target_id}'.")
            return

        if action == "attack":
            actor.attack(target)
        elif action == "heal":
            actor.heal(target, actor.attack_power)
        else:
            ability_id = self._option(args, "--id")
            if not ability_id:
                self.console.console_log("Usage: act ability <actor> <target> --id <id/name>")
                return
            ability = self._find(self.abilities, ability_id)
            if ability is None:
                self.console.console_log(f"No ability found for '{ability_id}'.")
                return
            actor.use_ability(ability, target)

    def cmd_ls(self, args: List[str]) -> None:
        stores = {"char": self.characters, "item": self.items, "ability": self.abilities}
        if not args or args[0] not in stores:
            self.console.console_log("Usage: ls <char|item|ability> [--id <id/name>]")
            return

        type = args[0]
        store = stores[type]
        obj_id = self._option(args, "--id")

        if obj_id:
            obj = self._find(store, obj_id)
            if obj is None:
                self.console.console_log(f"No {type} found for '{obj_id}'.")
                return
            self.console.console_log(obj.describe())
            if type != "char":
                self.console.console_log("  Used by: " + (", ".join(self._users_of(type, obj)) or "none"))
            return

        if not store:
            self.console.console_log(f"No {type}s yet.")
            return

        for obj in store.values():
            if type == "char":
                self.console.console_log(f"[{obj.id}] {obj.describe()}")
            else:
                users = self._users_of(type, obj)
                self.console.console_log(f"[{obj.id}] {obj.describe()} - used by: {', '.join(users) or 'none'}")
