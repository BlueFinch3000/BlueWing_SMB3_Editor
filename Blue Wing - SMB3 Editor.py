import os
import tkinter as tk

from application import App, ICON_DIR
from constants import APP_TITLE


def minimize_console_window():
    try:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 6)
    except Exception:
        pass


def main():
    minimize_console_window()
    root = tk.Tk()
    root.iconbitmap(os.path.join(ICON_DIR, "BlueWing.ico"))
    root.geometry("756x575")
    root.resizable(False, False)
    root.title(APP_TITLE)

    App(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        traceback.print_exc()
        input("\nPress Enter to close...")
