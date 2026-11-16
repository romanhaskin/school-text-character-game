import json

from pathlib import Path
from typing import Protocol


class Serializable(Protocol):
    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict): ...


class DataManager:

    SAVES_DIR = Path(__file__).resolve().parent.parent / "saves"

    @classmethod
    def save_to_json(cls, obj: Serializable, filename):
        cls.SAVES_DIR.mkdir(parents=True, exist_ok=True)

        filepath = cls.SAVES_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(obj.to_dict(), f, indent=4, ensure_ascii=False)

    @classmethod
    def load_from_json(cls, target_class: type[Serializable], filename):

        filepath = cls.SAVES_DIR / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Save file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            return target_class.from_dict(json.load(f))
