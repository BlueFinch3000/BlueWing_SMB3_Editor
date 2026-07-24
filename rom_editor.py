import copy
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

import backup_engine
from constants import *


class RomEditorMixin:
    LEVEL_NAME_COUNT = 48
    LEVEL_NAME_RECORD_SIZE = 18
    PROFILE_PALETTE_SIZE = 64

    def _require_rom_range(self, start, length, label):
        if start < 0 or start + length > len(self.rom):
            raise ValueError(
                f"{label} range 0x{start:X}-0x{start + length - 1:X} "
                "is outside the loaded ROM"
            )

    def _level_name_record_offset(self, profile, index):
        pointer_offset = profile["full_level_names"] + index * 2
        self._require_rom_range(pointer_offset, 2, "Level name pointer table")
        cpu = self.rom[pointer_offset] | (self.rom[pointer_offset + 1] << 8)
        if cpu >= profile["high_pointer_threshold"]:
            return cpu + profile["high_pointer_offset"] + profile["ines_header"]
        return cpu + profile["pointer_to_rom_offset"] + profile["ines_header"]

    def _game_text_entries(self, profile=None):
        profile = profile or self.profile
        for category, entries in profile["game_texts"].items():
            for entry in entries:
                yield category, entry

    def _game_text_entry_by_id(self, entry_id):
        for category, entry in self._game_text_entries():
            if entry["id"] == entry_id:
                return category, entry
        return None, None

    def _princess_letter_index(self, entry):
        entry_id = entry.get("id", "")
        prefix = "princess_letter_"
        if not entry_id.startswith(prefix):
            return None
        try:
            index = int(entry_id[len(prefix):])
        except ValueError:
            return None
        return index if 1 <= index <= 7 else None

    def _runtime_game_text_entry(self, entry, profile=None):
        runtime = copy.deepcopy(entry)
        index = self._princess_letter_index(entry)
        if index is None:
            return runtime
        text_length = max(0, runtime.get("max", 0) - 1)
        runtime.update({
            "table": "MAIN",
            "terminator": 0xFF,
            "line_length": 20,
            "lines": min(8, max(6, (text_length + 19) // 20)),
        })
        return runtime

    def _game_text_address(self, entry):
        return entry["addr"]

    def _game_text_configured(self, entry):
        return entry["addr"] > 0 and entry["max"] > 0

    def capture_game_text_rom_data(self, profile):
        existing = (profile.get("rom_data") or {}).get("game_texts") or {}
        game_texts = {}
        for category, entry in self._game_text_entries(profile):
            entry = self._runtime_game_text_entry(entry, profile)
            entry_id = entry["id"]
            if not self._game_text_configured(entry):
                game_texts[entry_id] = existing.get(entry_id, [])
                continue
            address = self._game_text_address(entry)
            self._require_rom_range(address, entry["max"], f"{category} / {entry['name']}")
            game_texts[entry_id] = list(self.rom[address:address + entry["max"]])
        return game_texts

    def restore_game_text_rom_data(self, profile, data):
        game_texts = data.get("game_texts")
        if not game_texts:
            return
        for category, entry in self._game_text_entries(profile):
            entry = self._runtime_game_text_entry(entry, profile)
            saved = game_texts.get(entry["id"])
            if not saved or not self._game_text_configured(entry):
                continue
            if len(saved) != entry["max"]:
                continue
            terminator = entry.get("terminator")
            if terminator is not None and saved[-1] != terminator:
                continue
            length = min(len(saved), entry["max"])
            address = self._game_text_address(entry)
            self._require_rom_range(address, length, f"{category} / {entry['name']}")
            self.rom[address:address + length] = bytes(saved[:length])

    def capture_profile_rom_data(self, profile=None):
        if not self.rom:
            return None
        profile = profile or self.profile
        existing = profile.get("rom_data") or {}
        banners = existing.get("world_banners")
        banner_positions = existing.get("world_banner_positions")
        level_names = existing.get("level_names")
        game_texts = self.capture_game_text_rom_data(profile)
        if profile.get("overworld_names_installed", True):
            banners = {}
            banner_positions = {}
            for world, info in profile["world_banners"].items():
                address = info["addr"] + profile["ines_header"]
                self._require_rom_range(address - 2, 3, f"{world} banner")
                banner_positions[world] = (
                    (self.rom[address - 2] << 8) | self.rom[address - 1]
                )
                length = min(self.rom[address], info["max"])
                self._require_rom_range(address, length + 2, f"{world} banner")
                banners[world] = list(self.rom[address:address + length + 2])

            level_names = []
            for index in range(self.LEVEL_NAME_COUNT):
                offset = self._level_name_record_offset(profile, index)
                self._require_rom_range(
                    offset, self.LEVEL_NAME_RECORD_SIZE, f"Level name {index + 1}"
                )
                level_names.append(
                    list(self.rom[offset:offset + self.LEVEL_NAME_RECORD_SIZE])
                )

        palette_offset = profile["level_name_palette_offset"]
        tile_palette_offset = profile["tile_palette_offset"]
        self._require_rom_range(
            palette_offset, self.PROFILE_PALETTE_SIZE, "Level name palettes"
        )
        self._require_rom_range(
            tile_palette_offset, self.PROFILE_PALETTE_SIZE, "Tile palettes"
        )
        return {
            "world_banners": banners,
            "world_banner_positions": banner_positions,
            "level_names": level_names,
            "game_texts": game_texts,
            "level_name_palettes": list(
                self.rom[palette_offset:palette_offset + self.PROFILE_PALETTE_SIZE]
            ),
            "tile_palettes": list(
                self.rom[
                    tile_palette_offset:tile_palette_offset + self.PROFILE_PALETTE_SIZE
                ]
            ),
        }

    def restore_profile_rom_data(self, profile=None):
        if not self.rom:
            return
        profile = profile or self.profile
        data = profile.get("rom_data")
        if not data:
            return
        if profile.get("overworld_names_installed", True):
            if data.get("world_banner_positions"):
                for world, info in profile["world_banners"].items():
                    address = info["addr"] + profile["ines_header"]
                    value = data["world_banner_positions"][world]
                    self._require_rom_range(address - 2, 2, f"{world} banner position")
                    self.rom[address - 2] = (value >> 8) & 0xFF
                    self.rom[address - 1] = value & 0xFF
            if data.get("world_banners"):
                for world, info in profile["world_banners"].items():
                    address = info["addr"] + profile["ines_header"]
                    saved = data["world_banners"][world]
                    length = min(
                        saved[0] if saved else 0,
                        info["max"],
                        max(0, len(saved) - 2),
                    )
                    block = saved[:length + 1] + [0]
                    block[0] = length
                    self._require_rom_range(address, len(block), f"{world} banner")
                    self.rom[address:address + len(block)] = bytes(block)

            if data.get("level_names"):
                for index, record in enumerate(data["level_names"]):
                    offset = self._level_name_record_offset(profile, index)
                    self._require_rom_range(
                        offset, self.LEVEL_NAME_RECORD_SIZE, f"Level name {index + 1}"
                    )
                    self.rom[offset:offset + self.LEVEL_NAME_RECORD_SIZE] = bytes(record)

        self.restore_game_text_rom_data(profile, data)

        palette_offset = profile["level_name_palette_offset"]
        tile_palette_offset = profile["tile_palette_offset"]
        self._require_rom_range(
            palette_offset, self.PROFILE_PALETTE_SIZE, "Level name palettes"
        )
        self._require_rom_range(
            tile_palette_offset, self.PROFILE_PALETTE_SIZE, "Tile palettes"
        )
        self.rom[palette_offset:palette_offset + self.PROFILE_PALETTE_SIZE] = bytes(
            data["level_name_palettes"]
        )
        self.rom[
            tile_palette_offset:tile_palette_offset + self.PROFILE_PALETTE_SIZE
        ] = bytes(data["tile_palettes"])

    def initialize_profile_rom_data_for_opened_rom(self):
        if not self.rom:
            return
        self.profile["rom_data"] = self.capture_profile_rom_data(self.profile)
        self.profile_store.save(self.profile, self.profile_filename)
        if self.editing_profile_filename == self.profile_filename:
            self.editing_profile = self.profile

    def initialize_or_restore_profile_rom_data(self):
        self.initialize_profile_rom_data_for_opened_rom()

    def save_profile_rom_data(self):
        if not self.rom:
            return
        self.apply_current_game_text_settings()
        self.profile["rom_data"] = self.capture_profile_rom_data(self.profile)
        self.profile_store.save(self.profile, self.profile_filename)
        if self.editing_profile_filename == self.profile_filename:
            self.editing_profile = self.profile

    def write_rom(self, path):
        self.save_profile_rom_data()
        with open(path, "wb") as handle:
            handle.write(self.rom)

    def refresh_backup_menus(self):
        if not hasattr(self, "backup_tileset_menu"):
            return
        self.backup_tileset_menu.delete(0, "end")
        self.restore_tileset_menu.delete(0, "end")
        for region in self.profile["backup_regions"]:
            self.backup_tileset_menu.add_command(
                label=region,
                command=lambda name=region: self.backup_region(name)
            )
            self.restore_tileset_menu.add_command(
                label=region,
                command=lambda name=region: self.restore_region(name)
            )
        state = "normal" if self.profile["features"]["level_backups"] else "disabled"
        self.menubar.entryconfig("Level Backups", state=state)
        if hasattr(self, "level_backups_node"):
            self.refresh_backup_tree_nodes()

    def refresh_backup_tree_nodes(self):
        for node in self.tree.get_children(self.level_backups_node):
            self.tree.delete(node)
        self.backup_region_nodes = {}
        for region in self.profile["backup_regions"]:
            node = self.tree.insert(self.level_backups_node, "end", text=region)
            self.backup_region_nodes[node] = region

    def refresh_game_text_tree_nodes(self):
        for node in self.tree.get_children(self.game_text_node):
            self.tree.delete(node)
        self.game_text_category_nodes = {}
        self.game_text_entry_nodes = {}
        for category, entries in self.profile["game_texts"].items():
            category_node = self.tree.insert(
                self.game_text_node,
                "end",
                text=category,
                open=True,
            )
            self.game_text_category_nodes[category_node] = category
            for entry in entries:
                entry_node = self.tree.insert(
                    category_node,
                    "end",
                    text=entry["name"],
                )
                self.game_text_entry_nodes[entry_node] = entry["id"]

    def _hide_editor_frames(self):
        for frame_name in (
            "world_frame",
            "palette_frame",
            "profile_frame",
            "backups_frame",
            "game_text_frame",
            "splash_frame",
        ):
            getattr(self, frame_name).pack_forget()
        self.mode_label.pack_forget()
        self.name.pack_forget()
        self.preview.pack_forget()
        self.attr_frame.pack_forget()

    def show_world_banner_editor(self, world_name):
        self._hide_editor_frames()
        self.current_mode = "world"
        self.current_world = world_name
        self.world_title.config(text=world_name)
        self.world_frame.pack(fill="both", expand=True)
        self.load_world_banner()

    def load_world_banner(self):
        if not self.rom or not self.current_world:
            self.banner_entry.delete(0, "end")
            self.apply_feature_controls()
            return
        info = self.profile["world_banners"][self.current_world]
        address = info["addr"] + self.profile["ines_header"]
        self._require_rom_range(address - 2, 3, f"{self.current_world} banner")
        self.banner_position_var.set(
            (self.rom[address - 2] << 8) | self.rom[address - 1]
        )
        length = min(self.rom[address], info["max"])
        text = self.decode_world_banner(self.rom[address + 1:address + 1 + length])
        self.banner_entry.config(state="normal")
        self.banner_entry.delete(0, "end")
        self.banner_entry.insert(0, text)
        self.validate_banner()
        self.apply_feature_controls()

    def restore_region(self, region):

        if not self.path or not self.profile["features"]["level_backups"]:
            return

        roots = backup_engine.backup_roots(
            self.path, self.profile_filename, self.profile["name"]
        )
        initial_root = next((root for root in roots if os.path.isdir(root)), roots[0])
        backup_file = filedialog.askopenfilename(
            title=f"Restore {region}",
            filetypes=[("Level Backups", "*.lvls")],
            initialdir=os.path.join(
                initial_root,
                region
            )
        )

        if not backup_file:
            return

        backup_engine.restore_tileset(
            self.path,
            region,
            backup_file,
            self.profile["backup_regions"],
            self.profile["ines_header"]
        )

        self.rom = bytearray(
            open(self.path, "rb").read()
        )
        print(f"Level backup restored: {region} <- {backup_file}")
        if self.current_mode == "backups":
            self.show_backup_status(getattr(self, "current_backup_region", region))

    def backup_region(self, region):

        if not self.path or not self.profile["features"]["level_backups"]:
            return

        backup_file = backup_engine.backup_tileset(
            self.path,
            region,
            self.profile["backup_regions"],
            self.profile["ines_header"],
            self.profile_filename
        )

        messagebox.showinfo(
            "Backup Complete",
            backup_file
        )
        print(f"Level backup created: {region} -> {backup_file}")
        if self.current_mode == "backups":
            self.show_backup_status(getattr(self, "current_backup_region", region))
    def do_backup_all(self):

        if not self.path or not self.profile["features"]["level_backups"]:
            return

        files = backup_engine.backup_all_tilesets(
            self.path,
            self.profile["backup_regions"],
            self.profile["ines_header"],
            self.profile_filename
        )

        messagebox.showinfo(
            "Backup Complete",
            f"{len(files)} tilesets backed up."
        )
        print(
            f"Level backup complete: {len(files)} tilesets for "
            f"{self.profile_filename}"
        )
        if self.current_mode == "backups":
            self.show_backup_status()

    def do_restore_all(self):

        if not self.path or not self.profile["features"]["level_backups"]:
            return

        restored = backup_engine.restore_all_tilesets(
            self.path,
            self.profile["backup_regions"],
            self.profile["ines_header"],
            self.profile_filename,
            self.profile["name"],
        )

        self.rom = bytearray(
            open(self.path, "rb").read()
        )

        messagebox.showinfo(
            "Restore Complete",
            f"{len(restored)} tilesets restored."
        )
        print(
            f"Level restore complete: {len(restored)} tilesets for "
            f"{self.profile_filename}"
        )
        if self.current_mode == "backups":
            self.show_backup_status()

    def show_backup_status(self, region=None):
        self._hide_editor_frames()
        self.current_mode = "backups"
        self.current_backup_region = region
        self.backup_refresh_button.config(
            command=lambda selected=region: self.show_backup_status(selected)
        )
        self.backups_frame.pack(fill="both", expand=True)
        for widget in self.backup_status_rows.winfo_children():
            widget.destroy()
        if region:
            self.backup_screen_title.set(f"{region} Backups")
            self.backup_primary_button.config(
                text=f"Backup {region}",
                command=lambda name=region: self.backup_region(name),
            )
            self.restore_primary_button.config(
                text="Restore Backup...",
                command=lambda name=region: self.restore_region(name),
            )
        else:
            self.backup_screen_title.set("Level Backups")
            self.backup_primary_button.config(
                text="Backup All", command=self.do_backup_all
            )
            self.restore_primary_button.config(
                text="Restore Latest", command=self.do_restore_all
            )
        if not self.path:
            self.backup_status_summary.set("Load a ROM to view backups.")
            return

        backed_up = 0
        regions = (
            (region,)
            if region in self.profile["backup_regions"]
            else tuple(self.profile["backup_regions"])
        )
        for row, region in enumerate(regions):
            files = backup_engine.region_backups(
                self.path, region, self.profile_filename, self.profile["name"]
            )
            if files:
                backed_up += 1
                latest = datetime.fromtimestamp(os.path.getmtime(files[0])).strftime(
                    "%Y-%m-%d %I:%M %p"
                )
                status = f"{len(files)} backup{'s' if len(files) != 1 else ''}; latest {latest}"
            else:
                status = "No backups"
            tk.Label(self.backup_status_rows, text=region).grid(
                row=row, column=0, sticky="w", padx=(0, 18), pady=2
            )
            tk.Label(
                self.backup_status_rows,
                text=status,
                fg="#207040" if files else "#777777",
            ).grid(row=row, column=1, sticky="w", pady=2)

        total = len(regions)
        if region:
            self.backup_status_summary.set(
                f"Backup status for {region} in {self.profile_filename}."
            )
            return
        if backed_up == total:
            overall = "Complete"
        elif backed_up:
            overall = "Partial"
        else:
            overall = "None"
        self.backup_status_summary.set(
            f"{overall}: {backed_up} of {total} configured regions have backups "
            f"for {self.profile_filename}."
        )

    def decode_game_text(self, data, table):
        if table in CUSTOM_TEXT_TABLES:
            decode_map = CUSTOM_TEXT_TABLES[table]["decode"]
            return "".join(decode_map.get(value, " ") for value in data).rstrip()
        if table == "world":
            return "".join(WORLD_CHAR_MAP.get(value, " ") for value in data).rstrip()
        if table == "ascii":
            return bytes(data).decode("ascii", errors="replace").rstrip("\x00 ")
        return "".join(CHAR_MAP.get(value, " ") for value in data).rstrip()

    def display_game_text(self, data, entry):
        terminator = entry.get("terminator")
        if terminator is not None and terminator in data:
            data = data[:data.index(terminator)]
        text = self.decode_game_text(data, entry.get("table", "level"))
        line_length = entry.get("line_length", 0)
        lines = entry.get("lines", 0)
        if line_length <= 0 or lines <= 0:
            return text
        rows = []
        padded = text.ljust(line_length * lines)
        for index in range(lines):
            start = index * line_length
            rows.append(padded[start:start + line_length].rstrip())
        return "\n".join(rows).rstrip()

    def _normalize_game_text_case(self, text, table):
        if table in CUSTOM_TEXT_TABLES or table == "ascii":
            return text
        return text.upper()

    def reflow_game_text(self, text, entry, table, max_length):
        text = self._normalize_game_text_case(text, table)
        if not entry or entry.get("line_length", 0) <= 0 or entry.get("lines", 0) <= 0:
            return text[:max_length] if max_length > 0 else text
        line_length = entry["line_length"]
        lines = entry["lines"]
        compact = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "")
        compact = compact[:max(0, max_length)]
        rows = [
            compact[index:index + line_length]
            for index in range(0, min(len(compact), line_length * lines), line_length)
        ]
        return "\n".join(rows)

    def prepare_game_text(self, text, entry):
        line_length = entry.get("line_length", 0)
        lines = entry.get("lines", 0)
        table = entry.get("table", "level")
        if table in CUSTOM_TEXT_TABLES or table == "ascii":
            normalize = lambda value: value
        else:
            normalize = lambda value: value.upper()
        if line_length <= 0 or lines <= 0:
            return normalize(text)[:entry["max"]]
        rows = normalize(text).splitlines()[:lines]
        rows.extend([""] * max(0, lines - len(rows)))
        return "".join(row[:line_length].ljust(line_length) for row in rows)

    def encode_game_text(self, text, table, max_length):
        if table in CUSTOM_TEXT_TABLES:
            custom_table = CUSTOM_TEXT_TABLES[table]
            values = [
                custom_table["encode"].get(char, custom_table["pad"])
                for char in text[:max_length]
            ]
            pad = custom_table["pad"]
        elif table == "world":
            text = text.upper()[:max_length]
            values = [WORLD_TEXT_MAP.get(char, 0xFF) for char in text]
            pad = 0xFF
        elif table == "ascii":
            text = text[:max_length]
            values = [ord(char) if 0 <= ord(char) <= 0x7F else 0x20 for char in text]
            pad = 0x20
        else:
            text = text.upper()[:max_length]
            values = [TEXT_MAP.get(char, 0x41) for char in text]
            pad = 0x41
        values.extend([pad] * max(0, max_length - len(values)))
        return bytes(values[:max_length])

    def encode_terminated_game_text(self, text, entry):
        terminator = entry.get("terminator")
        if terminator is None:
            return self.encode_game_text(text, entry["table"], entry["max"])
        max_text_length = max(0, entry["max"] - 1)
        encoded = bytearray(self.encode_game_text(text, entry["table"], max_text_length))
        encoded.append(terminator)
        return bytes(encoded[:entry["max"]])

    def show_game_text_editor(self, entry_id):
        self._hide_editor_frames()
        self.current_mode = "game_text"
        self.current_game_text_id = entry_id
        self.game_text_frame.pack(fill="both", expand=True)
        self.load_game_text()

    def load_game_text(self):
        category, entry = self._game_text_entry_by_id(
            getattr(self, "current_game_text_id", None)
        )
        if not entry:
            return
        entry = self._runtime_game_text_entry(entry)
        self.game_text_title.set(f"{category} / {entry['name']}")
        self.game_text_addr_var.set(f"0x{entry['addr']:X}")
        self.game_text_max_var.set(str(entry["max"]))
        self.game_text_table_var.set(entry.get("table", "level"))
        self.game_text_body.delete("1.0", "end")
        if not self.rom:
            self.game_text_limit.set("Load a ROM to edit this text.")
            self.set_game_text_hex("")
            return
        if not self._game_text_configured(entry):
            self.game_text_limit.set("Set an address and max length, then save.")
            self.set_game_text_hex("")
            return
        address = self._game_text_address(entry)
        self._require_rom_range(address, entry["max"], f"{category} / {entry['name']}")
        data = self.rom[address:address + entry["max"]]
        self.game_text_body.insert(
            "1.0",
            self.display_game_text(data, entry)
        )
        self.validate_game_text()

    def set_game_text_hex(self, text):
        self.game_text_hex.delete("1.0", "end")
        if text:
            self.game_text_hex.insert("1.0", text)

    def format_game_text_hex(self, encoded, entry):
        if entry and entry.get("line_length", 0) > 0 and entry.get("lines", 0) > 0:
            line_length = entry["line_length"]
            lines = entry["lines"]
            rows = []
            for index in range(lines):
                start = index * line_length
                row = encoded[start:start + line_length]
                rows.append(" ".join(f"{value:02X}" for value in row))
            return "HEX:\n" + "\n".join(rows)
        return "HEX:\n" + " ".join(f"{value:02X}" for value in encoded)

    def normalize_game_text_body(self, raw_text, entry, table, max_length):
        raw_text = self._normalize_game_text_case(raw_text, table)
        if entry and entry.get("line_length", 0) > 0 and entry.get("lines", 0) > 0:
            rows = raw_text.split("\n")[:entry["lines"]]
            rows = [row[:entry["line_length"]] for row in rows]
            return "\n".join(rows)
        if max_length > 0:
            return raw_text[:max_length]
        return raw_text

    def paste_game_text(self, event=None):
        category, entry = self._game_text_entry_by_id(
            getattr(self, "current_game_text_id", None)
        )
        if entry:
            entry = self._runtime_game_text_entry(entry)
        table = self.game_text_table_var.get()
        try:
            max_length = int(self.game_text_max_var.get().strip(), 0)
        except ValueError:
            max_length = 0
        text_limit = max_length - 1 if entry and entry.get("terminator") is not None else max_length
        try:
            pasted = self.root.clipboard_get()
        except tk.TclError:
            return "break"
        try:
            start = self.game_text_body.index("sel.first")
            end = self.game_text_body.index("sel.last")
            self.game_text_body.delete(start, end)
        except tk.TclError:
            pass
        self.game_text_body.insert(tk.INSERT, pasted)
        text = self.reflow_game_text(
            self.game_text_body.get("1.0", "end-1c"),
            entry,
            table,
            max(0, text_limit),
        )
        self.game_text_body.delete("1.0", "end")
        self.game_text_body.insert("1.0", text)
        self.game_text_body.mark_set(tk.INSERT, "insert")
        self.validate_game_text()
        return "break"

    def validate_game_text(self):
        try:
            max_length = int(self.game_text_max_var.get().strip(), 0)
        except ValueError:
            max_length = 0
        category, entry = self._game_text_entry_by_id(
            getattr(self, "current_game_text_id", None)
        )
        if entry:
            entry = self._runtime_game_text_entry(entry)
        table = self.game_text_table_var.get()
        raw_text = self.game_text_body.get("1.0", "end-1c")
        text_limit = max_length - 1 if entry and entry.get("terminator") is not None else max_length
        text = self.normalize_game_text_body(raw_text, entry, table, max(0, text_limit))
        if text != raw_text:
            position = self.game_text_body.index(tk.INSERT)
            self.game_text_body.delete("1.0", "end")
            self.game_text_body.insert("1.0", text)
            self.game_text_body.mark_set(tk.INSERT, position)
        prepared = self.prepare_game_text(text, entry) if entry else text
        if entry and entry.get("terminator") is not None:
            encoded = self.encode_terminated_game_text(prepared, entry)
        else:
            encoded = self.encode_game_text(prepared, table, max(0, max_length))
        count = len(text.replace("\n", ""))
        if entry and entry.get("line_length", 0) > 0 and entry.get("lines", 0) > 0:
            self.game_text_limit.set(
                f"{count} / {max(0, text_limit)} characters; "
                f"{entry['line_length']} per line, {entry['lines']} lines max"
            )
        else:
            self.game_text_limit.set(f"{count} / {max(0, text_limit)} characters")
        self.set_game_text_hex(self.format_game_text_hex(encoded, entry))

    def apply_current_game_text_settings(self):
        if getattr(self, "current_mode", None) != "game_text":
            return
        category, entry = self._game_text_entry_by_id(
            getattr(self, "current_game_text_id", None)
        )
        if not entry:
            return
        try:
            edited_addr = int(self.game_text_addr_var.get().strip(), 0)
            edited_max = int(self.game_text_max_var.get().strip(), 0)
            edited_table = self.game_text_table_var.get()
        except (AttributeError, ValueError):
            return
        if edited_addr < 0 or edited_max < 0:
            return
        entry["addr"] = edited_addr
        entry["max"] = edited_max
        entry["table"] = edited_table
        if self.editing_profile_filename == self.profile_filename:
            self.editing_profile = self.profile

    def save_game_text(self):
        category, entry = self._game_text_entry_by_id(
            getattr(self, "current_game_text_id", None)
        )
        if not entry:
            return
        try:
            edited_addr = int(self.game_text_addr_var.get().strip(), 0)
            edited_max = int(self.game_text_max_var.get().strip(), 0)
            edited_table = self.game_text_table_var.get()
            if edited_addr < 0 or edited_max < 0:
                raise ValueError("Address and max length cannot be negative")
            entry["addr"] = edited_addr
            entry["max"] = edited_max
            entry["table"] = edited_table
        except Exception as exc:
            messagebox.showerror("Game Text", str(exc))
            return
        entry = self._runtime_game_text_entry(entry)

        if not self.rom:
            self.profile_store.save(self.profile, self.profile_filename)
            return
        if not self._game_text_configured(entry):
            self.profile_store.save(self.profile, self.profile_filename)
            self.game_text_limit.set("Set an address and max length, then save.")
            return

        address = self._game_text_address(entry)
        try:
            self._require_rom_range(address, entry["max"], f"{category} / {entry['name']}")
            prepared = self.prepare_game_text(
                self.game_text_body.get("1.0", "end-1c"),
                entry,
            )
            encoded = self.encode_game_text(
                prepared,
                entry["table"],
                entry["max"],
            ) if entry.get("terminator") is None else self.encode_terminated_game_text(
                prepared,
                entry,
            )
            self.rom[address:address + entry["max"]] = encoded
        except Exception as exc:
            messagebox.showerror("Game Text", str(exc))
            return

        if not self.path:
            self.save_as()
            return

        self.write_rom(self.path)
        self.loaded_mtime = os.path.getmtime(self.path)
        self.validate_game_text()
        print(f"{category} / {entry['name']}: updated / saved")


           
    def on_attribute_changed(self):

        self.update_palette_hex_output()
        self.update_attr_debug()
        self.validate_name()

    def update_palette_hex_output(self):
        if not hasattr(self, "palette_hex_label"):
            return
        value = self.encode_attributes(
            self.palette_var.get(),
            self.priority_var.get(),
            self.hflip_var.get(),
            self.vflip_var.get()
        )
        self.palette_hex_label.config(text=f"Selected: ${value:02X}")
        
    def refresh_tree_labels(self):

        if not self.rom:
            return
   
    def toggle_topmost(self):

        self.root.attributes(
            "-topmost",
            self.always_on_top.get()
        )

    def validate_banner(self):

        if not self.current_world:
            return

        maxlen = self.profile["world_banners"][
            self.current_world
        ]["max"]

        s = "".join(
            c for c in self.banner_entry.get().upper()
            if c in WORLD_VALID_CHARS
        )[:maxlen]

        if s != self.banner_entry.get():

            pos = self.banner_entry.index(
                tk.INSERT
            )

            self.banner_entry.delete(
                0,
                "end"
            )

            self.banner_entry.insert(
                0,
                s
            )

            self.banner_entry.icursor(
                min(pos,len(s))
            )
        encoded = self.encode_world_banner(s)

        self.hexdebug.set(
            "HEX: " +
            " ".join(
                f"{b:02X}"
                for b in encoded
            )
        )
 
    def save_as(self):

        if not self.rom:
            return

        out = filedialog.asksaveasfilename(
            defaultextension=".nes",
            filetypes=[("NES ROM","*.nes")]
        )

        if not out:
            return

        self.write_rom(out)

        self.path = out

        self.assign_profile_to_project()

        self.add_recent_file(out)

    def add_recent_file(self,path):

        if path in self.recent_files:
            self.recent_files.remove(path)

        self.recent_files.insert(0,path)

        self.recent_files = self.recent_files[:10]

        self.refresh_recent_menu()

        self.save_settings()

    def refresh_recent_menu(self):

        self.recent_menu.delete(0,"end")

        for path in self.recent_files:

            self.recent_menu.add_command(
                label=path,
                command=lambda p=path:
                    self.open_recent(p)
            )

    def open_recent(self, path):

        try:

            self.path = path

            self.rom = bytearray(
                open(path, "rb").read()
            )
            if not self.load_project_profile(path):
                self.path = None
                self.rom = None
                return
            self.update_window_title()
            self.add_recent_file(path)
            self.reload_current_view()

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )
        self.loaded_mtime = os.path.getmtime(self.path)
        self.external_change_detected = False
        self.check_file_changes()

        
    def rom_changed_on_disk(self):

        if not self.path:
            return False

        try:
            current_mtime = os.path.getmtime(self.path)

            return current_mtime != self.loaded_mtime

        except OSError:
            return False
            
    def selected_index(self):

        sel = self.tree.selection()

        if not sel:
            return None

        node = sel[0]

        if node == self.home_node:
            return None
        if node == self.profiles_node:
            return None
        if node == self.level_names_node:
            return None
        if node == self.world_palettes_node:
            return None
        if node == self.game_text_node:
            return None
        if node == self.level_backups_node:
            return None
        if node in self.world_nodes:
            return None
        if node in self.palette_world_nodes:
            return None
        if node in self.game_text_category_nodes:
            return None
        if node in self.game_text_entry_nodes:
            return None

        return self.node_to_index.get(node)
        
    def autosave_timer(self):

        if (
            self.auto_save_changes.get()
            and self.rom
            and self.path
        ):
            try:
                self.save()
            except:
                pass

        self.root.after(
            15000,
            self.autosave_timer
        )
    def save_node(self, node):

        if node in self.world_nodes:
            self.current_world = self.world_node_names[node]
            self.save_world_banner()
            return

        if node in self.palette_world_nodes:
            self.current_world = self.palette_world_nodes[node]
            self.save_palette_world()
            return

        if node in self.game_text_entry_nodes:
            self.current_game_text_id = self.game_text_entry_nodes[node]
            self.save_game_text()
            return

        if node not in self.node_to_index:
            return

        self.save_level(node) 

    def _node_is_in_names_branch(self, node):
        while node:
            if node == self.level_names_node:
                return True
            node = self.tree.parent(node)
        return False

    def apply_profile_tree_access(self):
        installed = self.profile.get("overworld_names_installed", True)
        self.tree.tag_configure("names_disabled", foreground="#888888")

        def update_node(node):
            self.tree.item(node, tags=() if installed else ("names_disabled",))
            for child in self.tree.get_children(node):
                update_node(child)

        update_node(self.level_names_node)
        if not installed:
            self.tree.item(self.level_names_node, open=False)
            selection = self.tree.selection()
            if selection and self._node_is_in_names_branch(selection[0]):
                self.tree.selection_set(self.profiles_node)
                self.tree.focus(self.profiles_node)
        
    def tree_selected(self,event=None):

        sel = self.tree.selection()

        if not sel:
            return

        node = sel[0]
        if (
            not self.profile.get("overworld_names_installed", True)
            and self._node_is_in_names_branch(node)
        ):
            self.tree.selection_set(self.profiles_node)
            self.tree.focus(self.profiles_node)
            return
        self.last_selected_node = node
        
        # HOME clicked in treeview
        if node in (
            self.home_node,
            self.level_names_node,
            self.world_palettes_node,
            self.game_text_node,
        ):
            self.current_mode = "home"
            self._hide_editor_frames()
            self.show_welcome_screen()
            return
            
        # PROFILE clicked in treeview
        if node == self.profiles_node:
            self.current_mode = "profile"
            self._hide_editor_frames()
            self.profile_frame.pack(fill="both", expand=True)
            self.refresh_profile_editor()
            return

        if node == self.level_backups_node:
            self.show_backup_status()
            return

        if node in self.backup_region_nodes:
            self.show_backup_status(self.backup_region_nodes[node])
            return

        if node in self.game_text_category_nodes:
            self.current_mode = "home"
            self._hide_editor_frames()
            self.show_welcome_screen()
            return

        if node in self.game_text_entry_nodes:
            self.show_game_text_editor(self.game_text_entry_nodes[node])
            return
            
        # World X Overview clicked
        if node in self.world_nodes:
            self.show_world_banner_editor(self.world_node_names[node])
            return
                
        # World palette clicked
        if node in self.palette_world_nodes:

            self.current_mode = "palette"
            self.current_world = self.palette_world_nodes[node]

            self.show_palette_editor()

            if self.rom:
                self.load_palette_world()

            return
        # Level clicked
        self.current_mode = "level"
        self.profile_frame.pack_forget()

        if self.rom:
            self.load_level()
        
        
    def open_rom(self):
        p=filedialog.askopenfilename(filetypes=[("NES","*.nes"),("All","*.*")])
        if not p:return
        self.path=p
        self.rom=bytearray(open(p,"rb").read())
        if not self.load_project_profile(p):
            self.path = None
            self.rom = None
            return
        self.update_window_title()
        self.add_recent_file(p)
        self.reload_current_view()
        
        self.loaded_mtime = os.path.getmtime(self.path)
        self.external_change_detected = False
        self.check_file_changes()

    def check_file_changes(self):

        if self.path and not self.external_change_detected:

            try:
                current_mtime = os.path.getmtime(self.path)

                if current_mtime != self.loaded_mtime:

                    self.external_change_detected = True

                    if current_mtime != self.loaded_mtime:

                        self.external_change_detected = True

                        self.update_window_title()
                        self.root.title(
                            self.root.title() + " [OUT OF DATE]"
                        )

                        if self.auto_reload_external.get():

                            self.rom = bytearray(
                                open(self.path, "rb").read()
                            )

                            self.loaded_mtime = os.path.getmtime(
                                self.path
                            )

                            self.external_change_detected = False

                            self.update_window_title()

                            self.initialize_or_restore_profile_rom_data()
                            self.reload_current_view()
                            print(
                                f"ROM reloaded after external modification: "
                                f"{os.path.basename(self.path)}"
                            )
                            
                        else:
                            
                            reload_rom = messagebox.askyesno(
                                "ROM Changed",
                                "The loaded ROM was modified by another program.\n\n"
                                "Would you like to reload it now?"
                            )

                            if reload_rom:

                                try:

                                    self.rom = bytearray(
                                        open(self.path, "rb").read()
                                    )

                                    self.loaded_mtime = os.path.getmtime(
                                        self.path
                                    )

                                    self.external_change_detected = False

                                    self.update_window_title()

                                    self.initialize_or_restore_profile_rom_data()
                                    self.reload_current_view()
                                    print(
                                        f"ROM reloaded after external modification: "
                                        f"{os.path.basename(self.path)}"
                                    )
                                except Exception as e:

                                    messagebox.showerror(
                                        "Reload Failed",
                                        str(e)
                                    )

            except OSError:
                pass

        self.root.after(
            1000,
            self.check_file_changes
        )
        
    def validate_name(self):

        limit = 16

        if (
            getattr(self, "current_mode", "level") == "world"
            and getattr(self, "current_world", None)
        ):
            limit = self.profile["world_banners"][self.current_world]["max"]

        if self.current_mode == "world":
            valid_chars = WORLD_VALID_CHARS
        else:
            valid_chars = VALID_CHARS

        s = "".join(
            c for c in self.name.get().upper()
            if c in valid_chars
        )[:limit]

        if self.name.get() != s:
            self.name.delete(0, "end")
            self.name.insert(0, s)

        if self.current_mode == "world":

            self.preview.config(
                text=s
            )

        else:

            padded = s.ljust(16)

            self.preview.config(
                text=padded[:8] + "\n" + padded[8:16]
            )

        if self.current_mode == "level":

            pal = self.encode_attributes(

                self.palette_var.get(),

                self.priority_var.get(),

                self.hflip_var.get(),

                self.vflip_var.get()

            )

        else:

            pal = 1

        if self.current_mode == "world":
            record = self.encode_world_banner(s)
        else:
            record = self.encode(s)

        self.hexdebug.set(
            "HEX: " +
            " ".join(f"{b:02X}" for b in record)
        )

    def show_palette_editor(self):
        self._hide_editor_frames()
        self.palette_frame.pack(
            fill="both",
            expand=True
        )

    def hide_palette_editor(self):

        self.palette_frame.pack_forget()
        self.mode_label.pack()
        self.name.pack()
        self.preview.pack()
        self.attr_frame.pack()
        
    def update_level_palette_preview(self, world_index):
        base = self.profile["level_name_palette_offset"] + (world_index * 16)

        palette_data = list(
            self.rom[base:base+16]
        )

        for palette_num in range(4):

            start = palette_num * 4

            colors = palette_data[start:start+4]

            for color_num in range(4):

                value = colors[color_num]

                self.palette_swatches[palette_num][color_num].config(
                    bg=NES_RGB.get(value, "#000000")
                )            
    def update_attr_debug(self):

        attr = self.encode_attributes(
            self.palette_var.get(),
            self.priority_var.get(),
            self.hflip_var.get(),
            self.vflip_var.get()
        )

        self.attrinfo.set(
            f"Pal={self.palette_var.get()}  "
            f"P={'Y' if self.priority_var.get() else 'N'}  "
            f"H={'Y' if self.hflip_var.get() else 'N'}  "
            f"V={'Y' if self.vflip_var.get() else 'N'}  "
            f"HEX=${attr:02X}"
        )               
    def load_palette_world(self):
        self.splash_frame.pack_forget()
        world_index = {
            "World 1": 0,
            "World 2": 1,
            "World 3": 2,
            "World 4": 3
        }[self.current_world]

        base = self.profile["level_name_palette_offset"] + (world_index * 16)

        self.current_palette = list(
            self.rom[base:base+16]
        )

        tile_base = (
            self.profile["tile_palette_offset"]
            + (world_index * 16)
        )

        self.current_tile_palette = list(
            self.rom[tile_base:tile_base+16]
        )

        self.refresh_palette_buttons()
        self.apply_feature_controls()
        
    def refresh_palette_buttons(self):

        for i, value in enumerate(self.current_palette):

            bg = NES_RGB.get(value, "#000000")

            fg = "white" if bg.upper() == "#000000" else "black"

            self.palette_buttons[i].config(
                text=f"{value:02X}",
                bg=bg,
                fg=fg,
                activebackground=bg,
                activeforeground=fg
            )
        for i, value in enumerate(
            self.current_tile_palette

        ):

            bg = NES_RGB.get(value, "#000000")

            fg = "white" if bg.upper() == "#000000" else "black"

            self.tile_palette_buttons[i].config(
                text=f"{value:02X}",
                bg=bg,
                fg=fg,
                activebackground=bg,
                activeforeground=fg
            )           
       
    def load_level(self):
        self.world_frame.pack_forget()
        self.splash_frame.pack_forget()
        self.profile_frame.pack_forget()
        self.backups_frame.pack_forget()
        self.game_text_frame.pack_forget()
        self.hide_palette_editor()
        self.mode_label.config(text="Level Name")
        self.tilecombo.config(state="readonly")       
        self.priority_cb.config(state="normal")
        self.hflip_cb.config(state="normal")
        self.vflip_cb.config(state="normal") 
        self.name.config(state="normal")

        if not self.rom:return
        idx=self.selected_index()
        if idx is None:return
        world_name = self.index_to_world[idx]
        world_index = {
            "World 1": 0,
            "World 2": 1,
            "World 3": 2,
            "World 4": 3
        }[world_name]

        self.update_level_palette_preview(world_index)
        
        po=self.profile["full_level_names"]+idx*2

        cpu=self.rom[po] | (self.rom[po+1]<<8)
        if cpu >= self.profile["high_pointer_threshold"]:
            prg = cpu + self.profile["high_pointer_offset"] + self.profile["ines_header"]
        else:     
            prg=cpu + self.profile["pointer_to_rom_offset"] + self.profile["ines_header"]

        rec=self.rom[prg:prg+18]

        self.name.delete(0,"end")
        self.name.insert(0,self.decode(rec[1:17]))

        palette, priority, hflip, vflip = \
            self.decode_attributes(rec[0])

        self.palette_var.set(palette)

        self.priority_var.set(priority)
        self.hflip_var.set(hflip)
        self.vflip_var.set(vflip)

        self.attrinfo.set(
            f"Pal={palette} "
            f"P={'Y' if priority else 'N'} "
            f"H={'Y' if hflip else 'N'} "
            f"V={'Y' if vflip else 'N'}"
        )
        self.validate_name()

        tile=self.rom[self.profile["level_name_tiles"]+idx]
        self.select_map_tile(tile)

        self.cpu.set(f"CPU Pointer: {cpu:04X}")
        self.prg.set(f"PRG Offset: {prg:X}")
        self.tileoff.set(f"Tile Offset: {self.profile['level_name_tiles']+idx:X}")
        self.apply_feature_controls()
        
    def save(self):

        if self.current_mode in ("profile", "backups"):
            return

        if self.current_mode == "palette":

            self.save_palette_world()

        elif self.current_mode == "world":

            self.save_world_banner()

        elif self.current_mode == "game_text":

            self.save_game_text()

        elif self.current_mode == "level":

            self.save_level()

    def save_world_banner(self):
        if (
            not self.rom
            or not self.current_world
            or not self.profile.get("overworld_names_installed", True)
            or not self.profile["features"]["edit_world_banners"]
        ):
            return
        info = self.profile["world_banners"][self.current_world]
        address = info["addr"] + self.profile["ines_header"]
        position = self.banner_position_var.get()
        self.rom[address - 2] = (position >> 8) & 0xFF
        self.rom[address - 1] = position & 0xFF
        text = self.banner_entry.get().upper()[:info["max"]]
        encoded = self.encode_world_banner(text)
        self.rom[address] = len(text)
        self.rom[address + 1:address + 1 + len(encoded)] = encoded
        self.rom[address + 1 + len(encoded)] = 0
        if not self.path:
            self.save_as()
            return
        self.write_rom(self.path)
        self.loaded_mtime = os.path.getmtime(self.path)
        print(f"{self.current_world} / World Banner: updated / saved")

    def save_level(self, node=None):

        features = self.profile["features"]
        if not features["edit_level_names"] and not features["edit_map_tiles"]:
            return

        if self.confirm_before_overwrite.get():

            if not messagebox.askyesno(
                "Confirm Save",
                "Overwrite the current ROM file?"
            ):
                return
        if not self.rom:return
        if node is None:
            idx = self.selected_index()
        else:
            idx = self.node_to_index.get(node)

        if idx is None:
            return
        palette = self.palette_var.get()
        pal = self.encode_attributes(
            self.palette_var.get(),
            self.priority_var.get(),
            self.hflip_var.get(),
            self.vflip_var.get()
        )
        po=self.profile["full_level_names"]+idx*2
        cpu=self.rom[po] | (self.rom[po+1]<<8)
        
        if cpu >= self.profile["high_pointer_threshold"]:
            prg = cpu + self.profile["high_pointer_offset"] + self.profile["ines_header"]
        else:
            prg = cpu + self.profile["pointer_to_rom_offset"] + self.profile["ines_header"]

        if features["edit_level_names"]:
            self.rom[prg]=pal
            self.rom[prg+1:prg+17]=self.encode(self.name.get())
            self.rom[prg+17]=0

        tile = self.selected_map_tile_from_combo()

        if features["edit_map_tiles"] and tile is not None:
            self.rom[self.profile["level_name_tiles"] + idx] = tile

        if not self.path:

            self.save_as()
            return

        self.write_rom(self.path)
        if node is None:
            node = self.tree.selection()[0]

        world_node = self.tree.parent(node)

        world_name = self.tree.item(
            node,
            "text"
        ).replace(" Overview", "")

        level_name = self.tree.item(
            node,
            "text"
        )
        self.loaded_mtime = os.path.getmtime(self.path)
        print(
            f"{level_name}: "
            "updated / saved"
        )       
    def save_palette_world(self):
        if not self.rom:
            return

        features = self.profile["features"]
        if not features["edit_palettes"]:
            return

        world_index = {
            "World 1": 0,
            "World 2": 1,
            "World 3": 2,
            "World 4": 3
        }[self.current_world]

        # Level name palette

        base = self.profile["level_name_palette_offset"] + (world_index * 16)

        if features["edit_palettes"]:
            for i, value in enumerate(self.current_palette):
                self.rom[base + i] = value

        # Tile palette

        tile_base = (
            self.profile["tile_palette_offset"]
            + (world_index * 16)
        )

        if features["edit_palettes"]:
            for i, value in enumerate(self.current_tile_palette):
                self.rom[tile_base + i] = value

        if not self.path:

            self.save_as()
            return

        self.write_rom(self.path)
        self.loaded_mtime = os.path.getmtime(self.path)
        print(
            f"{self.current_world} "
            "/ World Palettes: updated / saved"
        )
