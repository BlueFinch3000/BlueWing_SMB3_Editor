import os
import tkinter as tk
from tkinter import ttk

from constants import *


class DialogMixin:
    def apply_bluewing_icon(self, win):
        try:
            win.iconbitmap(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "icons",
                    "BlueWing.ico",
                )
            )
        except tk.TclError:
            pass

    def finish_color_picker(self, win):
        self.apply_bluewing_icon(win)
        win.resizable(False, False)
        win.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{max(0, x)}+{max(0, y)}")

    def finish_dialog(self, win):
        self.apply_bluewing_icon(win)
        win.transient(self.root)
        win.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{max(0, x)}+{max(0, y)}")
        win.attributes("-topmost", True)
        win.lift(self.root)
        win.focus_force()

    def show_debug_window(self):

        if (
            self.debug_window
            and self.debug_window.winfo_exists()
        ):
            self.debug_window.lift()
            return

        self.debug_window = tk.Toplevel(self.root)

        self.debug_window.title("Debug")
        self.apply_bluewing_icon(self.debug_window)

        self.debug_window.resizable(
            False,
            False
        )

        self.debug_window.geometry(
            "450x140"
        )

        tk.Label(
            self.debug_window,
            textvariable=self.hexdebug,
            anchor="w",
            font=("Courier New",9)
        ).pack(
            fill="x",
            padx=5,
            pady=2
        )

        tk.Label(
            self.debug_window,
            textvariable=self.cpu,
            anchor="w"
        ).pack(fill="x", padx=5)

        tk.Label(
            self.debug_window,
            textvariable=self.prg,
            anchor="w"
        ).pack(fill="x", padx=5)

        tk.Label(
            self.debug_window,
            textvariable=self.tileoff,
            anchor="w"
        ).pack(fill="x", padx=5)

        tk.Label(
            self.debug_window,
            textvariable=self.attrinfo,
            anchor="w"
        ).pack(fill="x", padx=5)

    def show_welcome_screen(self):

        self.splash_frame.pack(
            fill="both",
            expand=True
        )

    def show_feature_guide(self):

        win = tk.Toplevel(self.root)
        win.title("Blue Wing Feature Guide")
        win.geometry("650x520")
        win.resizable(False, False)

        text = tk.Text(
            win,
            wrap="word",
            padx=14,
            pady=12
        )
        scrollbar = ttk.Scrollbar(
            win,
            orient="vertical",
            command=text.yview
        )
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)

        text.tag_config(
            "title",
            font=("Segoe UI", 18, "bold"),
            foreground="#204a87",
            spacing3=8
        )
        text.tag_config(
            "subtitle",
            font=("Segoe UI", 10, "italic"),
            spacing3=12
        )
        text.tag_config(
            "heading",
            font=("Segoe UI", 12, "bold"),
            spacing1=10,
            spacing3=4
        )
        text.tag_config(
            "body",
            font=("Segoe UI", 10),
            lmargin1=12,
            lmargin2=12,
            spacing3=5
        )

        text.insert("end", f"Blue Wing v{APP_VERSION}\n", "title")
        text.insert(
            "end",
            "By BlueFinch \u2014 last update: June 2026\n\n",
            "subtitle"
        )

        sections = [
            (
                "Project Profiles",
                [
                    "Create, duplicate, delete, save, and activate JSON-based hack profiles.",
                    "Store hack-specific offsets, feature toggles, behavior options, and backup regions per profile.",
                    "Associate a stable profile JSON filename with each ROM/project.",
                    "Track whether the Overworld Names Engine is installed for each profile / toggle features accordingly.",
                ]
            ),
            (
                "Profile ROM Data",
                [
                    "Save world banners, world banner positions, level names, level-name palettes, and world palettes into the active profile JSON.",
                    "Restore profile ROM data automatically when a profile becomes active or its ROM is loaded.",
                ]
            ),
            (
                "World / Level Names",
                [
                    "Disable this whole branch when the active profile does not have the Overworld Names Engine patch installed.",
                    "Edit level names for each world.",
                    "Edit world banners from the world nodes.",
                    "Choose whether a world banner appears \u201cAbove Border\u201d or \u201cOn Border\u201d.",
                    "Edit map tile assignments used by level-name triggers.",
                ]
            ),
            (
                "World Palettes",
                [
                    "Edit world map tile palettes / sprite palettes (colors level names).",
                    "Large palette swatch (with hex value) for easier color work.",
                ]
            ),
            (
                "Game Text",
                [
                    "Configure and edit in-game text entries for throne rooms, princess letters, princess rescue text, and Toad House speech.",
                    "Store user-customized game text bytes in the active profile and restore them after loading a freshly compiled ROM.",
                ]
            ),
            (
                "Level Backups",
                [
                    "Back up all configured level tileset regions for the active profile.",
                    "Back up and restore individual tileset regions from separate backup nodes.",
                    "Show backup status for each configured tileset.",
                    "Use stable profile JSON filenames for profile-specific backup folders.",
                ]
            ),
            (
                "ROM Workflow",
                [
                    "Open, save, and save-as ROM files.",
                    "Open the most recent ROM at startup.",
                    "Auto-reload when the ROM changes externally.",
                    "Auto-save changes when enabled.",
                    "Confirm before overwriting the active ROM.",
                ]
            ),
            (
                "Interface Tools",
                [
                    "Tree navigation for Home, Project Profiles, World / Level Names, World Palettes, and Level Backups.",
                    "Game Text branch for profile-backed in-game text editing.",
                    "Optional collapsed world nodes on startup.",
                    "Optional always-on-top window behavior.",
                    "Debug window for ROM address, pointer, tile offset, and attribute details.",
                    "Console updates for profile changes, profile saves, profile activation, level backups, and restores.",
                ]
            ),
        ]

        for heading, items in sections:
            text.insert("end", heading + "\n", "heading")
            for item in items:
                text.insert("end", f"\u2022 {item}\n", "body")
            text.insert("end", "\n", "body")

        text.config(state="disabled")
        self.finish_dialog(win)

    def show_about(self):

        win = tk.Toplevel(self.root)
        win.title("About Blue Wing")
        win.geometry("520x420")
        win.resizable(False, False)

        content = tk.Frame(win, padx=18, pady=16)
        content.pack(fill="both", expand=True)

        logo_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "icons",
            "BlueWing.png",
        )
        try:
            self.about_logo_image = tk.PhotoImage(file=logo_path).subsample(2, 2)
            tk.Label(content, image=self.about_logo_image).pack(pady=(0, 10))
        except tk.TclError:
            tk.Label(
                content,
                text=APP_NAME,
                font=("Segoe UI", 22, "bold"),
                foreground="#204a87",
            ).pack(pady=(0, 10))

        tk.Label(
            content,
            text=f"{APP_NAME} v{APP_VERSION}",
            font=("Segoe UI", 18, "bold"),
            foreground="#204a87",
        ).pack()

        tk.Label(
            content,
            text="By BlueFinch",
            font=("Segoe UI", 10, "italic"),
        ).pack(pady=(2, 14))

        copy = (
            "Blue Wing is a profile-driven ROM-editing environment for the NES "
            "version of Super Mario Bros. 3. that organizes hack-specific "
            "settings, backups, game text, palettes, and world/level metadata "
            "into a development-friendly ecosystem. Blue Wing combines project "
            "management, editing, debugging, and restoration tools into a "
            "single interface, and accommodates a streamlined workflow by "
            "allowing work to be saved and restored consistently across ROM "
            "builds from a given profile."
        )
        tk.Message(
            content,
            text=copy,
            width=460,
            font=("Segoe UI", 10),
        ).pack(fill="x", pady=(0, 14))

        ttk.Button(
            content,
            text="OK",
            command=win.destroy,
        ).pack()
        self.finish_dialog(win)

    def show_color_picker(self,index):

        win = tk.Toplevel(self.root)

        win.title("Choose NES Color")

        win.transient(self.root)
        win.grab_set()

        for color in range(64):

            bg = NES_RGB[color]
            fg = "white" if bg.upper() == "#000000" else "black"
            def choose(v=color):

                self.current_palette[index] = v

                self.refresh_palette_buttons()

                win.destroy()

            tk.Button(
                win,
                width=3,
                height=1,
                font=("Segoe UI", 11),
                text=f"{color:02X}",
                relief="flat",
                bd=1,
                highlightthickness=0,
                takefocus=False,
                bg=bg,
                fg=fg,
                activebackground=bg,
                command=choose
            ).grid(
                row=color // 16,
                column=color % 16,
                padx=1,
                pady=1
            )
        self.finish_color_picker(win)

    def show_tile_picker(self,index):
        win = tk.Toplevel(self.root)

        win.title("Choose NES Color")

        win.transient(self.root)
        win.grab_set()

        for color in range(64):

            bg = NES_RGB[color]
            fg = "white" if bg.upper() == "#000000" else "black"
            def choose(v=color):

                self.current_tile_palette[index] = v

                self.refresh_palette_buttons()

                win.destroy()

            tk.Button(
                win,
                width=3,
                height=1,
                font=("Segoe UI", 11),
                text=f"{color:02X}",
                relief="flat",
                bd=1,
                highlightthickness=0,
                takefocus=False,
                bg=bg,
                fg=fg,
                activebackground=bg,
                command=choose
            ).grid(
                row=color // 16,
                column=color % 16,
                padx=1,
                pady=1
            )
        self.finish_color_picker(win)

    def decode_attributes(self, value):

        palette = value & 0x03

        priority = bool(value & 0x20)
        hflip = bool(value & 0x40)
        vflip = bool(value & 0x80)

        return palette, priority, hflip, vflip

    def encode_attributes(
        self,
        palette,
        priority,
        hflip,
        vflip
    ):

        value = palette & 0x03

        if priority:
            value |= 0x20

        if hflip:
            value |= 0x40

        if vflip:
            value |= 0x80

        return value


       
    def decode(self,b):
        return "".join(CHAR_MAP.get(x," ") for x in b).rstrip()

    def encode(self,s):
        s=s.upper()[:16].ljust(16)
        return bytes(TEXT_MAP.get(c,0x41) for c in s)



    def decode_world_banner(self,b):
        return "".join(
            WORLD_CHAR_MAP.get(x,"?")
            for x in b
        ).rstrip()

    def encode_world_banner(self,s):
        return bytes(
            WORLD_TEXT_MAP[c]
            for c in s.upper()
        )
