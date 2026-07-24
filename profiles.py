import copy
import json
import os
import re

from constants import GAME_TEXT_TABLES

PROFILE_FIELDS = (
    "ines_header",
    "full_level_names",
    "level_name_tiles",
    "pointer_to_rom_offset",
    "high_pointer_threshold",
    "high_pointer_offset",
    "level_name_palette_offset",
    "tile_palette_offset",
)

OPTION_DEFAULTS = {
    "open_recent_on_start": True,
    "auto_reload_external": False,
    "auto_save_changes": False,
    "confirm_before_overwrite": True,
    "debug_on_start": False,
    "collapse_worlds_on_start": False,
    "always_on_top": False,
    "show_status_bar": False,
}

FEATURE_DEFAULTS = {
    "edit_level_names": True,
    "edit_world_banners": True,
    "edit_palettes": True,
    "edit_map_tiles": True,
    "level_backups": True,
}

DEFAULT_BACKUP_REGIONS = {
    "Underground": {"bank": 13, "start": 0xA577, "end": 0xBC2B},
    "2P VS": {"bank": 14, "start": 0xC4B6, "end": 0xC571},
    "Plains": {"bank": 15, "start": 0xA4F9, "end": 0xBDDB},
    "Hills": {"bank": 16, "start": 0xA577, "end": 0xB9CE},
    "High Ice": {"bank": 17, "start": 0xA810, "end": 0xBFA7},
    "Water": {"bank": 18, "start": 0xAB8D, "end": 0xB9A8},
    "Sky": {"bank": 19, "start": 0xAA5F, "end": 0xBFDC},
    "Desert": {"bank": 20, "start": 0xAF26, "end": 0xBDB6},
    "Fortress": {"bank": 21, "start": 0xA7E7, "end": 0xBFFF},
    "Airship": {"bank": 23, "start": 0xABF7, "end": 0xBEFB},
}

DEFAULT_GAME_TEXTS = {
    "Throne Room Speech": [
        {
            "id": "king_help_msg_1",
            "name": "Initial Speech",
            "addr": 0x3012A,
            "max": 120,
            "table": "level",
            "line_length": 20,
            "lines": 6,
        },
        {
            "id": "king_help_msg_2",
            "name": "Secondary Speech",
            "addr": 0x301A2,
            "max": 120,
            "table": "level",
            "line_length": 20,
            "lines": 6,
        },
        {
            "id": "king_victory_normal",
            "name": "Victory Speech: Normal",
            "addr": 0x362C4,
            "max": 120,
            "table": "MAIN",
            "line_length": 20,
            "lines": 6,
        },
        {
            "id": "king_victory_frog",
            "name": "Victory Speech: Frog",
            "addr": 0x3633C,
            "max": 120,
            "table": "MAIN",
            "line_length": 20,
            "lines": 6,
        },
        {
            "id": "king_victory_tanooki",
            "name": "Victory Speech: Tanooki",
            "addr": 0x363B4,
            "max": 120,
            "table": "MAIN",
            "line_length": 20,
            "lines": 6,
        },
        {
            "id": "king_victory_hammer_suit",
            "name": "Victory Speech: Hammer Suit",
            "addr": 0x3642C,
            "max": 120,
            "table": "MAIN",
            "line_length": 20,
            "lines": 6,
        },
    ],
    "Princess Letters": [
        {
            "id": "princess_letter_1",
            "name": "World 1 Letter",
            "addr": 0x36792,
            "max": 125,
            "table": "MAIN",
            "terminator": 0xFF,
            "line_length": 20,
            "lines": 7,
        },
        {
            "id": "princess_letter_2",
            "name": "World 2 Letter",
            "addr": 0x3680F,
            "max": 103,
            "table": "MAIN",
            "terminator": 0xFF,
            "line_length": 20,
            "lines": 6,
        },
        {
            "id": "princess_letter_3",
            "name": "World 3 Letter",
            "addr": 0x36876,
            "max": 131,
            "table": "MAIN",
            "terminator": 0xFF,
            "line_length": 20,
            "lines": 7,
        },
        {
            "id": "princess_letter_4",
            "name": "World 4 Letter",
            "addr": 0x368F9,
            "max": 128,
            "table": "MAIN",
            "terminator": 0xFF,
            "line_length": 20,
            "lines": 7,
        },
        {
            "id": "princess_letter_5",
            "name": "World 5 Letter",
            "addr": 0x36979,
            "max": 139,
            "table": "MAIN",
            "terminator": 0xFF,
            "line_length": 20,
            "lines": 7,
        },
        {
            "id": "princess_letter_6",
            "name": "World 6 Letter",
            "addr": 0x36A04,
            "max": 147,
            "table": "MAIN",
            "terminator": 0xFF,
            "line_length": 20,
            "lines": 8,
        },
        {
            "id": "princess_letter_7",
            "name": "World 7 Letter",
            "addr": 0x36A97,
            "max": 119,
            "table": "MAIN",
            "terminator": 0xFF,
            "line_length": 20,
            "lines": 6,
        },
    ],
    "Princess Rescue Speech": [
        {
            "id": "princess_rescue_speech",
            "name": "Speech",
            "addr": 0x31ABB,
            "max": 81,
            "table": "MAIN",
            "terminator": 0x00,
            "line_length": 15,
            "lines": 6,
        },
    ],
    "Toad House Speech": [
        {
            "id": "toad_house_standard",
            "name": "Toad House Standard",
            "addr": 0x05311,
            "max": 90,
            "table": "MAIN",
            "line_length": 15,
            "lines": 6,
        },
        {
            "id": "toad_house_warp_whistle",
            "name": "Toad House Warp Whistle",
            "addr": 0x0536B,
            "max": 90,
            "table": "MAIN",
            "line_length": 15,
            "lines": 6,
        },
        {
            "id": "toad_house_anchor_p_wing",
            "name": "Toad House Anchor / P-Wing",
            "addr": 0x053C5,
            "max": 90,
            "table": "MAIN",
            "line_length": 15,
            "lines": 6,
        },
        {
            "id": "toad_house_sbb_debug",
            "name": "Toad House - SBB Debug",
            "addr": 0x0541F,
            "max": 90,
            "table": "MAIN",
            "line_length": 15,
            "lines": 6,
        },
    ],
}

def _normalize_game_text_table(value):
    value = str(value or "level").strip()
    for table in GAME_TEXT_TABLES:
        if value.lower() == table.lower():
            return table
    raise ValueError(f"Unsupported game text table: {value}")

DEFAULT_PROFILE = {
    "name": "Super Boonie Bros",
    "overworld_names_installed": True,
    "ines_header": 0x10,
    "full_level_names": 0x14008 + 0x10,
    "level_name_tiles": 0x14068 + 0x10,
    "pointer_to_rom_offset": 0x34000,
    "high_pointer_threshold": 0xD000,
    "high_pointer_offset": 0x8000,
    "level_name_palette_offset": 0x36C52 + 0x10,
    "tile_palette_offset": 0x36C52 + 0x10 - 0x80,
    "options": copy.deepcopy(OPTION_DEFAULTS),
    "features": copy.deepcopy(FEATURE_DEFAULTS),
    "backup_regions": copy.deepcopy(DEFAULT_BACKUP_REGIONS),
    "world_banners": {
        "World 1": {"addr": 0x154DD, "max": 15},
        "World 2": {"addr": 0x154F0, "max": 11},
        "World 3": {"addr": 0x154FF, "max": 12},
        "World 4": {"addr": 0x1550F, "max": 18},
    },
    "game_texts": copy.deepcopy(DEFAULT_GAME_TEXTS),
    "rom_data": None,
}


def _normalize_byte(value, label):
    value = parse_number(value)
    if not 0 <= value <= 0xFF:
        raise ValueError(f"{label} must contain only byte values")
    return value


def _normalize_byte_list(values, label, expected_length=None):
    if not isinstance(values, list):
        raise ValueError(f"{label} must be a list")
    if expected_length is not None and len(values) != expected_length:
        raise ValueError(f"{label} must contain {expected_length} bytes")
    return [_normalize_byte(value, label) for value in values]


def _normalize_word(value, label):
    value = parse_number(value)
    if not 0 <= value <= 0xFFFF:
        raise ValueError(f"{label} must be a 16-bit value")
    return value


def _normalize_game_texts(value):
    if not isinstance(value, dict):
        raise ValueError("game_texts must be a JSON object")
    normalized = {}
    for category, default_entries in DEFAULT_GAME_TEXTS.items():
        entries = value.get(category, default_entries)
        if category in (
            "Throne Room Speech",
            "Princess Letters",
            "Princess Rescue Speech",
            "Toad House Speech",
        ):
            entries_by_id = {
                str(entry.get("id", "")).strip(): entry
                for entry in entries
                if isinstance(entry, dict)
            }
            entries = []
            for default_entry in default_entries:
                merged = copy.deepcopy(default_entry)
                existing = entries_by_id.get(default_entry["id"])
                if existing:
                    merged.update(existing)
                if (
                    default_entry["id"].startswith("king_victory_")
                    or default_entry["id"] == "princess_rescue_speech"
                    or default_entry["id"].startswith("toad_house_")
                ):
                    for field in (
                        "name",
                        "addr",
                        "max",
                        "table",
                        "terminator",
                        "line_length",
                        "lines",
                    ):
                        if field in default_entry:
                            merged[field] = default_entry[field]
                entries.append(merged)
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"game_texts.{category} must be a non-empty list")
        normalized_entries = []
        seen_ids = set()
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                raise ValueError(f"game_texts.{category}[{index}] must be an object")
            entry_id = str(entry.get("id") or f"{category}_{index}").strip()
            name = str(entry.get("name") or f"Entry {index}").strip()
            if not entry_id or entry_id in seen_ids:
                raise ValueError(f"Invalid or duplicate game text id in {category}")
            addr = parse_number(entry.get("addr", 0))
            max_length = parse_number(entry.get("max", 0))
            table = _normalize_game_text_table(entry.get("table", "level"))
            if addr < 0 or max_length < 0:
                raise ValueError(f"Invalid game text address or length in {category}")
            line_length = parse_number(entry.get("line_length", 0))
            lines = parse_number(entry.get("lines", 0))
            if line_length < 0 or lines < 0:
                raise ValueError(f"Invalid game text line settings in {category}")
            normalized_entry = {
                "id": entry_id,
                "name": name or f"Entry {index}",
                "addr": addr,
                "max": max_length,
                "table": table,
                "line_length": line_length,
                "lines": lines,
            }
            if "terminator" in entry:
                normalized_entry["terminator"] = _normalize_byte(
                    entry["terminator"],
                    f"game_texts.{category}[{index}].terminator",
                )
            normalized_entries.append(normalized_entry)
            seen_ids.add(entry_id)
        normalized[category] = normalized_entries
    return normalized


def parse_number(value):
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid addresses")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value.strip(), 0)
    raise ValueError(f"Expected an integer or numeric string, got {value!r}")


def normalize_profile(data):
    if not isinstance(data, dict):
        raise ValueError("Profile root must be a JSON object")

    result = copy.deepcopy(DEFAULT_PROFILE)
    for field in (
        ("name", "overworld_names_installed") + PROFILE_FIELDS +
        (
            "world_banners",
            "game_texts",
            "options",
            "features",
            "backup_regions",
            "rom_data",
        )
    ):
        if field in data:
            result[field] = data[field]
    result["name"] = str(result.get("name", "")).strip()
    if not result["name"]:
        raise ValueError("Profile name cannot be empty")
    result["overworld_names_installed"] = bool(
        result.get("overworld_names_installed", True)
    )

    for field in PROFILE_FIELDS:
        result[field] = parse_number(result[field])
        if result[field] < 0:
            raise ValueError(f"{field} cannot be negative")

    banners = result.get("world_banners")
    if not isinstance(banners, dict):
        raise ValueError("world_banners must be a JSON object")

    normalized_banners = {}
    for world in DEFAULT_PROFILE["world_banners"]:
        info = banners.get(world)
        if not isinstance(info, dict):
            raise ValueError(f"Missing banner settings for {world}")
        addr = parse_number(info.get("addr"))
        max_length = parse_number(info.get("max"))
        if addr < 0 or max_length < 1:
            raise ValueError(f"Invalid banner settings for {world}")
        normalized_banners[world] = {"addr": addr, "max": max_length}

    result["world_banners"] = normalized_banners
    result["game_texts"] = _normalize_game_texts(result.get("game_texts"))

    options = result.get("options")
    if not isinstance(options, dict):
        raise ValueError("options must be a JSON object")
    result["options"] = {
        key: bool(options.get(key, default))
        for key, default in OPTION_DEFAULTS.items()
    }

    features = result.get("features")
    if not isinstance(features, dict):
        raise ValueError("features must be a JSON object")
    result["features"] = {
        key: bool(features.get(key, default))
        for key, default in FEATURE_DEFAULTS.items()
    }

    regions = result.get("backup_regions")
    if not isinstance(regions, dict) or not regions:
        raise ValueError("backup_regions must be a non-empty JSON object")
    normalized_regions = {}
    for name, info in regions.items():
        if not isinstance(info, dict) or not str(name).strip():
            raise ValueError("Each backup region must have a name and settings")
        bank = parse_number(info.get("bank"))
        start = parse_number(info.get("start"))
        end = parse_number(info.get("end"))
        if bank < 0 or start < 0 or end < start:
            raise ValueError(f"Invalid backup region: {name}")
        normalized_regions[str(name).strip()] = {
            "bank": bank,
            "start": start,
            "end": end,
        }
    result["backup_regions"] = normalized_regions

    rom_data = result.get("rom_data")
    if rom_data is not None:
        if not isinstance(rom_data, dict):
            raise ValueError("rom_data must be a JSON object or null")
        banner_data = rom_data.get("world_banners")
        banner_positions = rom_data.get("world_banner_positions")
        level_names = rom_data.get("level_names")
        game_texts = rom_data.get("game_texts")
        if banner_data is not None and not isinstance(banner_data, dict):
            raise ValueError("rom_data.world_banners must be a JSON object or null")
        if level_names is not None and (
            not isinstance(level_names, list) or len(level_names) != 48
        ):
            raise ValueError("rom_data.level_names must contain 48 records or be null")
        if banner_positions is not None and not isinstance(banner_positions, dict):
            raise ValueError(
                "rom_data.world_banner_positions must be a JSON object or null"
            )
        if game_texts is not None and not isinstance(game_texts, dict):
            raise ValueError("rom_data.game_texts must be a JSON object or null")
        result["rom_data"] = {
            "world_banners": None if banner_data is None else {
                world: _normalize_byte_list(
                    banner_data.get(world),
                    f"rom_data.world_banners.{world}",
                )
                for world in DEFAULT_PROFILE["world_banners"]
            },
            "level_names": None if level_names is None else [
                _normalize_byte_list(record, f"rom_data.level_names[{index}]", 18)
                for index, record in enumerate(level_names)
            ],
            "world_banner_positions": None if banner_positions is None else {
                world: _normalize_word(
                    banner_positions.get(world),
                    f"rom_data.world_banner_positions.{world}",
                )
                for world in DEFAULT_PROFILE["world_banners"]
            },
            "game_texts": None if game_texts is None else {
                entry["id"]: _normalize_byte_list(
                    game_texts.get(entry["id"], []),
                    f"rom_data.game_texts.{entry['id']}",
                )
                for entries in result["game_texts"].values()
                for entry in entries
            },
            "level_name_palettes": _normalize_byte_list(
                rom_data.get("level_name_palettes"),
                "rom_data.level_name_palettes",
                64,
            ),
            "tile_palettes": _normalize_byte_list(
                rom_data.get("tile_palettes"),
                "rom_data.tile_palettes",
                64,
            ),
        }
    return result


class ProfileStore:
    def __init__(self, directory):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)
        if not self.list_files():
            self.save(DEFAULT_PROFILE, "Super Boonie Bros.json")

    @staticmethod
    def safe_filename(name):
        stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
        if not stem:
            stem = "Profile"
        return f"{stem}.json"

    def list_files(self):
        return sorted(
            (name for name in os.listdir(self.directory)
             if name.lower().endswith(".json")),
            key=str.casefold,
        )

    def path_for(self, filename):
        filename = os.path.basename(filename)
        if not filename.lower().endswith(".json"):
            raise ValueError("Profile filename must end in .json")
        return os.path.join(self.directory, filename)

    def load(self, filename):
        with open(self.path_for(filename), "r", encoding="utf-8") as handle:
            raw_profile = json.load(handle)
        profile = normalize_profile(raw_profile)
        if raw_profile != profile:
            self.save(profile, filename)
        return profile

    def save(self, profile, filename=None):
        profile = normalize_profile(profile)
        filename = filename or self.safe_filename(profile["name"])
        with open(self.path_for(filename), "w", encoding="utf-8") as handle:
            json.dump(profile, handle, indent=4)
            handle.write("\n")
        return filename

    def delete(self, filename):
        if len(self.list_files()) <= 1:
            raise ValueError("At least one profile must remain")
        os.remove(self.path_for(filename))
