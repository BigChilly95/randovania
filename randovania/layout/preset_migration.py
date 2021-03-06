import json
from pathlib import Path
from typing import Optional

import aiofiles
import slugify

from randovania.layout.preset import Preset

CURRENT_PRESET_VERSION = 4


class InvalidPreset(Exception):
    def __init__(self, original_exception: Exception):
        self.original_exception = original_exception


def _migrate_v1(preset: dict) -> dict:
    layout_configuration = preset["layout_configuration"]
    layout_configuration["beam_configuration"] = {
        "power": {
            "item_index": 0,
            "ammo_a": -1,
            "ammo_b": -1,
            "uncharged_cost": 0,
            "charged_cost": 0,
            "combo_missile_cost": 5,
            "combo_ammo_cost": 0
        },
        "dark": {
            "item_index": 1,
            "ammo_a": 45,
            "ammo_b": -1,
            "uncharged_cost": 1,
            "charged_cost": 5,
            "combo_missile_cost": 5,
            "combo_ammo_cost": 30
        },
        "light": {
            "item_index": 2,
            "ammo_a": 46,
            "ammo_b": -1,
            "uncharged_cost": 1,
            "charged_cost": 5,
            "combo_missile_cost": 5,
            "combo_ammo_cost": 30
        },
        "annihilator": {
            "item_index": 3,
            "ammo_a": 46,
            "ammo_b": 45,
            "uncharged_cost": 1,
            "charged_cost": 5,
            "combo_missile_cost": 5,
            "combo_ammo_cost": 30
        }
    }
    layout_configuration["skip_final_bosses"] = False
    layout_configuration["energy_per_tank"] = 100.0
    return preset


def _migrate_v2(preset: dict) -> dict:
    level_renaming = {
        "trivial": "beginner",
        "easy": "intermediate",
        "normal": "advanced",
        "hard": "expert",
        "minimal-restrictions": "minimal-logic",
    }
    trick_level = preset["layout_configuration"]["trick_level"]
    trick_level["global_level"] = level_renaming.get(trick_level["global_level"], trick_level["global_level"])
    for specific, value in trick_level["specific_levels"].items():
        trick_level["specific_levels"][specific] = level_renaming.get(value, value)

    return preset


def _migrate_v3(preset: dict) -> dict:
    preset["layout_configuration"]["safe_zone"] = {
        "fully_heal": True,
        "prevents_dark_aether": True,
        "heal_per_second": 1.0,
    }
    return preset


_MIGRATIONS = {
    1: _migrate_v1,
    2: _migrate_v2,
    3: _migrate_v3,
}


def _apply_migration(preset: dict, version: int) -> dict:
    while version < CURRENT_PRESET_VERSION:
        preset = _MIGRATIONS[version](preset)
        version += 1
    return preset


def convert_to_current_version(preset: dict) -> dict:
    schema_version = preset["schema_version"]
    if schema_version > CURRENT_PRESET_VERSION:
        raise ValueError(f"Unknown version: {schema_version}")

    if schema_version < CURRENT_PRESET_VERSION:
        return _apply_migration(preset, schema_version)
    else:
        return preset


class VersionedPreset:
    data: dict
    _converted = False
    exception: Optional[InvalidPreset] = None
    _preset: Optional[Preset] = None

    def __init__(self, data):
        self.data = data

    @classmethod
    def file_extension(cls) -> str:
        return "rdvpreset"

    @property
    def slug_name(self) -> str:
        return slugify.slugify(self.name)

    @property
    def name(self) -> str:
        if self.data is None:
            return self._preset.name
        else:
            return self.data["name"]

    def __eq__(self, other):
        if isinstance(other, VersionedPreset):
            return self.get_preset() == other.get_preset()
        return False

    def ensure_converted(self):
        if not self._converted:
            try:
                self._preset = Preset.from_json_dict(convert_to_current_version(self.data))
                self._converted = True
            except (ValueError, KeyError) as e:
                self.exception = InvalidPreset(e)

    def get_preset(self) -> Preset:
        self.ensure_converted()
        if self.exception:
            raise self.exception
        else:
            return self._preset

    @classmethod
    async def from_file(cls, path: Path) -> "VersionedPreset":
        async with aiofiles.open(path) as f:
            return VersionedPreset(json.loads(await f.read()))

    @classmethod
    def from_file_sync(cls, path: Path) -> "VersionedPreset":
        with path.open() as f:
            return VersionedPreset(json.load(f))

    @classmethod
    def with_preset(cls, preset: Preset) -> "VersionedPreset":
        result = VersionedPreset(None)
        result._converted = True
        result._preset = preset
        return result

    def save_to_file(self, path: Path):
        path.parent.mkdir(exist_ok=True, parents=True)
        with path.open("w") as preset_file:
            json.dump(self.as_json, preset_file, indent=4)

    @property
    def as_json(self) -> dict:
        if self._converted:
            preset_json = {
                "schema_version": CURRENT_PRESET_VERSION,
            }
            preset_json.update(self._preset.as_json)
            return preset_json
        else:
            return self.data
