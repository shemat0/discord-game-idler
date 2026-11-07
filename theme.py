"""Live light/dark palettes and their validated local preference."""
import tkinter as tk
from tkinter import ttk
from i18n import read_preferences, save_preference

PALETTES = {
    "dark": dict(background="#101722", surface="#192331", foreground="#e6edf5",
                 border="#3a4a60", selected="#315b8a", trough="#0c121c", focus="#82b8ff",
                 button="#26364b", disabled="#1b2532", muted="#91a0b3", pressed="#355b84",
                 hover="#344b68", checkhover="#1d2b3c", warning="#f3bd67", indicator="#93c5fd",
                 scrollbar="#34455d", scrollhover="#526988", scrollpressed="#6284af"),
    "light": dict(background="#f6f8fb", surface="#ffffff", foreground="#1f2937",
                  border="#a3b0c2", selected="#245ea0", trough="#e5eaf1", focus="#205b9a",
                  button="#e4eaf3", disabled="#e8edf3", muted="#647184", pressed="#c5d7ef",
                  hover="#d4e2f4", checkhover="#e8eff8", warning="#855000", indicator="#245ea0",
                  scrollbar="#a8b8cc", scrollhover="#8da4bf", scrollpressed="#6d8cae"),
}


def load_theme(path):
    value = read_preferences(path).get("theme")
    return value if isinstance(value, str) and value in PALETTES else "dark"


def save_theme(path, name):
    if name not in PALETTES:
        raise ValueError("Unsupported theme")
    save_preference(path, "theme", name)


def listbox_options(name):
    p = PALETTES[name]
    return dict(background=p["surface"], foreground=p["foreground"],
                selectbackground=p["selected"], selectforeground="#ffffff",
                disabledforeground=p["muted"], highlightbackground=p["border"],
                highlightcolor=p["focus"], highlightthickness=1,
                borderwidth=0, activestyle="none")


def apply_theme(root, name):
    p = PALETTES[name]
    style = ttk.Style(root)
    if style.theme_use() != "clam":
        style.theme_use("clam")
    root.configure(background=p["background"])
    style.configure(".", background=p["background"], foreground=p["foreground"],
                    bordercolor=p["border"], lightcolor=p["border"], darkcolor=p["border"],
                    troughcolor=p["trough"], focuscolor=p["focus"])
    style.configure("TFrame", background=p["background"])
    style.configure("TLabel", background=p["background"], foreground=p["foreground"])
    style.configure("Warning.TLabel", foreground=p["warning"], background=p["background"])
    style.configure("TButton", background=p["button"], foreground=p["foreground"], padding=(10, 5), borderwidth=1)
    style.map("TButton", background=[("disabled", p["disabled"]), ("pressed", p["pressed"]), ("active", p["hover"])],
              foreground=[("disabled", p["muted"]), ("active", p["foreground"])])
    for widget in ("TEntry", "TSpinbox", "TCombobox"):
        style.configure(widget, fieldbackground=p["surface"], background=p["button"], foreground=p["foreground"],
                        insertcolor=p["foreground"], selectbackground=p["selected"], selectforeground="#ffffff",
                        arrowcolor=p["foreground"], bordercolor=p["border"])
        style.map(widget, fieldbackground=[("disabled", p["disabled"]), ("readonly", p["surface"])],
                  foreground=[("disabled", p["muted"]), ("readonly", p["foreground"])],
                  background=[("active", p["hover"])], bordercolor=[("focus", p["focus"])],
                  arrowcolor=[("disabled", p["muted"])])
    style.configure("TCheckbutton", background=p["background"], foreground=p["foreground"],
                    indicatorbackground=p["surface"], indicatorforeground="#ffffff", indicatorcolor=p["indicator"])
    style.map("TCheckbutton", background=[("active", p["checkhover"])],
              foreground=[("disabled", p["muted"]), ("active", p["foreground"])],
              indicatorbackground=[("disabled", p["disabled"]), ("selected", p["selected"])])
    style.configure("Treeview", background=p["surface"], fieldbackground=p["surface"],
                    foreground=p["foreground"], bordercolor=p["border"], rowheight=24)
    style.map("Treeview", background=[("selected", p["selected"])], foreground=[("selected", "#ffffff"), ("disabled", p["muted"])])
    style.configure("Treeview.Heading", background=p["button"], foreground=p["foreground"], relief="flat", padding=(6, 5))
    style.map("Treeview.Heading", background=[("active", p["hover"])])
    style.configure("TScrollbar", background=p["scrollbar"], troughcolor=p["trough"], arrowcolor=p["foreground"], bordercolor=p["background"])
    style.map("TScrollbar", background=[("active", p["scrollhover"]), ("pressed", p["scrollpressed"])])
    options = listbox_options(name)
    for key in ("background", "foreground", "selectbackground", "selectforeground"):
        root.option_add("*TCombobox*Listbox." + {"selectbackground": "selectBackground", "selectforeground": "selectForeground"}.get(key, key), options[key])
    def visit(widget):
        if isinstance(widget, tk.Listbox):
            widget.configure(**options)
        elif isinstance(widget, ttk.Combobox):
            # Existing Tcl-created popups are not Python widget objects, and
            # option_add alone only affects popups created after the change.
            popup = str(root.tk.call("ttk::combobox::PopdownWindow", str(widget)))
            root.tk.call(popup + ".f.l", "configure", "-background", p["surface"],
                         "-foreground", p["foreground"], "-selectbackground", p["selected"],
                         "-selectforeground", "#ffffff")
            return
        for child in widget.winfo_children():
            visit(child)
    visit(root)
