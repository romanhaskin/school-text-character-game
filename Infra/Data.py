import json
import os

from pathlib import Path
from typing import Protocol


class Serializable(Protocol):
    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict): ...


def default_data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / "text-character-game"


class DataManager:

    CHARACTERS_DIR = "characters"

    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir) if base_dir else default_data_dir()

    def _path(self, filename: str, subdir: str | None, create: bool = False) -> Path:
        name = str(filename).strip()
        if not name or name in (".", "..") or "/" in name or "\\" in name or "\0" in name:
            raise ValueError(f"invalid save name: {filename!r}")
        if not name.endswith(".json"):
            name += ".json"
        directory = self.base_dir / subdir if subdir else self.base_dir
        if create:
            directory.mkdir(parents=True, exist_ok=True)
        return directory / name

    def save_to_json(self, obj: Serializable, filename, subdir: str | None = None):
        filepath = self._path(filename, subdir, create=True)
        tmp = filepath.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj.to_dict(), f, indent=4, ensure_ascii=False)
        os.replace(tmp, filepath)

    def read_json(self, filename, subdir: str | None = None) -> dict:
        filepath = self._path(filename, subdir)
        if not filepath.exists():
            raise FileNotFoundError(f"Save file not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_from_json(self, target_class: type[Serializable], filename, subdir: str | None = None):
        return target_class.from_dict(self.read_json(filename, subdir))
