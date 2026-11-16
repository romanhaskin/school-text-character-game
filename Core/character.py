from abc import ABC, abstractmethod
from typing import List, Optional
from Core.events import CharacterEvent, EventEmitter, EventKind


"""base character class"""

class Item:
    """Base item class"""
    def __init__(self, name: str, hp_bonus: int = 0, armor_bonus: int = 0, attack_bonus: int = 0):
        self.name = name
        self.hp_bonus = hp_bonus
        self.armor_bonus = armor_bonus
        self.attack_bonus = attack_bonus
        self.id: Optional[int] = None

    def describe(self) -> str:
        return (f"Item '{self.name}' (+{self.hp_bonus} HP, "
                f"+{self.armor_bonus} armor, +{self.attack_bonus} attack)")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "hp_bonus": self.hp_bonus,
            "armor_bonus": self.armor_bonus,
            "attack_bonus": self.attack_bonus,
            "id": self.id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Item':
        item = cls(data["name"], data["hp_bonus"], data["armor_bonus"], data["attack_bonus"])
        item.id = data["id"]
        return item


class AbilityEffect(ABC):

    @abstractmethod
    def apply(self, user: 'Character', target: 'Character', power: int) -> None:
        pass


class AttackEffect(AbilityEffect):

    def apply(self, user: 'Character', target: 'Character', power: int) -> None:
        user.attack(target, power=power)


class HealEffect(AbilityEffect):

    def apply(self, user: 'Character', target: 'Character', power: int) -> None:
        user.heal(target, power)


EFFECTS = {"attack": AttackEffect(), "heal": HealEffect()}


class Ability:
    """Base ability class"""

    TYPE = tuple(EFFECTS)

    def __init__(self, name: str, type: str, power: int = 0):
        if type not in self.TYPE:
            raise ValueError(f"Unknown ability type '{type}'. Available: {', '.join(self.TYPE)}")
        self.name = name
        self.type = type
        self.power = power
        self.id: Optional[int] = None

    def use(self, user: 'Character', target: 'Character') -> None:
        EFFECTS[self.type].apply(user, target, self.power)

    def describe(self) -> str:
        return f"Ability '{self.name}' ({self.type}, power {self.power})"

    def to_dict(self) -> dict:
        return {"name": self.name, "type": self.type, "power": self.power, "id": self.id}

    @classmethod
    def from_dict(cls, data: dict) -> 'Ability':
        ability = cls(data["name"], data["type"], data["power"])
        ability.id = data["id"]
        return ability


class Character:
    """Main character class"""
    def __init__(self, name: str, health: int, armor: int, attack_power: int):

        self.name = name
        self.id: Optional[int] = None

        self.max_hp = health
        self._hp = health

        self.base_armor = armor
        self.base_attack_power = attack_power

        self.inventory: List[Item] = []
        self.abilities: List[Ability] = []
        self.isalive = True
        self.events = EventEmitter()

    def _emit(self, kind: EventKind, target=None, subject=None, amount: int = 0) -> None:
        self.events.emit(CharacterEvent(kind, self, target, subject, amount))

    @property
    def max_health(self) -> int:
        return self.max_hp + sum(item.hp_bonus for item in self.inventory)

    @property
    def health(self) -> int:
        return self._hp

    @health.setter
    def health(self, value: int):
        self._hp = max(0, min(value, self.max_health))

    @property
    def armor(self) -> int:
        bonus = sum(item.armor_bonus for item in self.inventory)
        return self.base_armor + bonus

    @property
    def attack_power(self) -> int:
        bonus = sum(item.attack_bonus for item in self.inventory)
        return self.base_attack_power + bonus

    """character abilities"""

    def attack(self, target: 'Character', power: Optional[int] = None) -> None:
        if not self.isalive:
            self._emit(EventKind.ATTACKER_DEAD)
            return

        if not target.isalive:
            self._emit(EventKind.TARGET_DEAD, target)
            return

        attack_power = self.attack_power if power is None else power
        damage = max(0, attack_power - target.armor)

        target.health -= damage
        if target.health > 0:
            self._emit(EventKind.DAMAGED, target, amount=damage)
            return

        target.isalive = False
        target.health = 0
        self._emit(EventKind.KILLED, target)

    def heal(self, target: 'Character', amount: int) -> None:
        old_hp = target.health

        if old_hp == 0:
            target.isalive = True
            self._emit(EventKind.REVIVED, target)

        target.health += amount
        self._emit(EventKind.HEALED, target, amount=target.health - old_hp)

    def use_ability(self, ability: Ability, target: 'Character') -> None:
        if ability not in self.abilities:
            self._emit(EventKind.ABILITY_UNKNOWN, subject=ability)
            return

        ability.use(self, target)

    def equip_item(self, item: Item) -> None:
        self.inventory.append(item)
        self._emit(EventKind.EQUIPPED, subject=item)

    def remove_item(self, item: Item) -> None:
        self.inventory.remove(item)
        self._emit(EventKind.DROPPED, subject=item)

    def learn_ability(self, ability: Ability) -> None:
        self.abilities.append(ability)
        self._emit(EventKind.LEARNED, subject=ability)

    def forget_ability(self, ability: Ability) -> None:
        self.abilities.remove(ability)
        self._emit(EventKind.FORGOT, subject=ability)

    def describe(self) -> str:
        status = "alive" if self.isalive else "dead"
        return (f"Character '{self.name}' [{status}] HP: {self.health}/"
                f"{self.max_health}, "
                f"armor: {self.armor}, attack power: {self.attack_power}")

    def describe_bonuses(self) -> str:
        lines = [self.describe()]
        lines.append("  Items: " + (", ".join(i.name for i in self.inventory) or "none"))
        lines.append("  Abilities: " + (", ".join(a.name for a in self.abilities) or "none"))
        return "\n".join(lines)


    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "id": self.id,
            "max_hp": self.max_hp,
            "hp": self._hp,
            "base_armor": self.base_armor,
            "base_attack_power": self.base_attack_power,
            "isalive": self.isalive,
            "inventory": [item.to_dict() for item in self.inventory],
            "abilities": [ability.to_dict() for ability in self.abilities],
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Character':

        character = cls(
            data["name"],
            health=data["max_hp"],
            armor=data["base_armor"],
            attack_power=data["base_attack_power"],
        )
        character.inventory = [Item.from_dict(d) for d in data["inventory"]]
        character.abilities = [Ability.from_dict(d) for d in data["abilities"]]
        character.id = data["id"]
        character.isalive = data["isalive"]
        character._hp = data["hp"]
        return character
