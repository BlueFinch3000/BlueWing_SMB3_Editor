
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil, os
import webbrowser
import sys
from constants import *
from PIL import Image, ImageDraw, ImageTk
import backup_engine
from profiles import DEFAULT_PROFILE, PROFILE_FIELDS, ProfileStore, normalize_profile

import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(BASE_DIR, "icons")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
PROFILES_DIR = os.path.join(BASE_DIR, "Profiles")

from profile_support import ProfileSupportMixin
from rom_editor import RomEditorMixin
from app_dialogs import DialogMixin


class ConsoleMirror:
    def __init__(self, original_stream, app):
        self.original_stream = original_stream
        self.app = app

    def write(self, text):
        self.original_stream.write(text)
        self.app.append_status_output(text)

    def flush(self):
        self.original_stream.flush()

    def isatty(self):
        return self.original_stream.isatty()


class App(ProfileSupportMixin, RomEditorMixin, DialogMixin):
        
    def __init__(self, root):
        self.root=root
        self.rom=None
        self.path=None
        self.current_mode = "level"
        self.current_world = None
        self.debug_window = None
        self.current_palette = [0] * 16
        self.current_tile_palette = [0] * 16
        self.normal_title = root.title()
        self.profile_store = ProfileStore(PROFILES_DIR)
        self.profile_filename = self.profile_store.list_files()[0]
        self.profile = self.profile_store.load(self.profile_filename)
        self.editing_profile_filename = self.profile_filename
        self.editing_profile = self.profile
        self.project_profiles = {}
        self._status_output = ""
        self._console_original_stdout = None
        self._console_original_stderr = None
        

        self.icon_open = tk.PhotoImage(file=os.path.join(ICON_DIR, "Open.png"))
        self.icon_save = tk.PhotoImage(file=os.path.join(ICON_DIR, "Save.png"))
        self.icon_saveas = tk.PhotoImage(file=os.path.join(ICON_DIR, "Save_as.png"))
        self.icon_pin = tk.PhotoImage(file=os.path.join(ICON_DIR, "Pin.png"))
        self.icon_about = tk.PhotoImage(file=os.path.join(ICON_DIR, "Info.png"))
        
        self.palette_nodes = set()
        self.palette_world_nodes = {}
        self.last_selected_node = None
        
        self.recent_files = []
        
        menubar = tk.Menu(root)
        self.menubar = menubar
        root.config(menu=menubar)     

        filemenu = tk.Menu(menubar, tearoff=0)
        self.always_on_top = tk.BooleanVar(value=True)
        self.debug_on_start = tk.BooleanVar(
            value=False
        )        
        self.open_recent_on_start = tk.BooleanVar(
            value=True
        )

        self.auto_reload_external = tk.BooleanVar(
            value=False
        )

        self.auto_save_changes = tk.BooleanVar(
            value=False
        )

        self.confirm_before_overwrite = tk.BooleanVar(
            value=True
        )

        self.collapse_worlds_on_start = tk.BooleanVar(
            value=False
        )
        self.show_status_bar = tk.BooleanVar(
            value=False
        )
        self.load_settings() 
        for var in (
            self.open_recent_on_start,
            self.auto_reload_external,
            self.auto_save_changes,
            self.confirm_before_overwrite,
            self.debug_on_start,
            self.collapse_worlds_on_start,
            self.always_on_top
        ):
            var.trace_add(
                "write",
                lambda *args:
                    self.on_profile_option_changed()
            )
        self.show_status_bar.trace_add(
            "write",
            lambda *args: self.on_status_bar_option_changed()
        )
            
        menubar.add_cascade(label="File", menu=filemenu)

        filemenu.add_command(
            label="Open...",
            command=self.open_rom
        )

        filemenu.add_command(
            label="Save",
            command=self.save
        )

        filemenu.add_command(
            label="Save As...",
            command=self.save_as
        )

        filemenu.add_separator()

        self.recent_menu = tk.Menu(filemenu, tearoff=0)

        filemenu.add_cascade(
            label="Recent Files",
            menu=self.recent_menu
        )
        self.refresh_recent_menu()

        filemenu.add_separator()

        filemenu.add_command(
            label="Exit",
            command=self.close_app
        )
        viewmenu = tk.Menu(menubar, tearoff=0)
        
        optionsmenu = tk.Menu(
            menubar,
            tearoff=0
        )

        menubar.add_cascade(
            label="Options",
            menu=optionsmenu
        )       
        optionsmenu.add_checkbutton(
            label="Open Most Recent on Start",
            variable=self.open_recent_on_start
        )

        optionsmenu.add_checkbutton(
            label="Auto-Reload Externally Modified ROM",
            variable=self.auto_reload_external
        )

        optionsmenu.add_checkbutton(
            label="Auto-Save Changes",
            variable=self.auto_save_changes
        )

        optionsmenu.add_checkbutton(
            label="Confirm Before Overwrite",
            variable=self.confirm_before_overwrite
        )

        optionsmenu.add_checkbutton(
            label="Open Debug Window on Startup",
            variable=self.debug_on_start
        )

        optionsmenu.add_checkbutton(
            label="Collapse World Nodes on Startup",
            variable=self.collapse_worlds_on_start
        )        
        menubar.add_cascade(
            label="View",
            menu=viewmenu
        )
        
        viewmenu.add_checkbutton(
            label="Always on Top",
            variable=self.always_on_top,
            command=self.toggle_topmost
        )
        viewmenu.add_checkbutton(
            label="Console Status Bar",
            variable=self.show_status_bar
        )
        viewmenu.add_command(
            label="Debug Window",
            command=self.show_debug_window
        ) 
        self.backupmenu = tk.Menu(menubar, tearoff=0)

        menubar.add_cascade(
            label="Level Backups",
            menu=self.backupmenu
        )

        # -------------------------
        # Backup By Tileset
        # -------------------------

        self.backup_tileset_menu = tk.Menu(
            self.backupmenu,
            tearoff=0
        )

        self.backupmenu.add_cascade(
            label="Backup by Tileset",
            menu=self.backup_tileset_menu
        )

        self.backupmenu.add_command(
            label="Backup All",
            command=self.do_backup_all
        )

        self.backupmenu.add_separator()

        # -------------------------
        # Restore By Tileset
        # -------------------------

        self.restore_tileset_menu = tk.Menu(
            self.backupmenu,
            tearoff=0
        )

        self.backupmenu.add_cascade(
            label="Restore by Tileset",
            menu=self.restore_tileset_menu
        )

        self.backupmenu.add_command(
            label="Restore All",
            command=self.do_restore_all
        )
        self.refresh_backup_menus()
        
        helpmenu = tk.Menu(menubar, tearoff=0)

        menubar.add_cascade(
            label="Help",
            menu=helpmenu
        )
        helpmenu.add_command(
            label="SMB3 Prime Discord",
            command=lambda: webbrowser.open("https://discord.gg/h9w767s4vc")
        )
        helpmenu.add_command(
            label="Blue Finch's GitHub",
            command=lambda: webbrowser.open("https://github.com/BlueFinch3000")
        )
        helpmenu.add_separator()
        helpmenu.add_command(
            label="Feature Guide",
            command=self.show_feature_guide
        )
        helpmenu.add_command(
            label="About",
            command=self.show_about
        )
        toolbar = ttk.Frame(root)
        toolbar.pack(fill="x")

        ttk.Separator(root, orient="horizontal").pack(fill="x")

        ttk.Button(
            toolbar,
            text="Open",
            image=self.icon_open,
            compound="left",
            command=self.open_rom
        ).pack(side="left", padx=2, pady=2)

        ttk.Button(
            toolbar,
            text="Save",
            image=self.icon_save,
            compound="left",
            command=self.save
        ).pack(side="left", padx=2, pady=2)

        ttk.Button(
            toolbar,
            text="Save As",
            image=self.icon_saveas,
            compound="left",
            command=self.save_as
        ).pack(side="left", padx=2, pady=2)

        ttk.Separator(
            toolbar,
            orient="vertical"
        ).pack(side="left", fill="y", padx=5)
                
        ttk.Checkbutton(
            toolbar,
            text="Always On Top",
            image=self.icon_pin,
            compound="left",
            variable=self.always_on_top,
            command=self.toggle_topmost
        ).pack(
            side="left",
            padx=2,
            pady=2
        )     

        ttk.Button(
            toolbar,
            text="About",
            image=self.icon_about,
            compound="left",
            command=self.show_about
        ).pack(
            side="right",
            padx=2,
            pady=2
        )

        root.bind("<Control-o>",
                  lambda e: self.open_rom())

        root.bind("<Control-s>",
                  lambda e: self.save())

        root.bind("<Control-Shift-S>",
                  lambda e: self.save_as())

        self.status_frame = tk.Frame(
            root,
            bd=1,
            relief="sunken",
            bg="#f0f0f0"
        )
        self.status_text = tk.Text(
            self.status_frame,
            height=2,
            wrap="word",
            state="disabled",
            bg="#f0f0f0",
            relief="flat",
            padx=5,
            pady=2,
            font=("Consolas", 9)
        )
        self.status_text.pack(fill="x")
        self.toggle_status_bar()
        self.install_console_mirror()
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)
                  
        self.main=tk.Frame(root)
        self.main.pack(fill="both",expand=True)

        self.left_frame = tk.Frame(self.main)
        self.left_frame.pack(side="left", fill="y")
        left = self.left_frame

        self.right_frame = tk.Frame(self.main)
        self.right_frame.pack(side="left", fill="both", expand=True)
        right = self.right_frame
        self.splash_frame = tk.Canvas(
            self.right_frame,
            bd=0,
            highlightthickness=0,
            bg=self.root.cget("bg"),
        )
        
        
        self.world_frame = tk.Frame(right)
        self.world_title = tk.Label(
            self.world_frame,
            font=("Segoe UI", 14, "bold")
        )

        self.world_title.pack(pady=(10,5))

        tk.Label(
            self.world_frame,
            text="World Banner",
            font=("Segoe UI", 11, "bold")
        ).pack()
        self.banner_entry = tk.Entry(
            self.world_frame,
            width=24,
            font=("Segoe UI", 14)
        )
        self.banner_entry.pack(pady=(4, 10))
        self.banner_entry.bind("<KeyRelease>", lambda event: self.validate_banner())
        self.banner_position_var = tk.IntVar(value=0x2843)
        banner_position_frame = tk.LabelFrame(
            self.world_frame, text="Banner Position"
        )
        banner_position_frame.pack(pady=(2, 10))
        self.banner_position_buttons = []
        above_border_button = ttk.Radiobutton(
            banner_position_frame,
            text="Above Border",
            variable=self.banner_position_var,
            value=0x2843,
        )
        above_border_button.pack(side="left", padx=8, pady=5)
        on_border_button = ttk.Radiobutton(
            banner_position_frame,
            text="On Border",
            variable=self.banner_position_var,
            value=0x2863,
        )
        on_border_button.pack(side="left", padx=8, pady=5)
        self.banner_position_buttons.extend(
            (above_border_button, on_border_button)
        )

        # ------------------------------------------------------------------
        # HOME Splash Frame
        # ------------------------------------------------------------------        
        img = Image.open(
            os.path.join(
                ICON_DIR,
                "editor_splash.png"
            )
        )
        self.welcome_img = ImageTk.PhotoImage(img)
        self.splash_background = self.splash_frame.create_image(
            0,
            0,
            image=self.welcome_img,
            anchor="w",
        )
        logo = Image.open(os.path.join(ICON_DIR, "BlueWing.png"))
        logo.thumbnail((128, 128), Image.Resampling.LANCZOS)
        self.splash_logo_img = ImageTk.PhotoImage(logo)
        self.splash_logo = self.splash_frame.create_image(
            0,
            0,
            image=self.splash_logo_img,
            anchor="s",
        )

        self.splash_info = tk.Frame(
            self.splash_frame,
            bg="white",
            bd=1,
            relief="ridge"
        )

        tk.Label(
            self.splash_info,
            text=f"{APP_TITLE}",
            font=("Segoe UI", 18, "bold"),
            bg="white"
        ).pack(padx=20, pady=(15,0))

        tk.Label(
            self.splash_info,
            text="A Super Mario Bros. 3 Editor \n by BlueFinch",
            font=("Segoe UI", 11),
            bg="white"
        ).pack(pady=(0,15)) 
        self.splash_info_window = self.splash_frame.create_window(
            0,
            0,
            window=self.splash_info,
            anchor="center",
        )

        def layout_splash(event):
            center_x = event.width // 2
            center_y = event.height // 2
            self.splash_frame.coords(self.splash_background, 0, center_y)
            self.splash_frame.coords(self.splash_info_window, center_x, center_y)
            logo_y = center_y - (self.splash_info.winfo_reqheight() // 2) - 12
            self.splash_frame.coords(self.splash_logo, center_x, logo_y)

        self.splash_frame.bind("<Configure>", layout_splash)
        
        # ------------------------------------------------------------------
        # Palette Editor Frame
        # ------------------------------------------------------------------
        self.palette_frame = tk.Frame(right)
        self.palette_title = tk.Label(
            self.palette_frame,
            text="Sprite / Level Names",
            font=("Segoe UI", 11, "bold")
        )

        self.palette_title.pack(pady=(0,10))

        self.palette_grid = tk.Frame(self.palette_frame)
        self.palette_grid.pack()

        self.palette_buttons = []

        for row in range(4):

            tk.Label(
                self.palette_grid,
                text=f"Palette {row}"
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0,10)
            )

            for col in range(4):

                btn = tk.Button(
                    self.palette_grid,
                    width=3,
                    height=1,
                    font=("Segoe UI", 11),
                    text="00",
                    relief="flat",
                    bd=1,
                    highlightthickness=0,
                    takefocus=False,
                    command=lambda idx=len(self.palette_buttons):
                        self.show_color_picker(idx)
                )

                btn.grid(
                    row=row,
                    column=col+1,
                    padx=1,
                    pady=1
                )

                self.palette_buttons.append(btn) 

        self.tile_palette_title = tk.Label(
            self.palette_frame,
            text="Tiles",
            font=("Segoe UI",11,"bold")
        )

        self.tile_palette_title.pack(
            pady=(15,5)
        )

        self.tile_palette_grid = tk.Frame(
            self.palette_frame
        )

        self.tile_palette_grid.pack()
                
        self.tile_palette_buttons = []

        for row in range(4):

            tk.Label(
                self.tile_palette_grid,
                text=f"Palette {row}"
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0,10)
            )

            for col in range(4):

                btn = tk.Button(
                    self.tile_palette_grid,
                    width=3,
                    height=1,
                    font=("Segoe UI", 11),
                    text="00",
                    relief="flat",
                    bd=1,
                    highlightthickness=0,
                    takefocus=False,
                    command=lambda idx=len(self.tile_palette_buttons):
                        self.show_tile_picker(idx)
                )

                btn.grid(
                    row=row,
                    column=col+1,
                    padx=1,
                    pady=1
                )

                self.tile_palette_buttons.append(btn)

        self.palette_frame.pack_forget()       

        # ------------------------------------------------------------------
        # Level Backups Frame
        # ------------------------------------------------------------------
        self.backups_frame = tk.Frame(right)
        self.backup_screen_title = tk.StringVar(value="Level Backups")
        tk.Label(
            self.backups_frame,
            textvariable=self.backup_screen_title,
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(12, 4))
        self.backup_status_summary = tk.StringVar()
        tk.Label(
            self.backups_frame,
            textvariable=self.backup_status_summary,
            fg="#555555",
        ).pack(pady=(0, 8))
        self.backup_status_rows = tk.Frame(self.backups_frame)
        self.backup_status_rows.pack(fill="x", padx=30)
        backup_actions = tk.Frame(self.backups_frame)
        backup_actions.pack(pady=12)
        self.backup_primary_button = ttk.Button(
            backup_actions,
            text="Backup All",
            command=self.do_backup_all,
        )
        self.backup_primary_button.pack(side="left")
        self.restore_primary_button = ttk.Button(
            backup_actions,
            text="Restore Latest",
            command=self.do_restore_all,
        )
        self.restore_primary_button.pack(side="left", padx=(8, 0))
        self.backup_refresh_button = ttk.Button(
            backup_actions,
            text="Refresh",
            command=self.show_backup_status,
        )
        self.backup_refresh_button.pack(side="left", padx=(8, 0))

        # ------------------------------------------------------------------
        # Game Text Frame
        # ------------------------------------------------------------------
        self.game_text_frame = tk.Frame(right)
        self.game_text_title = tk.StringVar(value="Game Text")
        tk.Label(
            self.game_text_frame,
            textvariable=self.game_text_title,
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(12, 8))
        game_text_settings = tk.Frame(self.game_text_frame)
        game_text_settings.pack(pady=(0, 8))
        tk.Label(game_text_settings, text="Address").grid(
            row=0, column=0, sticky="e", padx=(0, 6), pady=2
        )
        self.game_text_addr_var = tk.StringVar()
        tk.Entry(
            game_text_settings,
            textvariable=self.game_text_addr_var,
            width=14,
        ).grid(row=0, column=1, sticky="w", pady=2)
        tk.Label(game_text_settings, text="Max Length").grid(
            row=0, column=2, sticky="e", padx=(12, 6), pady=2
        )
        self.game_text_max_var = tk.StringVar()
        tk.Entry(
            game_text_settings,
            textvariable=self.game_text_max_var,
            width=8,
        ).grid(row=0, column=3, sticky="w", pady=2)
        tk.Label(game_text_settings, text="Text Table").grid(
            row=1, column=0, sticky="e", padx=(0, 6), pady=2
        )
        self.game_text_table_var = tk.StringVar(value="level")
        self.game_text_table_combo = ttk.Combobox(
            game_text_settings,
            textvariable=self.game_text_table_var,
            state="readonly",
            values=GAME_TEXT_TABLES,
            width=12,
        )
        self.game_text_table_combo.grid(row=1, column=1, sticky="w", pady=2)
        self.game_text_table_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.validate_game_text()
        )
        self.game_text_limit = tk.StringVar(value="No ROM loaded.")
        tk.Label(
            self.game_text_frame,
            textvariable=self.game_text_limit,
            fg="#555555",
        ).pack(pady=(0, 4))
        self.game_text_body = tk.Text(
            self.game_text_frame,
            width=56,
            height=8,
            wrap="word",
            font=("Segoe UI", 11),
        )
        self.game_text_body.pack(padx=20, pady=(0, 8), fill="x")
        self.game_text_body.bind(
            "<KeyRelease>",
            lambda event: self.validate_game_text()
        )
        self.game_text_body.bind("<<Paste>>", self.paste_game_text)
        game_text_actions = tk.Frame(self.game_text_frame)
        game_text_actions.pack(pady=(0, 8))
        ttk.Button(
            game_text_actions,
            text="Save Text",
            command=self.save_game_text,
        ).pack(side="left")
        game_text_hex_frame = tk.Frame(self.game_text_frame)
        game_text_hex_frame.pack(padx=20, fill="x")
        self.game_text_hex = tk.Text(
            game_text_hex_frame,
            width=60,
            height=7,
            wrap="none",
            font=("Consolas", 9),
            fg="#555555",
            relief="flat",
            bg=self.root.cget("bg"),
            takefocus=True,
            insertwidth=0,
        )
        self.game_text_hex_scrollbar = ttk.Scrollbar(
            game_text_hex_frame,
            orient="vertical",
            command=self.game_text_hex.yview,
        )
        self.game_text_hex.configure(yscrollcommand=self.game_text_hex_scrollbar.set)
        self.game_text_hex.bind(
            "<Key>",
            lambda event: (
                None
                if event.state & 0x4 and event.keysym.lower() in ("a", "c")
                else "break"
            )
        )
        self.game_text_hex.bind("<<Paste>>", lambda event: "break")
        self.game_text_hex.pack(side="left", fill="x", expand=True)
        self.game_text_hex_scrollbar.pack(side="right", fill="y")

        # ------------------------------------------------------------------
        # Profile Editor Frame
        # ------------------------------------------------------------------
        self.profile_frame = tk.Frame(right)
        tk.Label(
            self.profile_frame,
            text="Project Profile",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=(10, 5))
        self.profile_notebook = ttk.Notebook(self.profile_frame)
        self.profile_notebook.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.profile_data_tab = tk.Frame(self.profile_notebook)
        self.profile_options_tab = tk.Frame(self.profile_notebook)
        self.profile_backups_tab = tk.Frame(self.profile_notebook)
        self.profile_notebook.add(self.profile_data_tab, text="Data")
        self.profile_notebook.add(self.profile_options_tab, text="Options")
        self.profile_notebook.add(self.profile_backups_tab, text="Backups")
        self.overworld_names_installed_var = tk.BooleanVar(value=True)
        self.overworld_names_installed_check = ttk.Checkbutton(
            self.profile_data_tab,
            text="Overworld Names Engine Installed",
            variable=self.overworld_names_installed_var,
            command=self.apply_profile_data_access
        )
        self.overworld_names_installed_check.pack(pady=(0, 8))

        profile_picker = tk.Frame(self.profile_data_tab)
        profile_picker.pack(fill="x", padx=20, pady=(0, 10))
        self.profile_choice = ttk.Combobox(
            profile_picker,
            state="readonly",
            width=32
        )
        self.profile_choice.pack(side="left", fill="x", expand=True)
        self.profile_choice.bind(
            "<<ComboboxSelected>>",
            lambda event: self.preview_profile(self.profile_choice.get())
        )
        ttk.Button(
            profile_picker,
            text="New",
            width=11,
            command=self.new_profile
        ).pack(side="left", padx=(5, 0))
        ttk.Button(
            profile_picker,
            text="Duplicate",
            width=11,
            command=self.duplicate_profile
        ).pack(side="left", padx=(5, 0))
        ttk.Button(
            profile_picker,
            text="Delete",
            width=11,
            command=self.delete_profile
        ).pack(side="left", padx=(5, 0))

        self.profile_fields_frame = tk.Frame(self.profile_data_tab)
        self.profile_fields_frame.pack(padx=20)
        self.profile_vars = {}
        self.advanced_profile_entries = []
        self.profile_data_widgets = []
        self.advanced_settings_var = tk.BooleanVar(value=False)
        field_labels = {
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
        regular_frame = tk.LabelFrame(
            self.profile_fields_frame,
            text="Data Locations"
        )
        regular_frame.grid(row=0, column=0, sticky="n", padx=(0, 8))
        advanced_frame = tk.LabelFrame(
            self.profile_fields_frame,
            text="Advanced"
        )
        advanced_frame.grid(row=0, column=1, sticky="n")

        for row, field in enumerate(regular_fields):
            tk.Label(
                regular_frame,
                text=field_labels[field]
            ).grid(row=row, column=0, sticky="e", padx=(6, 8), pady=2)
            variable = tk.StringVar()
            self.profile_vars[field] = variable
            entry = tk.Entry(
                regular_frame,
                textvariable=variable,
                width=16
            )
            entry.grid(row=row, column=1, padx=(0, 6), pady=2)
            if field == "name":
                self.profile_name_entry = entry
            else:
                self.profile_data_widgets.append(entry)

        self.advanced_settings_check = ttk.Checkbutton(
            advanced_frame,
            text="Enable for Editing",
            variable=self.advanced_settings_var,
            command=self.toggle_advanced_settings
        )
        self.advanced_settings_check.grid(
            row=0, column=0, columnspan=2, sticky="w", padx=6, pady=(2, 4)
        )
        for row, field in enumerate(advanced_fields, start=1):
            label = tk.Label(advanced_frame, text=field_labels[field])
            label.grid(row=row, column=0, sticky="e", padx=(6, 8), pady=2)
            variable = tk.StringVar()
            self.profile_vars[field] = variable
            entry = tk.Entry(
                advanced_frame,
                textvariable=variable,
                width=16,
                state="disabled"
            )
            entry.grid(row=row, column=1, padx=(0, 6), pady=2)
            self.advanced_profile_entries.append((label, entry))
            self.profile_data_widgets.append(entry)

        banner_frame = tk.LabelFrame(self.profile_data_tab, text="World Banners")
        banner_frame.pack(pady=(8, 0))
        for index, world in enumerate(WORLD_BANNERS):
            label = tk.Label(
                banner_frame,
                text=f"{world} Banner / Max"
            )
            label.grid(row=index, column=0, sticky="e", padx=(6, 8), pady=2)
            pair = tk.Frame(banner_frame)
            pair.grid(row=index, column=1, sticky="w", padx=(0, 6), pady=2)
            addr_var = tk.StringVar()
            max_var = tk.StringVar()
            self.profile_vars[f"banner_{index}_addr"] = addr_var
            self.profile_vars[f"banner_{index}_max"] = max_var
            addr_entry = tk.Entry(pair, textvariable=addr_var, width=15)
            addr_entry.pack(side="left")
            max_entry = tk.Entry(pair, textvariable=max_var, width=7)
            max_entry.pack(side="left", padx=(4, 0))
            self.profile_data_widgets.extend((addr_entry, max_entry))

        profile_actions = tk.Frame(self.profile_data_tab)
        profile_actions.pack(pady=12)
        ttk.Button(
            profile_actions,
            text="Save Profile",
            command=self.save_profile
        ).pack(side="left")
        ttk.Button(
            profile_actions,
            text="Activate",
            command=self.activate_profile
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            profile_actions,
            text="Restore Profile Data to ROM",
            command=self.restore_active_profile_data_to_rom
        ).pack(side="left", padx=(8, 0))
        self.build_profile_settings_tabs(
            self.profile_options_tab,
            self.profile_backups_tab
        )
        self.active_indicator = tk.Frame(self.profile_frame)
        tk.Label(
            self.active_indicator,
            text="\u25cf",
            fg="#20A050",
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")
        tk.Label(
            self.active_indicator,
            text="Active profile",
            font=("Segoe UI", 10)
        ).pack(side="left", padx=(3, 0))
        self.active_indicator.pack()
        self.profile_status = tk.StringVar()
        tk.Label(
            self.profile_frame,
            textvariable=self.profile_status,
            fg="#555555"

        ).pack()
        profile_links_frame = tk.LabelFrame(self.profile_frame, text="Linked ROMs")
        profile_links_frame.pack(fill="x", padx=20, pady=(8, 0))
        self.profile_links_summary = tk.StringVar(value="No linked ROMs.")
        tk.Label(
            profile_links_frame,
            textvariable=self.profile_links_summary,
            fg="#555555",
            anchor="w",
        ).pack(fill="x", padx=8, pady=(5, 2))
        self.profile_links_list = tk.Listbox(
            profile_links_frame,
            height=3,
            exportselection=False,
        )
        self.profile_links_list.pack(fill="x", padx=8, pady=(0, 8))
        self.toggle_advanced_settings()
        self.refresh_profile_editor()
        
        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill="both", expand=True)
        self.tree=ttk.Treeview(tree_frame,show="tree",height=25)
        self.tree.column("#0", width=225, stretch=True)
        self.tree_scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=self.tree_scrollbar.set)
        self.tree.pack(side="left", fill="y", expand=True)
        self.tree_scrollbar.pack(side="right", fill="y")
        self.node_to_index = {}
        self.world_nodes = set()
        self.world_node_names = {}
        self.palette_world_nodes = {}
        self.index_to_world = {}
        self.game_text_category_nodes = {}
        self.game_text_entry_nodes = {}

        idx = 0
        first = None
        self.home_node = self.tree.insert(
            "",
            "end",
            text="\U0001f3e0 Home"
        )
        self.profiles_node = self.tree.insert(
            "",
            "end",
            text="\U0001f464 Project Profiles"
        )
        self.game_text_node = self.tree.insert(
            "",
            "end",
            text="\U0001f4dd Game Text",
            open=True,
        )
        self.refresh_game_text_tree_nodes()
        self.level_names_node = self.tree.insert(
            "",
            "end",
            text="\u2699\ufe0f World / Level Names",
            open=True
        )        
        for world, levels in WORLDS.items():

            wn = self.tree.insert(
                self.level_names_node,
                "end",
                text=f"{world}",
                open=not self.collapse_worlds_on_start.get()
            )

            self.world_nodes.add(wn)
            self.world_node_names[wn] = world

            for level in levels:

                current_idx = idx
                idx += 1

                if level == "NULL":
                    continue

                ln = self.tree.insert(
                    wn,
                    "end",
                    text=level
                )

                self.node_to_index[ln] = current_idx
                self.index_to_world[current_idx] = world

        self.world_palettes_node = self.tree.insert(
            "",
            "end",
            text="\U0001f3a8 World Palettes",
            open=True,
        )
        for world in WORLDS:
            node = self.tree.insert(self.world_palettes_node, "end", text=world)
            self.palette_world_nodes[node] = world

        self.level_backups_node = self.tree.insert(
            "",
            "end",
            text="\U0001f4e6 Level Backups",
        )
        self.backup_region_nodes = {}
        self.refresh_backup_tree_nodes()
                
        self.tree.bind("<Button-1>", self.tree_before_select)
        self.tree.bind("<<TreeviewSelect>>", self.tree_selected)

        self.mode_label = tk.Label(
            right,
            text="Level Name",
            font=("Segoe UI",11,"bold")
        )
        self.mode_label.pack()        
        
        self.name=tk.Entry(right,width=24,font=("Segoe UI", 14))
        self.name.pack()
        self.name.bind("<KeyRelease>",lambda e:self.validate_name())

        self.preview=tk.Label(right,font=("Courier New",12))
        self.preview.pack()

        self.attr_frame = tk.Frame(right)
        self.attr_frame.pack(fill="x", pady=10)

        self.palette_options_frame = tk.Frame(self.attr_frame)
        self.palette_options_frame.pack(
            side="left",
            anchor="n",
            padx=(20, 16)
        )

        self.map_tile_frame = tk.Frame(self.attr_frame)
        self.map_tile_frame.pack(
            side="left",
            anchor="n",
            padx=(8, 20)
        )

        g = self.palette_options_frame

        # ------------------------
        # Palette section
        # ------------------------

        tk.Label(
            g,
            text="Palette",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        self.palette_hex_label = tk.Label(
            g,
            text="Selected: $00",
            font=("Segoe UI", 9)
        )
        self.palette_hex_label.pack(anchor="w", pady=(0, 4))

        self.palette_var = tk.IntVar(value=0)

        self.palette_rows = []
        self.palette_swatches = []

        for i in range(4):

            row = tk.Frame(g)
            row.pack(anchor="w", pady=2)

            rb = tk.Radiobutton(
                row,
                text=f"Palette {i}",
                variable=self.palette_var,
                value=i
            )

            rb.pack(side="left")

            swatches = []

            for _ in range(4):

                box = tk.Label(
                    row,
                    width=2,
                    height=1,
                    bg="black",
                    relief="solid",
                    bd=1
                )

                box.pack(side="left", padx=1)

                swatches.append(box)

            self.palette_swatches.append(swatches)

        # ------------------------
        # Flags
        # ------------------------

        self.priority_var = tk.BooleanVar()
        self.hflip_var = tk.BooleanVar()
        self.vflip_var = tk.BooleanVar()

        self.priority_cb = tk.Checkbutton(
            g,
            text="Behind BG",
            variable=self.priority_var
        )
        self.priority_cb.pack(anchor="w")

        self.hflip_cb = tk.Checkbutton(
            g,
            text="H Flip",
            variable=self.hflip_var
        )
        self.hflip_cb.pack(anchor="w")

        self.vflip_cb = tk.Checkbutton(
            g,
            text="V Flip",
            variable=self.vflip_var
        )
        self.vflip_cb.pack(anchor="w")

        self.palette_var.trace_add("write", lambda *args: self.on_attribute_changed())
        self.priority_var.trace_add("write",lambda *args: self.on_attribute_changed())
        self.hflip_var.trace_add("write", lambda *args: self.on_attribute_changed())
        self.vflip_var.trace_add("write", lambda *args: self.on_attribute_changed())
        
        # Map Tile
        # ------------------------

        tk.Label(
            self.map_tile_frame,
            text="Map Tile Activation",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        self.selected_tile_label = tk.Label(
            self.map_tile_frame,
            text="Selected: --",
            font=("Segoe UI", 9)
        )
        self.selected_tile_label.pack(anchor="w", pady=(0, 4))

        self.map_tile_canvas = tk.Canvas(
            self.map_tile_frame,
            highlightthickness=1,
            highlightbackground="#808080",
            cursor="hand2"
        )
        self.map_tile_canvas.pack(anchor="w")
        self.map_tile_canvas.bind("<Button-1>", self.on_map_tile_canvas_click)

        self.tilecombo = ttk.Combobox(
            self.map_tile_frame,
            state="readonly",
            values=[f"{k:02X} - {v}" for k, v in TILE_NAMES.items()],
            width=30
        )

        self.tilecombo.bind("<<ComboboxSelected>>", lambda e: self.on_attribute_changed())
        self.load_map_tile_grid()

        self.cpu=tk.StringVar()
        self.prg=tk.StringVar()
        self.tileoff=tk.StringVar()
        self.attrinfo=tk.StringVar()
        self.hexdebug = tk.StringVar()
        
        self.tree.selection_set(self.home_node)
        self.tree.focus(self.home_node)
        
        self.mode_label.pack_forget()
        self.name.pack_forget()
        self.preview.pack_forget()
        self.attr_frame.pack_forget()
        self.palette_frame.pack_forget()
        self.profile_frame.pack_forget()
        self.backups_frame.pack_forget()
        self.game_text_frame.pack_forget()
        
        self.show_welcome_screen()        
        self.apply_active_profile_settings()
        self.mode_label.lift()
        self.name.lift()
        self.preview.lift()
        self.attr_frame.lift()
        self.palette_frame.lift()
        self.backups_frame.lift()
        self.game_text_frame.lift()
        
        self.autosave_timer()
        if self.debug_on_start.get():
            self.show_debug_window()    

        if (
            self.open_recent_on_start.get()
            and self.recent_files
        ):
            self.open_recent(self.recent_files[0])
        
    def test_restore(self):

        backup_file = backup_engine.backup_tileset(
            self.path,
            "Fortress",
            self.profile["backup_regions"],
            self.profile["ines_header"],
            self.profile_filename
        )

        backup_engine.restore_tileset(
            self.path,
            "Fortress",
            backup_file,
            self.profile["backup_regions"],
            self.profile["ines_header"]
        )

        print("Restore complete")

    def tree_before_select(self, event):

        target = self.tree.identify_row(event.y)
        if (
            target
            and not self.profile.get("overworld_names_installed", True)
            and self._node_is_in_names_branch(target)
        ):
            return "break"

        if (
            not self.auto_save_changes.get()
            or not self.rom
        ):
            return

        if self.last_selected_node:
            self.save_node(self.last_selected_node)

    def install_console_mirror(self):
        if self._console_original_stdout is not None:
            return
        self._console_original_stdout = sys.stdout
        self._console_original_stderr = sys.stderr
        sys.stdout = ConsoleMirror(self._console_original_stdout, self)
        sys.stderr = ConsoleMirror(self._console_original_stderr, self)

    def restore_console_streams(self):
        if self._console_original_stdout is not None:
            sys.stdout = self._console_original_stdout
            self._console_original_stdout = None
        if self._console_original_stderr is not None:
            sys.stderr = self._console_original_stderr
            self._console_original_stderr = None

    def close_app(self):
        self.restore_console_streams()
        self.root.destroy()

    def on_status_bar_option_changed(self):
        self.toggle_status_bar()
        self.on_profile_option_changed()

    def toggle_status_bar(self):
        if not hasattr(self, "status_frame"):
            return
        if self.show_status_bar.get():
            pack_options = {
                "side": "bottom",
                "fill": "x",
            }
            if hasattr(self, "main"):
                pack_options["before"] = self.main
            self.status_frame.pack(**pack_options)
        else:
            self.status_frame.pack_forget()

    def append_status_output(self, text):
        if (
            not text
            or not hasattr(self, "status_text")
        ):
            return
        self._status_output += text
        if len(self._status_output) > 8000:
            self._status_output = self._status_output[-8000:]
        lines = self._status_output.splitlines()
        if not lines:
            lines = [self._status_output]
        visible_text = "\n".join(lines[-2:])
        self.status_text.config(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.insert("end", visible_text)
        self.status_text.config(state="disabled")

    def tile_cell_bounds(self, tile):
        col = tile % 16
        row = tile // 16
        x0 = col * self.map_tile_cell_width
        y0 = row * self.map_tile_cell_height
        x1 = x0 + self.map_tile_cell_width
        y1 = y0 + self.map_tile_cell_height
        return x0, y0, x1, y1

    def load_map_tile_grid(self):
        self.map_tile_source_img = Image.open(
            os.path.join(ICON_DIR, "MapTiles.png")
        ).convert("RGBA")
        width, height = self.map_tile_source_img.size
        if width != 256 or height != 256:
            raise ValueError("MapTiles.png must be 256x256")
        self.map_tile_cell_width = width // 16
        self.map_tile_cell_height = height // 16
        self.selected_tile_value = None
        self.refresh_map_tile_grid()

    def refresh_map_tile_grid(self):
        if not hasattr(self, "map_tile_source_img"):
            return

        img = self.map_tile_source_img.copy()
        draw = ImageDraw.Draw(img, "RGBA")

        for tile in range(0x100):
            if tile not in TILE_NAMES:
                draw.rectangle(
                    self.tile_cell_bounds(tile),
                    fill=(235, 235, 235, 170)
                )

        if self.selected_tile_value is not None:
            x0, y0, x1, y1 = self.tile_cell_bounds(self.selected_tile_value)
            for inset in range(3):
                draw.rectangle(
                    (x0 + inset, y0 + inset, x1 - inset - 1, y1 - inset - 1),
                    outline=(0, 92, 255, 255)
                )

        self.map_tile_photo = ImageTk.PhotoImage(img)
        width, height = img.size
        self.map_tile_canvas.config(width=width, height=height)
        self.map_tile_canvas.delete("all")
        self.map_tile_canvas.create_image(
            0,
            0,
            image=self.map_tile_photo,
            anchor="nw"
        )

    def select_map_tile(self, tile):
        if tile in TILE_NAMES:
            self.selected_tile_value = tile
            self.tilecombo.set(f"{tile:02X} - {TILE_NAMES[tile]}")
            self.selected_tile_label.config(
                text=f"Selected: {tile:02X} - {TILE_NAMES[tile]}"
            )
        elif isinstance(tile, int) and 0 <= tile <= 0xFF:
            self.selected_tile_value = tile
            self.tilecombo.set("")
            self.selected_tile_label.config(
                text=f"Selected: {tile:02X} - inactive / unnamed"
            )
        else:
            self.selected_tile_value = None
            self.tilecombo.set("")
            self.selected_tile_label.config(text="Selected: --")
        self.refresh_map_tile_grid()

    def selected_map_tile_from_combo(self):
        tile_text = self.tilecombo.get().strip()
        if not tile_text:
            return None
        try:
            return int(tile_text.split()[0], 16)
        except (ValueError, IndexError):
            return None

    def on_map_tile_canvas_click(self, event):
        if (
            not self.profile["features"]["edit_map_tiles"]
            or not hasattr(self, "map_tile_source_img")
        ):
            return
        width, height = self.map_tile_source_img.size
        if not (0 <= event.x < width and 0 <= event.y < height):
            return
        col = event.x // self.map_tile_cell_width
        row = event.y // self.map_tile_cell_height
        tile = row * 16 + col
        if tile not in TILE_NAMES:
            return
        self.select_map_tile(tile)
        self.on_attribute_changed()
        
    def save_settings(self):

        data = {
            "recent_files": self.recent_files,
            "active_profile": self.profile_filename,
            "project_profiles": self.project_profiles,
            "profile_settings_migrated": True
        }

        with open(
            SETTINGS_FILE,
            "w"
        ) as f:

            json.dump(
                data,
                f,
                indent=4
            )



    def load_settings(self):

        if not os.path.exists(
            SETTINGS_FILE
        ):
            return

        try:

            with open(
                SETTINGS_FILE,
                "r"
            ) as f:

                data = json.load(f)
            self.recent_files = data.get(
                "recent_files",
                []
            )            
            self.open_recent_on_start.set(
                data.get(
                    "open_recent_on_start",
                    True
                )
            )

            self.auto_reload_external.set(
                data.get(
                    "auto_reload_external",
                    False
                )
            )

            self.auto_save_changes.set(
                data.get(
                    "auto_save_changes",
                    False
                )
            )

            self.confirm_before_overwrite.set(
                data.get(
                    "confirm_before_overwrite",
                    True
                )
            )

            self.debug_on_start.set(
                data.get(
                    "debug_on_start",
                    False
                )
            )

            self.collapse_worlds_on_start.set(
                data.get(
                    "collapse_worlds_on_start",
                    False
                )
            )
            self.always_on_top.set(
                data.get(
                    "always_on_top",
                    False
                )
            )
            self.project_profiles = data.get("project_profiles", {})
            requested_profile = data.get("active_profile")
            if requested_profile in self.profile_store.list_files():
                self.profile_filename = requested_profile
                self.profile = self.profile_store.load(requested_profile)
                self.editing_profile_filename = self.profile_filename
                self.editing_profile = self.profile
            if not data.get("profile_settings_migrated", False):
                for key in self.profile["options"]:
                    if key in data:
                        self.profile["options"][key] = bool(data[key])
                self.profile_store.save(self.profile, self.profile_filename)
                self.editing_profile = self.profile
            self.apply_active_profile_settings()
        except Exception:
            pass        

    def update_window_title(self):

        title = APP_TITLE

        if self.path:

            rom_name = os.path.basename(self.path)
            title += f" [{self.profile['name']}]: {rom_name}"
        
        self.root.title(title)
