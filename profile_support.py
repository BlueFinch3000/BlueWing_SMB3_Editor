import copy
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from constants import WORLD_BANNERS
from profiles import (
    DEFAULT_PROFILE,
    FEATURE_DEFAULTS,
    OPTION_DEFAULTS,
    PROFILE_FIELDS,
    normalize_profile,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(BASE_DIR, "icons")


class ProfileSupportMixin:
    def on_profile_option_changed(self):
        if not hasattr(self, "profile"):
            return
        if getattr(self, "_suppress_profile_option_updates", False):
            return
        if hasattr(self, "apply_current_game_text_settings"):
            self.apply_current_game_text_settings()
        for key in OPTION_DEFAULTS:
            variable = getattr(self, key, None)
            if variable is not None:
                self.profile["options"][key] = variable.get()
        if self.editing_profile_filename == self.profile_filename:
            self.editing_profile = self.profile
        self.profile_store.save(self.profile, self.profile_filename)
        self.save_settings()
        self.apply_feature_controls()
        print(f"Profile updated: {self.profile_filename}")

    def apply_active_profile_settings(self):
        self._suppress_profile_option_updates = True
        try:
            for key, default in OPTION_DEFAULTS.items():
                variable = getattr(self, key, None)
                if variable is not None:
                    variable.set(self.profile["options"].get(key, default))
        finally:
            self._suppress_profile_option_updates = False
        if hasattr(self, "root"):
            self.root.attributes("-topmost", self.always_on_top.get())
        self.apply_feature_controls()
        if hasattr(self, "tree"):
            self.apply_profile_tree_access()
            self.refresh_game_text_tree_nodes()
        self.refresh_backup_menus()

    def apply_feature_controls(self):
        if not hasattr(self, "name"):
            return
        features = self.profile["features"]
        level_state = "normal" if features["edit_level_names"] else "disabled"
        map_state = "readonly" if features["edit_map_tiles"] else "disabled"
        banner_state = "normal" if features["edit_world_banners"] else "disabled"
        palette_state = "normal" if features["edit_palettes"] else "disabled"
        self.name.config(state=level_state)
        for widget in (self.priority_cb, self.hflip_cb, self.vflip_cb):
            widget.config(state=level_state)
        self.tilecombo.config(state=map_state)
        if hasattr(self, "map_tile_canvas"):
            self.map_tile_canvas.config(
                cursor="hand2" if features["edit_map_tiles"] else ""
            )
        if hasattr(self, "selected_tile_label"):
            self.selected_tile_label.config(
                fg="SystemWindowText" if features["edit_map_tiles"] else "SystemGrayText"
            )
        self.banner_entry.config(state=banner_state)
        for button in getattr(self, "banner_position_buttons", ()):
            button.config(state=banner_state)
        for button in self.palette_buttons + self.tile_palette_buttons:
            button.config(state=palette_state)

    def profile_for_project(self, path):
        if not path:
            return None
        key = os.path.normcase(os.path.abspath(path))
        return self.project_profiles.get(key)

    def linked_rom_paths_for_profile(self, filename):
        links = []
        for path_key, profile_filename in self.project_profiles.items():
            if profile_filename != filename:
                continue
            display_path = next(
                (
                    recent_path for recent_path in self.recent_files
                    if os.path.normcase(os.path.abspath(recent_path)) == path_key
                ),
                path_key,
            )
            links.append(display_path)
        return sorted(links, key=str.casefold)

    def refresh_profile_links_editor(self):
        if not hasattr(self, "profile_links_list"):
            return
        self.profile_links_list.delete(0, "end")
        links = self.linked_rom_paths_for_profile(self.editing_profile_filename)
        if links:
            for path in links:
                marker = " (current)" if self.path and (
                    os.path.normcase(os.path.abspath(path))
                    == os.path.normcase(os.path.abspath(self.path))
                ) else ""
                self.profile_links_list.insert("end", path + marker)
            self.profile_links_summary.set(
                f"{len(links)} ROM link{'s' if len(links) != 1 else ''} for this profile."
            )
        else:
            self.profile_links_list.insert("end", "No ROMs linked to this profile.")
            self.profile_links_summary.set("No linked ROMs.")

    def ask_profile_for_unpaired_rom(self, path):
        dialog = tk.Toplevel(self.root)
        dialog.title("Pair ROM With Profile")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        try:
            dialog.iconbitmap(os.path.join(ICON_DIR, "BlueWing.ico"))
        except tk.TclError:
            pass

        selected = {"filename": None}
        tk.Label(
            dialog,
            text="Pair ROM With Profile",
            font=("Segoe UI", 14, "bold"),
        ).pack(padx=18, pady=(14, 6))
        tk.Message(
            dialog,
            text=(
                f"{os.path.basename(path)} is not linked to a Blue Wing profile. "
                "Choose the profile whose offsets and editor settings should be used. "
                "Opening will read data from this ROM into that profile; it will not "
                "restore saved profile data into the ROM."
            ),
            width=420,
        ).pack(padx=18, pady=(0, 10))

        choice = tk.StringVar(value=self.profile_filename)
        combo = ttk.Combobox(
            dialog,
            textvariable=choice,
            values=self.profile_store.list_files(),
            state="readonly",
            width=38,
        )
        combo.pack(padx=18, pady=(0, 12), fill="x")

        buttons = tk.Frame(dialog)
        buttons.pack(pady=(0, 14))

        def use_profile():
            selected["filename"] = choice.get()
            dialog.destroy()

        def create_profile():
            suggested = os.path.splitext(os.path.basename(path))[0] or "Profile"
            name = simpledialog.askstring(
                "Create Profile",
                "Profile name:",
                initialvalue=suggested,
                parent=dialog,
            )
            if not name or not name.strip():
                return
            profile = copy.deepcopy(DEFAULT_PROFILE)
            profile["name"] = name.strip()
            try:
                filename = self.profile_store.safe_filename(profile["name"])
                if filename in self.profile_store.list_files():
                    raise ValueError(f"{filename} already exists")
                self.profile_store.save(profile, filename)
                selected["filename"] = filename
                dialog.destroy()
            except Exception as exc:
                messagebox.showerror("Create Profile", str(exc), parent=dialog)

        def cancel():
            dialog.destroy()

        ttk.Button(buttons, text="Pair and Open", command=use_profile).pack(side="left")
        ttk.Button(buttons, text="Create New Profile", command=create_profile).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(buttons, text="Cancel", command=cancel).pack(side="left", padx=(8, 0))
        dialog.bind("<Return>", lambda event: use_profile())
        dialog.bind("<Escape>", lambda event: cancel())
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        dialog.attributes("-topmost", True)
        dialog.lift(self.root)
        dialog.focus_force()
        dialog.wait_window()
        return selected["filename"]

    def toggle_advanced_settings(self):
        engine_installed = self.overworld_names_installed_var.get()
        enabled = engine_installed and self.advanced_settings_var.get()
        for label, entry in self.advanced_profile_entries:
            entry.config(state="normal" if enabled else "disabled")
            label.config(fg="SystemWindowText" if enabled else "SystemGrayText")

    def apply_profile_data_access(self):
        if not hasattr(self, "profile_data_widgets"):
            return
        engine_installed = self.overworld_names_installed_var.get()
        state = "normal" if engine_installed else "disabled"
        for widget in self.profile_data_widgets:
            widget.config(state=state)
        self.overworld_names_installed_check.config(state=state)
        self.advanced_settings_check.config(state=state)
        self.toggle_advanced_settings()

    def assign_profile_to_project(self):
        if self.path:
            key = os.path.normcase(os.path.abspath(self.path))
            self.project_profiles[key] = self.profile_filename
            self.refresh_profile_links_editor()

    def load_project_profile(self, path):
        previous_filename = self.profile_filename
        filename = self.profile_for_project(path)
        if filename not in self.profile_store.list_files():
            filename = self.ask_profile_for_unpaired_rom(path)
            if not filename:
                return False
            key = os.path.normcase(os.path.abspath(path))
            self.project_profiles[key] = filename
        if filename in self.profile_store.list_files():
            self.profile_filename = filename
            self.profile = self.profile_store.load(filename)
        self.editing_profile_filename = self.profile_filename
        self.editing_profile = self.profile
        self.initialize_profile_rom_data_for_opened_rom()
        self.assign_profile_to_project()
        self.apply_active_profile_settings()
        if hasattr(self, "profile_choice"):
            self.refresh_profile_editor()
        self.save_settings()
        if self.profile_filename != previous_filename:
            print(
                f"Profile changed: {previous_filename} -> {self.profile_filename}"
            )
        return True

    def refresh_profile_editor(self):
        files = self.profile_store.list_files()
        self.profile_choice["values"] = files
        self.profile_choice.set(self.editing_profile_filename)
        self.overworld_names_installed_var.set(
            self.editing_profile.get("overworld_names_installed", True)
        )
        for field in ("name",) + PROFILE_FIELDS:
            value = self.editing_profile[field]
            self.profile_vars[field].set(
                value if field == "name" else f"0x{value:X}"
            )
        for index, world in enumerate(WORLD_BANNERS):
            info = self.editing_profile["world_banners"][world]
            self.profile_vars[f"banner_{index}_addr"].set(f"0x{info['addr']:X}")
            self.profile_vars[f"banner_{index}_max"].set(str(info["max"]))
        if self.editing_profile_filename == self.profile_filename:
            self.active_indicator.pack()
            project_text = os.path.basename(self.path) if self.path else "new projects"
            self.profile_status.set(f"Used by {project_text}.")
        else:
            self.active_indicator.pack_forget()
            self.profile_status.set(
                f"Viewing {self.editing_profile_filename}. Click Activate to use it."
            )
        self.apply_profile_data_access()
        self.refresh_profile_settings_editor()
        self.refresh_profile_links_editor()

    def profile_from_editor(self):
        options = copy.deepcopy(self.editing_profile["options"])
        if hasattr(self, "profile_option_vars"):
            options = {
                key: variable.get()
                for key, variable in self.profile_option_vars.items()
            }
        features = copy.deepcopy(self.editing_profile["features"])
        if hasattr(self, "profile_feature_vars"):
            features = {
                key: variable.get()
                for key, variable in self.profile_feature_vars.items()
            }
        backup_regions = copy.deepcopy(self.editing_profile["backup_regions"])
        if hasattr(self, "profile_backup_regions"):
            self.apply_profile_backup_region()
            backup_regions = copy.deepcopy(self.profile_backup_regions)
        data = {
            "name": self.profile_vars["name"].get().strip(),
            "overworld_names_installed": self.overworld_names_installed_var.get(),
            "world_banners": {},
            "options": options,
            "features": features,
            "backup_regions": backup_regions,
            "game_texts": copy.deepcopy(self.editing_profile["game_texts"]),
            "rom_data": copy.deepcopy(self.editing_profile.get("rom_data")),
        }
        for field in PROFILE_FIELDS:
            data[field] = self.profile_vars[field].get().strip()
        for index, world in enumerate(WORLD_BANNERS):
            data["world_banners"][world] = {
                "addr": self.profile_vars[f"banner_{index}_addr"].get().strip(),
                "max": self.profile_vars[f"banner_{index}_max"].get().strip(),
            }
        return normalize_profile(data)

    def preview_profile(self, filename):
        try:
            self.editing_profile = self.profile_store.load(filename)
            self.editing_profile_filename = filename
            self.refresh_profile_editor()
            print(f"Profile changed: viewing {filename}")
        except Exception as exc:
            messagebox.showerror("Profile Error", str(exc))

    def build_profile_settings_tabs(self, options_tab, backups_tab):
        option_labels = {
            "open_recent_on_start": "Open most recent ROM on startup",
            "auto_reload_external": "Auto-reload externally modified ROM",
            "auto_save_changes": "Auto-save changes",
            "confirm_before_overwrite": "Confirm before overwrite",
            "debug_on_start": "Open debug window on startup",
            "collapse_worlds_on_start": "Collapse world nodes on startup",
            "always_on_top": "Keep application always on top",
            "show_status_bar": "Show console status bar",
        }
        feature_labels = {
            "edit_level_names": "Level-name and attribute editing",
            "edit_world_banners": "World-banner editing",
            "edit_palettes": "Palette editing",
            "edit_map_tiles": "Map-tile activation editing",
            "level_backups": "Level backup and restore tools",
        }
        self.profile_option_vars = {}
        self.profile_feature_vars = {}
        options_frame = tk.LabelFrame(options_tab, text="Program Options")
        options_frame.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)
        features_frame = tk.LabelFrame(options_tab, text="Enabled Features")
        features_frame.pack(side="left", fill="both", expand=True, padx=(5, 10), pady=10)
        for key, label in option_labels.items():
            variable = tk.BooleanVar(value=self.editing_profile["options"][key])
            self.profile_option_vars[key] = variable
            ttk.Checkbutton(options_frame, text=label, variable=variable).pack(
                anchor="w", padx=8, pady=4
            )
        for key, label in feature_labels.items():
            variable = tk.BooleanVar(value=self.editing_profile["features"][key])
            self.profile_feature_vars[key] = variable
            ttk.Checkbutton(features_frame, text=label, variable=variable).pack(
                anchor="w", padx=8, pady=4
            )

        self.profile_backup_regions = copy.deepcopy(
            self.editing_profile["backup_regions"]
        )
        self.profile_backup_list = tk.Listbox(
            backups_tab, width=24, exportselection=False
        )
        self.profile_backup_list.pack(
            side="left", fill="y", padx=(10, 5), pady=10
        )
        editor = tk.LabelFrame(backups_tab, text="Selected Region")
        editor.pack(side="left", fill="both", expand=True, padx=(5, 10), pady=10)
        self.profile_backup_vars = {
            "name": tk.StringVar(),
            "bank": tk.StringVar(),
            "start": tk.StringVar(),
            "end": tk.StringVar(),
        }
        for row, (key, label) in enumerate((
            ("name", "Name"),
            ("bank", "Bank"),
            ("start", "CPU Start"),
            ("end", "CPU End"),
        )):
            tk.Label(editor, text=label).grid(
                row=row, column=0, sticky="e", padx=(10, 6), pady=5
            )
            tk.Entry(
                editor,
                textvariable=self.profile_backup_vars[key],
                width=24
            ).grid(row=row, column=1, sticky="w", padx=(0, 10), pady=5)

        self.current_profile_backup_region = None
        self.profile_backup_list.bind(
            "<<ListboxSelect>>",
            lambda event: self.load_profile_backup_region()
        )
        region_buttons = tk.Frame(editor)
        region_buttons.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(
            region_buttons,
            text="Apply Region",
            command=self.safe_apply_profile_backup_region
        ).pack(side="left")
        ttk.Button(
            region_buttons,
            text="Add",
            command=self.add_profile_backup_region
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            region_buttons,
            text="Remove",
            command=self.remove_profile_backup_region
        ).pack(side="left", padx=(6, 0))
        self.refresh_profile_backup_list()

    def refresh_profile_settings_editor(self):
        if not hasattr(self, "profile_option_vars"):
            return
        for key, variable in self.profile_option_vars.items():
            variable.set(self.editing_profile["options"][key])
        for key, variable in self.profile_feature_vars.items():
            variable.set(self.editing_profile["features"][key])
        self.profile_backup_regions = copy.deepcopy(
            self.editing_profile["backup_regions"]
        )
        self.current_profile_backup_region = None
        self.refresh_profile_backup_list()

    def refresh_profile_backup_list(self, select_name=None):
        if not hasattr(self, "profile_backup_list"):
            return
        self.profile_backup_list.delete(0, "end")
        names = list(self.profile_backup_regions)
        for name in names:
            self.profile_backup_list.insert("end", name)
        if names:
            index = names.index(select_name) if select_name in names else 0
            self.profile_backup_list.selection_set(index)
            self.load_profile_backup_region()
        else:
            for variable in self.profile_backup_vars.values():
                variable.set("")

    def load_profile_backup_region(self):
        selection = self.profile_backup_list.curselection()
        if not selection:
            return
        name = self.profile_backup_list.get(selection[0])
        info = self.profile_backup_regions[name]
        self.current_profile_backup_region = name
        self.profile_backup_vars["name"].set(name)
        self.profile_backup_vars["bank"].set(f"0x{info['bank']:X}")
        self.profile_backup_vars["start"].set(f"0x{info['start']:X}")
        self.profile_backup_vars["end"].set(f"0x{info['end']:X}")

    def apply_profile_backup_region(self):
        old_name = getattr(self, "current_profile_backup_region", None)
        if not old_name:
            return
        name = self.profile_backup_vars["name"].get().strip()
        if not name:
            raise ValueError("Backup region name cannot be empty")
        info = {
            "bank": int(self.profile_backup_vars["bank"].get().strip(), 0),
            "start": int(self.profile_backup_vars["start"].get().strip(), 0),
            "end": int(self.profile_backup_vars["end"].get().strip(), 0),
        }
        if info["bank"] < 0 or info["start"] < 0 or info["end"] < info["start"]:
            raise ValueError("Invalid backup bank or address range")
        if name != old_name and name in self.profile_backup_regions:
            raise ValueError(f"A backup region named {name} already exists")
        items = list(self.profile_backup_regions.items())
        self.profile_backup_regions.clear()
        for item_name, item_info in items:
            if item_name == old_name:
                self.profile_backup_regions[name] = info
            else:
                self.profile_backup_regions[item_name] = item_info
        self.current_profile_backup_region = name
        self.refresh_profile_backup_list(name)

    def safe_apply_profile_backup_region(self):
        try:
            self.apply_profile_backup_region()
        except Exception as exc:
            messagebox.showerror("Backup Region", str(exc))

    def add_profile_backup_region(self):
        name = simpledialog.askstring(
            "Add Backup Region", "Region name:", parent=self.root
        )
        if not name or not name.strip():
            return
        name = name.strip()
        if name in self.profile_backup_regions:
            messagebox.showerror("Backup Region", "That region already exists.")
            return
        self.profile_backup_regions[name] = {"bank": 0, "start": 0x8000, "end": 0x8000}
        self.refresh_profile_backup_list(name)

    def remove_profile_backup_region(self):
        name = getattr(self, "current_profile_backup_region", None)
        if not name:
            return
        if len(self.profile_backup_regions) <= 1:
            messagebox.showerror("Backup Region", "At least one region must remain.")
            return
        del self.profile_backup_regions[name]
        self.current_profile_backup_region = None
        self.refresh_profile_backup_list()

    def activate_profile(self):
        try:
            self.profile = self.profile_from_editor()
            self.profile_store.save(
                self.profile,
                self.editing_profile_filename
            )
            self.profile_filename = self.editing_profile_filename
            self.editing_profile = self.profile
            self.initialize_profile_rom_data_for_opened_rom()
            self.assign_profile_to_project()
            self.apply_active_profile_settings()
            self.refresh_profile_editor()
            self.save_settings()
            self.update_window_title()
            self.reload_current_view()
            print(f"Profile activated: {self.profile_filename}")
        except Exception as exc:
            messagebox.showerror("Activate Profile", str(exc))

    def restore_active_profile_data_to_rom(self):
        if not self.rom:
            messagebox.showinfo("Restore Profile Data", "Load a ROM first.")
            return
        if not self.profile.get("rom_data"):
            messagebox.showinfo(
                "Restore Profile Data",
                "This profile does not have saved ROM data to restore.",
            )
            return
        if not messagebox.askyesno(
            "Restore Profile Data",
            "Write the active profile's saved ROM data into the currently loaded ROM?\n\n"
            "This is intentionally separate from opening a ROM.",
        ):
            return
        try:
            self.restore_profile_rom_data(self.profile)
            if self.path:
                self.write_rom(self.path)
                self.loaded_mtime = os.path.getmtime(self.path)
            self.reload_current_view()
            print(f"Profile ROM data restored: {self.profile_filename}")
        except Exception as exc:
            messagebox.showerror("Restore Profile Data", str(exc))

    def new_profile(self):
        self.open_profile_dialog(
            "New Profile",
            DEFAULT_PROFILE,
            ask_engine_installed=True,
            show_data_fields=True
        )

    def duplicate_profile(self):
        try:
            source = self.profile_from_editor()
            self.open_profile_dialog(
                "Duplicate Profile",
                source,
                suggested_name=f"{source['name']} Copy",
                ask_engine_installed=False,
                show_data_fields=False
            )
        except Exception as exc:
            messagebox.showerror("Duplicate Profile", str(exc))

    def open_profile_dialog(
        self,
        title,
        source,
        suggested_name=None,
        ask_engine_installed=False,
        show_data_fields=True
    ):
        source = normalize_profile(source)
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        try:
            dialog.iconbitmap(os.path.join(ICON_DIR, "BlueWing.ico"))
        except tk.TclError:
            pass

        tk.Label(
            dialog,
            text=title,
            font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=0, columnspan=4, pady=(12, 10))

        variables = {}
        name_var = tk.StringVar(value=suggested_name or source["name"])
        tk.Label(dialog, text="Profile Name").grid(
            row=1, column=0, sticky="e", padx=(12, 6), pady=3
        )
        tk.Entry(dialog, textvariable=name_var, width=28).grid(
            row=1, column=1, columnspan=3, sticky="w", padx=(0, 12), pady=3
        )
        variables["name"] = name_var
        dialog_engine_installed = tk.BooleanVar(
            value=source.get("overworld_names_installed", True)
        )
        if ask_engine_installed:
            ttk.Checkbutton(
                dialog,
                text="Overworld Names Engine Installed",
                variable=dialog_engine_installed,
                command=lambda: toggle_dialog_data_access()
            ).grid(
                row=2,
                column=0,
                columnspan=4,
                sticky="w",
                padx=12,
                pady=(4, 8)
            )
        labels = {
            "name": "Profile Name",
            "ines_header": "iNES Header",
            "full_level_names": "Level Pointer Table",
            "level_name_tiles": "Level Map Tiles",
            "pointer_to_rom_offset": "Pointer to ROM Offset",
            "high_pointer_threshold": "High Pointer Threshold",
            "high_pointer_offset": "High Pointer Offset",
            "level_name_palette_offset": "Level Name Palettes",
            "tile_palette_offset": "Tile Palettes",
        }
        regular_fields = (
            "name",
            "full_level_names",
            "level_name_tiles",
            "level_name_palette_offset",
            "tile_palette_offset",
        )
        advanced_fields = (
            "ines_header",
            "pointer_to_rom_offset",
            "high_pointer_threshold",
            "high_pointer_offset",
        )
        data_widgets = []
        regular_frame = tk.LabelFrame(dialog, text="Data Locations")
        advanced_frame = tk.LabelFrame(dialog, text="Advanced")
        banner_frame = tk.LabelFrame(dialog, text="World Banners")
        if show_data_fields:
            regular_frame.grid(
                row=3, column=0, columnspan=2, sticky="n", padx=(12, 6)
            )
            advanced_frame.grid(
                row=3, column=2, columnspan=2, sticky="n", padx=(6, 12)
            )
            banner_frame.grid(
                row=4,
                column=0,
                columnspan=4,
                padx=12,
                pady=(10, 5),
                sticky="ew"
            )

        for row, field in enumerate(regular_fields[1:]):
            tk.Label(regular_frame, text=labels[field]).grid(
                row=row,
                column=0,
                sticky="e",
                padx=(6, 6),
                pady=3
            )
            value = source[field]
            if field == "name":
                value = suggested_name or value
            else:
                value = f"0x{value:X}"
            variable = tk.StringVar(value=value)
            variables[field] = variable
            entry = tk.Entry(regular_frame, textvariable=variable, width=18)
            entry.grid(
                row=row,
                column=1,
                padx=(0, 6),
                pady=3
            )
            data_widgets.append(entry)

        advanced_enabled = tk.BooleanVar(value=False)
        advanced_widgets = []

        def toggle_dialog_advanced():
            enabled = (
                (not ask_engine_installed or dialog_engine_installed.get())
                and advanced_enabled.get()
            )
            for label, entry in advanced_widgets:
                entry.config(state="normal" if enabled else "disabled")
                label.config(fg="SystemWindowText" if enabled else "SystemGrayText")

        def toggle_dialog_data_access():
            enabled = not ask_engine_installed or dialog_engine_installed.get()
            for widget in data_widgets:
                widget.config(state="normal" if enabled else "disabled")
            advanced_check.config(state="normal" if enabled else "disabled")
            toggle_dialog_advanced()

        advanced_check = ttk.Checkbutton(
            advanced_frame,
            text="Enable for Editing",
            variable=advanced_enabled,
            command=toggle_dialog_advanced
        )
        advanced_check.grid(
            row=0, column=0, columnspan=2, sticky="w", padx=6, pady=(2, 4)
        )
        for row, field in enumerate(advanced_fields, start=1):
            label = tk.Label(advanced_frame, text=labels[field])
            label.grid(row=row, column=0, sticky="e", padx=(6, 6), pady=3)
            variable = tk.StringVar(value=f"0x{source[field]:X}")
            variables[field] = variable
            entry = tk.Entry(
                advanced_frame,
                textvariable=variable,
                width=18,
                state="disabled"
            )
            entry.grid(row=row, column=1, padx=(0, 6), pady=3)
            advanced_widgets.append((label, entry))
            data_widgets.append(entry)
        toggle_dialog_advanced()

        for index, world in enumerate(WORLD_BANNERS):
            info = source["world_banners"][world]
            tk.Label(banner_frame, text=world).grid(
                row=index,
                column=0,
                sticky="e",
                padx=(8, 6),
                pady=3
            )
            addr_var = tk.StringVar(value=f"0x{info['addr']:X}")
            max_var = tk.StringVar(value=str(info["max"]))
            variables[f"banner_{index}_addr"] = addr_var
            variables[f"banner_{index}_max"] = max_var
            addr_entry = tk.Entry(banner_frame, textvariable=addr_var, width=18)
            addr_entry.grid(row=index, column=1, pady=3)
            data_widgets.append(addr_entry)
            tk.Label(banner_frame, text="Max length").grid(
                row=index, column=2, padx=(12, 6), pady=3
            )
            max_entry = tk.Entry(banner_frame, textvariable=max_var, width=8)
            max_entry.grid(row=index, column=3, padx=(0, 8), pady=3)
            data_widgets.append(max_entry)

        def create_profile():
            try:
                data = {
                    "name": variables["name"].get().strip(),
                    "overworld_names_installed": (
                        dialog_engine_installed.get()
                        if ask_engine_installed
                        else source.get("overworld_names_installed", True)
                    ),
                    "world_banners": {},
                    "options": copy.deepcopy(source["options"]),
                    "features": copy.deepcopy(source["features"]),
                    "backup_regions": copy.deepcopy(source["backup_regions"]),
                    "game_texts": copy.deepcopy(source["game_texts"]),
                }
                for field in PROFILE_FIELDS:
                    data[field] = variables[field].get().strip()
                for index, world in enumerate(WORLD_BANNERS):
                    data["world_banners"][world] = {
                        "addr": variables[f"banner_{index}_addr"].get().strip(),
                        "max": variables[f"banner_{index}_max"].get().strip(),
                    }
                profile = normalize_profile(data)
                filename = self.profile_store.safe_filename(profile["name"])
                if filename in self.profile_store.list_files():
                    raise ValueError(f"{filename} already exists")
                self.profile_store.save(profile, filename)
                self.editing_profile_filename = filename
                self.editing_profile = profile
                self.refresh_profile_editor()
                self.save_settings()
                dialog.destroy()
                action = "duplicated" if title == "Duplicate Profile" else "created"
                print(f"Profile {action}: {filename}")
            except Exception as exc:
                messagebox.showerror("Invalid Profile", str(exc), parent=dialog)

        buttons = tk.Frame(dialog)
        buttons.grid(
            row=5 if show_data_fields else 3,
            column=0,
            columnspan=4,
            pady=(8, 12)
        )
        ttk.Button(buttons, text="Create", command=create_profile).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(
            side="left", padx=(8, 0)
        )
        toggle_dialog_data_access()
        dialog.bind("<Return>", lambda event: create_profile())
        dialog.bind("<Escape>", lambda event: dialog.destroy())
        dialog.wait_window()

    def save_profile(self):
        try:
            self.editing_profile = self.profile_from_editor()
            self.profile_store.save(
                self.editing_profile,
                self.editing_profile_filename
            )
            if self.editing_profile_filename == self.profile_filename:
                self.profile = self.editing_profile
                self.assign_profile_to_project()
                self.apply_active_profile_settings()
            self.refresh_profile_editor()
            self.save_settings()
            self.update_window_title()
            self.reload_current_view()
            self.profile_status.set(f"Saved {self.editing_profile_filename}.")
            print(f"Profile updated: {self.editing_profile_filename}")
        except Exception as exc:
            messagebox.showerror("Invalid Profile", str(exc))

    def delete_profile(self):
        if self.editing_profile_filename == self.profile_filename:
            messagebox.showinfo(
                "Active Profile",
                "Activate another profile before deleting this one."
            )
            return
        if not messagebox.askyesno(
            "Delete Profile",
            f"Delete {self.editing_profile_filename}?"
        ):
            return
        try:
            deleted = self.editing_profile_filename
            self.profile_store.delete(deleted)
            for path, filename in list(self.project_profiles.items()):
                if filename == deleted:
                    del self.project_profiles[path]
            self.editing_profile_filename = self.profile_filename
            self.editing_profile = self.profile
            self.refresh_profile_editor()
            self.save_settings()
            print(f"Profile deleted: {deleted}")
        except Exception as exc:
            messagebox.showerror("Delete Profile", str(exc))

    def reload_current_view(self):
        if self.current_mode == "profile":
            self.refresh_profile_editor()
            return
        if not self.rom:
            return
        if self.current_mode == "palette":
            self.load_palette_world()
        elif self.current_mode == "world" and self.current_world:
            self.show_world_banner_editor(self.current_world)
        elif self.current_mode == "backups":
            self.show_backup_status(getattr(self, "current_backup_region", None))
        elif self.current_mode == "game_text":
            self.load_game_text()
        elif self.current_mode == "level":
            self.load_level()
