import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from Infra.Data import DataManager


class Box:
    def __init__(self, d): self.d = d
    def to_dict(self): return self.d


def test_round_trip_in_subdir(tmp_path):
    dm = DataManager(tmp_path)
    dm.save_to_json(Box({"a": 1}), "hero", DataManager.CHARACTERS_DIR)
    assert (tmp_path / "characters" / "hero.json").exists()
    assert dm.read_json("hero", DataManager.CHARACTERS_DIR) == {"a": 1}


@pytest.mark.parametrize("name", ["", "..", "../x", "a/b"])
def test_invalid_names_rejected(tmp_path, name):
    with pytest.raises(ValueError):
        DataManager(tmp_path).save_to_json(Box({}), name)


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        DataManager(tmp_path).read_json("nope")


def test_default_dir_uses_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert DataManager().base_dir == tmp_path / "text-character-game"
