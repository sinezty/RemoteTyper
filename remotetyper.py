"""
RemoteTyper — Universal Remote Console Text Injector

Types text character-by-character using Direct Keystrokes or ALT+Numpad ASCII codes.
Built for environments where clipboard paste doesn't work:
VNC, Proxmox (noVNC), IPMI/iLO/iDRAC consoles, Hyper-V, and air-gapped terminals.

Hotkeys (Conflict-Free, Suppressed):
  F2     — Step: Type single line & wait for next F2
  F8     — Auto: Run all lines (5s initial countdown, Line Delay between lines)
  F9     — Emergency stop immediately
  Escape — Cancel typing (when focused)

GitHub: https://github.com/sinezty/RemoteTyper
License: MIT
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from pynput.keyboard import Controller, Key, KeyCode
import time
import threading
import keyboard as kb_listener
import os
import sys
import webbrowser
import logging

DEBUG_MODE = "--debug" in sys.argv
LOG_FILE = "remotetyper_debug.log"

if DEBUG_MODE:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8", mode="w"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.debug("================ RemoteTyper Debug Mode Activated ================")
    logging.debug(f"Python Version: {sys.version}")
    logging.debug(f"Platform: {sys.platform}")
    logging.debug(f"CLI Arguments: {sys.argv}")

pynput_kb = Controller()

def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

PLACEHOLDER_TEXT = (
    "# ── [ INPUT BUFFER ] ───────────────────────────────────────────────\n"
    "# Paste your commands, shell script, or config text here.\n"
    "# F2: Step line-by-line  |  F8: Auto execute (5s delay)  |  F9: Abort\n"
    "# Line Delay: Pauses between lines to allow command output to settle.\n"
    "# Supports Proxmox (noVNC), VNC, IPMI/iDRAC, Hyper-V, and KVMs."
)

def sanitize_text(text: str) -> tuple[str, int]:
    replacements = {
        '\u201c': '"',  # “
        '\u201d': '"',  # ”
        '\u201e': '"',  # „
        '\u00ab': '"',  # «
        '\u00bb': '"',  # »
        '\u2018': "'",  # ‘
        '\u2019': "'",  # ’
        '\u201a': "'",  # ‚
        '\u2014': '--', # —
        '\u2013': '-',  # –
        '\u2212': '-',  # −
        '\u00a0': ' ',  # non-breaking space
        '\u200b': '',   # zero-width space
        '\ufeff': '',   # byte order mark (BOM)
        '┌': '+', '┐': '+', '└': '+', '┘': '+',
        '├': '+', '┤': '+', '┬': '+', '┴': '+', '┼': '+',
        '│': '|', '─': '-', '═': '=', '║': '|',
        '╔': '+', '╗': '+', '╚': '+', '╝': '+',
        '╠': '+', '╣': '+', '╦': '+', '╩': '+', '╬': '+',
        '•': '*', '·': '*', '…': '...', '→': '->', '←': '<-',
    }
    count = 0
    cleaned = []
    for ch in text:
        if ch in replacements:
            cleaned.append(replacements[ch])
            count += 1
        else:
            cleaned.append(ch)
    return "".join(cleaned), count

SPEED_PRESETS = {
    "Slow":   (0.025, 0.018, 0.035, 0.12),
    "Normal": (0.012, 0.008, 0.018, 0.08),
    "Fast":   (0.006, 0.004, 0.009, 0.04),
}

# ─── High-Contrast TUI / Console Palette ────────────────────────────────────

C = {
    "bg":             "#0a0e14",
    "surface":        "#10151f",
    "surface_alt":    "#161e2c",
    "editor_bg":      "#070a0f",
    "gutter_bg":      "#0d121b",

    "border":         "#253347",
    "border_light":   "#3b4e6b",
    "separator":      "#1a2433",

    "cyan":           "#22d3ee",
    "cyan_dim":       "#0e3b43",
    "cyan_hover":     "#06b6d4",

    "step":           "#0284c7",
    "step_hover":     "#0369a1",
    "step_bg":        "#082f49",
    "step_fg":        "#38bdf8",

    "green":          "#10b981",
    "green_hover":    "#059669",
    "green_bg":       "#062d1f",
    "green_fg":       "#4ade80",

    "red":            "#ef4444",
    "red_hover":      "#dc2626",
    "red_bg":         "#381315",
    "red_fg":         "#f87171",

    "amber":          "#f59e0b",
    "amber_bg":       "#2e1c07",

    "text":           "#ffffff",
    "text_sec":       "#cbd5e1",
    "text_muted":     "#94a3b8",
    "gutter_fg":      "#64748b",

    "prog":           "#22d3ee",
    "prog_bg":        "#161e2c",
    "hl_bg":          "#123730",
    "hl_fg":          "#a7f3d0",
}

FONT_UI = "Segoe UI"
FONT_CODE = "Consolas"

def _make_optionmenu_toggleable(opt_menu: ctk.CTkOptionMenu):
    opt_menu._last_unmap = 0

    def on_unmap(e=None):
        opt_menu._last_unmap = time.time()

    try:
        opt_menu._dropdown_menu.bind("<Unmap>", on_unmap, add="+")
    except Exception:
        pass

    orig_open = opt_menu._open_dropdown_menu

    def custom_open():
        if time.time() - getattr(opt_menu, '_last_unmap', 0) < 0.25:
            return
        orig_open()

    opt_menu._open_dropdown_menu = custom_open

class RemoteTyperApp:
    def __init__(self):
        self.stop_flag = False
        self.total_chars = 0
        self.typed_chars = 0
        self.is_typing = False
        self.step_idx = 0
        self._last_total = 0
        self._placeholder_active = True

        self._build_window()
        self._build_ui()
        self._build_context_menu()
        self._register_hotkeys()

        self.root.mainloop()

    # ── Window ───────────────────────────────────────────────────────────

    def _build_window(self):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('sinezty.remotetyper.app.1.0')
        except Exception:
            pass

        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.title("RemoteTyper")

        w, h = 840, 580
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.minsize(760, 420)
        self.root.configure(fg_color=C["bg"])

        self.topmost_var = ctk.BooleanVar(value=True)
        self.root.attributes("-topmost", True)

        self.root.grid_columnconfigure(0, weight=1)
        # Row 0: Banner
        # Row 1: Top File bar
        # Row 2: Editor (expand)
        # Row 3: Bottom deck
        self.root.grid_rowconfigure(2, weight=1)

        ico_path = resource_path("icon.ico")
        png_path = resource_path(os.path.join("assets", "icon.png"))
        if not os.path.exists(png_path):
            png_path = resource_path("icon.png")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass
        if os.path.exists(png_path):
            try:
                self._app_icon_img = tk.PhotoImage(file=png_path)
                self.root.iconphoto(True, self._app_icon_img)
            except Exception:
                pass

        # Windows 11 DWM: Force pure dark title bar with bright white title text
        try:
            self.root.update_idletasks()
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            dark = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(dark), ctypes.sizeof(dark))
            caption_color = ctypes.c_int(0x00140E0A)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(caption_color), ctypes.sizeof(caption_color))
            text_color = ctypes.c_int(0x00FFFFFF)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, ctypes.byref(text_color), ctypes.sizeof(text_color))
        except Exception:
            pass

        self.root.bind("<Escape>", lambda e: self._stop() if self.is_typing else None)

    def _build_ui(self):
        self._build_banner()
        self._build_top_bar()
        self._build_editor()
        self._build_bottom_deck()

    # ── 1. Header Banner ─────────────────────────────────────────────────

    def _build_banner(self):
        banner = ctk.CTkFrame(self.root, fg_color=C["surface"], corner_radius=0, height=40)
        banner.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 5))

        left = ctk.CTkFrame(banner, fg_color="transparent")
        left.pack(side="left", padx=16, pady=6)

        ctk.CTkLabel(
            left, text=">_",
            font=ctk.CTkFont(family=FONT_CODE, size=15, weight="bold"),
            text_color=C["cyan"]
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            left, text="RemoteTyper",
            font=ctk.CTkFont(family=FONT_UI, size=14, weight="bold"),
            text_color="#ffffff"
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            left, text="v1.0",
            font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold"),
            text_color=C["cyan"]
        ).pack(side="left", padx=(0, 6))

        if DEBUG_MODE:
            ctk.CTkLabel(
                left, text="[DEBUG LOGGING]",
                font=ctk.CTkFont(family=FONT_UI, size=10, weight="bold"),
                text_color=C["amber"]
            ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            left, text="──  Universal Remote Console Keystroke Injector",
            font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold"),
            text_color="#e2e8f0"
        ).pack(side="left")

        right = ctk.CTkFrame(banner, fg_color="transparent")
        right.pack(side="right", padx=16, pady=6)

        self.btn_gh = ctk.CTkButton(
            right, text="github.com/sinezty",
            font=ctk.CTkFont(family=FONT_UI, size=10),
            text_color="#64748b", hover_color=C["surface_alt"],
            fg_color="transparent", border_width=1, border_color="#1e293b",
            height=22, width=120, corner_radius=3, cursor="hand2",
            command=lambda: webbrowser.open("https://github.com/sinezty")
        )
        self.btn_gh.pack(side="left", padx=(0, 10))

        self.chk_topmost = ctk.CTkCheckBox(
            right, text="Pin on top",
            variable=self.topmost_var, command=self._toggle_topmost,
            font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold"),
            text_color=C["cyan"], fg_color=C["cyan"],
            checkmark_color="#000000",
            border_color=C["border_light"],
            width=16, height=16, checkbox_width=16, checkbox_height=16,
            corner_radius=3
        )
        self.chk_topmost.pack(side="left")

    # ── 2. Top Bar (File Ops & Enter mode) ────────────────────────────────

    def _build_top_bar(self):
        bar = ctk.CTkFrame(self.root, fg_color=C["surface"], corner_radius=4,
                           border_width=1, border_color=C["border"], height=40)
        bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=5)

        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left")

        btn_tui = dict(
            height=28, corner_radius=4,
            fg_color=C["surface_alt"], hover_color=C["border_light"],
            text_color="#ffffff", border_width=1, border_color=C["border_light"],
            font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold")
        )

        self.btn_open = ctk.CTkButton(left, text="📂  Open File", width=105, command=self._open_file, **btn_tui)
        self.btn_open.pack(side="left", padx=(0, 8))

        self.btn_clear = ctk.CTkButton(left, text="✕  Clear", width=80, command=self._clear_text, **btn_tui)
        self.btn_clear.pack(side="left")

        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")

        ctk.CTkLabel(
            right, text="Enter at EOL:",
            font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold"),
            text_color=C["cyan"]
        ).pack(side="left", padx=(0, 6))

        self.enter_mode_var = ctk.StringVar(value="Each Line")
        self.opt_enter = ctk.CTkOptionMenu(
            right, values=["Each Line", "Except Last", "Disabled"],
            variable=self.enter_mode_var, width=120, height=28,
            fg_color=C["surface_alt"], button_color=C["border_light"],
            button_hover_color=C["cyan_dim"],
            dropdown_fg_color=C["surface"],
            dropdown_hover_color=C["surface_alt"],
            text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold"),
            dropdown_font=ctk.CTkFont(family=FONT_UI, size=11),
            corner_radius=4
        )
        self.opt_enter.pack(side="left")
        _make_optionmenu_toggleable(self.opt_enter)

    # ── 3. Terminal Buffer Editor ────────────────────────────────────────

    def _build_editor(self):
        frame = ctk.CTkFrame(self.root, fg_color=C["surface"], corner_radius=4,
                             border_width=1, border_color=C["border"])
        frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 5))
        frame.grid_columnconfigure(2, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.line_numbers = tk.Text(
            frame, width=5, padx=6, pady=8,
            bg=C["gutter_bg"], fg=C["gutter_fg"],
            font=(FONT_CODE, 11), bd=0, highlightthickness=0,
            state="disabled", cursor="arrow", relief="flat"
        )
        self.line_numbers.grid(row=0, column=0, sticky="ns")

        tk.Frame(frame, width=1, bg=C["border"]).grid(row=0, column=1, sticky="ns")

        self.text_area = tk.Text(
            frame, wrap="none", padx=12, pady=8,
            bg=C["editor_bg"], fg=C["text"],
            insertbackground=C["cyan"],
            selectbackground="#1e3a5f",
            selectforeground="#ffffff",
            font=(FONT_CODE, 11), bd=0, highlightthickness=0,
            undo=True, autoseparators=True, maxundo=50, relief="flat"
        )
        self.text_area.grid(row=0, column=2, sticky="nsew")

        scrollbar = ctk.CTkScrollbar(
            frame, command=self.text_area.yview,
            fg_color=C["surface"], button_color=C["border"],
            button_hover_color=C["border_light"]
        )
        scrollbar.grid(row=0, column=3, sticky="ns", padx=(0, 2), pady=4)
        self.text_area.configure(yscrollcommand=scrollbar.set)

        self.text_area.tag_config("typed", background=C["hl_bg"], foreground=C["hl_fg"])

        self.text_area.bind("<KeyRelease>", self._update_line_numbers)
        self.text_area.bind("<MouseWheel>", self._sync_scroll)
        self.text_area.bind("<<Modified>>", self._on_modified)
        self.text_area.bind("<Configure>", lambda e: self._update_line_numbers())
        self.text_area.bind("<Control-a>", self._select_all)
        self.text_area.bind("<FocusIn>", self._on_focus_in)
        self.text_area.bind("<FocusOut>", self._on_focus_out)

        self._placeholder_active = True
        self.text_area.insert("1.0", PLACEHOLDER_TEXT)
        self.text_area.configure(fg=C["text_muted"])
        self._update_line_numbers()

    def _build_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0, font=(FONT_UI, 10),
                                    bg=C["surface"], fg=C["text"],
                                    activebackground=C["cyan_dim"], activeforeground=C["cyan"])
        self.context_menu.add_command(label="✂  Cut", command=lambda: self.text_area.event_generate("<<Cut>>"))
        self.context_menu.add_command(label="📋  Copy", command=lambda: self.text_area.event_generate("<<Copy>>"))
        self.context_menu.add_command(label="📥  Paste", command=lambda: self.text_area.event_generate("<<Paste>>"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🔍  Select All", command=self._select_all)
        self.context_menu.add_command(label="✕  Clear", command=self._clear_text)
        self.text_area.bind("<Button-3>", lambda e: self.context_menu.tk_popup(e.x_root, e.y_root))

    # ── Bottom Controls ──────────────────────────────────────────────────

    def _build_bottom_deck(self):
        deck = ctk.CTkFrame(self.root, fg_color=C["surface"], corner_radius=4,
                            border_width=1, border_color=C["border"])
        deck.grid(row=3, column=0, sticky="sew", padx=10, pady=(0, 8))
        deck.grid_columnconfigure(0, weight=1)

        ctrl_bar = ctk.CTkFrame(deck, fg_color="transparent")
        ctrl_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=6)

        left_settings = ctk.CTkFrame(ctrl_bar, fg_color="transparent")
        left_settings.pack(side="left")

        cfg_lbl = dict(text_color=C["cyan"], font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold"))

        # Mode
        ctk.CTkLabel(left_settings, text="Mode:", **cfg_lbl).pack(side="left", padx=(0, 5))
        self.input_mode_var = ctk.StringVar(value="Direct Type")
        self.opt_mode = ctk.CTkOptionMenu(
            left_settings, values=["Direct Type", "ALT+Numpad"],
            variable=self.input_mode_var, width=115, height=28,
            fg_color=C["surface_alt"], button_color=C["border_light"],
            button_hover_color=C["cyan_dim"],
            dropdown_fg_color=C["surface"],
            dropdown_hover_color=C["surface_alt"],
            text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold"),
            dropdown_font=ctk.CTkFont(family=FONT_UI, size=11),
            corner_radius=4
        )
        self.opt_mode.pack(side="left", padx=(0, 10))
        _make_optionmenu_toggleable(self.opt_mode)

        # Speed
        ctk.CTkLabel(left_settings, text="Speed:", **cfg_lbl).pack(side="left", padx=(0, 5))
        self.speed_var = ctk.StringVar(value="Normal")
        self.opt_speed = ctk.CTkOptionMenu(
            left_settings, values=list(SPEED_PRESETS.keys()),
            variable=self.speed_var, width=88, height=28,
            fg_color=C["surface_alt"], button_color=C["border_light"],
            button_hover_color=C["cyan_dim"],
            dropdown_fg_color=C["surface"],
            dropdown_hover_color=C["surface_alt"],
            text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold"),
            dropdown_font=ctk.CTkFont(family=FONT_UI, size=11),
            corner_radius=4
        )
        self.opt_speed.pack(side="left", padx=(0, 10))
        _make_optionmenu_toggleable(self.opt_speed)

        # Line Delay
        ctk.CTkLabel(left_settings, text="Line Delay:", **cfg_lbl).pack(side="left", padx=(0, 5))
        self.line_delay_var = ctk.StringVar(value="3")
        ctk.CTkEntry(
            left_settings, width=34, height=28, textvariable=self.line_delay_var,
            fg_color=C["surface_alt"], border_color=C["border_light"], text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold"), corner_radius=4, justify="center"
        ).pack(side="left", padx=(0, 3))
        ctk.CTkLabel(left_settings, text="s", text_color=C["text_sec"],
                     font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold")).pack(side="left")

        # Action Buttons
        btn_box = ctk.CTkFrame(ctrl_bar, fg_color="transparent")
        btn_box.pack(side="right")

        self.btn_step = ctk.CTkButton(
            btn_box, text="⏭  STEP (F2)", width=120, height=28,
            fg_color=C["step"], hover_color=C["step_hover"],
            text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold"),
            corner_radius=4, command=self._on_step
        )
        self.btn_step.pack(side="left", padx=(0, 8))

        self.btn_start = ctk.CTkButton(
            btn_box, text="▶  AUTO (F8)", width=125, height=28,
            fg_color=C["green"], hover_color=C["green_hover"],
            text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold"),
            corner_radius=4, command=self._on_start
        )
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_stop = ctk.CTkButton(
            btn_box, text="■  ABORT (F9)", width=110, height=28,
            fg_color=C["red_bg"], hover_color=C["red"],
            border_width=1, border_color=C["red"],
            text_color=C["red_fg"],
            font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold"),
            corner_radius=4, state="disabled", command=self._stop
        )
        self.btn_stop.pack(side="left")

        sep = ctk.CTkFrame(deck, fg_color=C["separator"], height=1)
        sep.grid(row=1, column=0, sticky="ew")

        # Status Bar
        status_bar = ctk.CTkFrame(deck, fg_color="#070a0f", corner_radius=0, height=32)
        status_bar.grid(row=2, column=0, sticky="ew")
        status_bar.grid_columnconfigure(1, weight=1)

        self.lbl_status = ctk.CTkLabel(
            status_bar, text="● IDLE",
            text_color=C["cyan"], font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold")
        )
        self.lbl_status.grid(row=0, column=0, sticky="w", padx=(12, 8), pady=4)

        prog_container = ctk.CTkFrame(status_bar, fg_color="transparent")
        prog_container.grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        prog_container.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(
            prog_container, height=8, fg_color=C["prog_bg"],
            progress_color=C["prog"], corner_radius=2,
            border_width=1, border_color=C["border_light"]
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.progress_bar.set(0)

        self.lbl_progress = ctk.CTkLabel(
            prog_container, text="[ 0/0 · 0% ]",
            text_color="#ffffff", font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold")
        )
        self.lbl_progress.grid(row=0, column=1, sticky="e")

        right_box = ctk.CTkFrame(status_bar, fg_color="transparent")
        right_box.grid(row=0, column=2, sticky="e", padx=(8, 12), pady=3)

        # Hotkey chips
        k_f2 = ctk.CTkFrame(right_box, fg_color=C["surface_alt"], corner_radius=3)
        k_f2.pack(side="left", padx=2)
        ctk.CTkLabel(k_f2, text=" F2 ", bg_color=C["step"], text_color="#ffffff",
                     font=ctk.CTkFont(family=FONT_UI, size=10, weight="bold")).pack(side="left")
        ctk.CTkLabel(k_f2, text=" Step ", text_color=C["step_fg"],
                     font=ctk.CTkFont(family=FONT_UI, size=10, weight="bold")).pack(side="left")

        k_f8 = ctk.CTkFrame(right_box, fg_color=C["surface_alt"], corner_radius=3)
        k_f8.pack(side="left", padx=2)
        ctk.CTkLabel(k_f8, text=" F8 ", bg_color=C["green"], text_color="#000000",
                     font=ctk.CTkFont(family=FONT_UI, size=10, weight="bold")).pack(side="left")
        ctk.CTkLabel(k_f8, text=" Auto ", text_color=C["green_fg"],
                     font=ctk.CTkFont(family=FONT_UI, size=10, weight="bold")).pack(side="left")

        k_f9 = ctk.CTkFrame(right_box, fg_color=C["surface_alt"], corner_radius=3)
        k_f9.pack(side="left", padx=2)
        ctk.CTkLabel(k_f9, text=" F9 ", bg_color=C["red"], text_color="#ffffff",
                     font=ctk.CTkFont(family=FONT_UI, size=10, weight="bold")).pack(side="left")
        ctk.CTkLabel(k_f9, text=" Abort ", text_color=C["red_fg"],
                     font=ctk.CTkFont(family=FONT_UI, size=10, weight="bold")).pack(side="left")

        k_esc = ctk.CTkFrame(right_box, fg_color=C["surface_alt"], corner_radius=3)
        k_esc.pack(side="left", padx=2)
        ctk.CTkLabel(k_esc, text=" Esc ", bg_color=C["border_light"], text_color="#ffffff",
                     font=ctk.CTkFont(family=FONT_UI, size=10, weight="bold")).pack(side="left")
        ctk.CTkLabel(k_esc, text=" Stop ", text_color=C["text_sec"],
                     font=ctk.CTkFont(family=FONT_UI, size=10, weight="bold")).pack(side="left")

        self.lbl_chars = ctk.CTkLabel(
            right_box, text="0L·0C",
            text_color=C["text_sec"], font=ctk.CTkFont(family=FONT_UI, size=10, weight="bold")
        )
        self.lbl_chars.pack(side="left", padx=(4, 0))

    # ── Helpers ──────────────────────────────────────────────────────────

    def _toggle_topmost(self):
        self.root.attributes("-topmost", self.topmost_var.get())

    def _select_all(self, e=None):
        if not self._placeholder_active:
            self.text_area.tag_add("sel", "1.0", "end")
        return "break"

    def _on_focus_in(self, event=None):
        if self._placeholder_active:
            self.text_area.delete("1.0", "end")
            self.text_area.configure(fg=C["text"])
            self._placeholder_active = False
            self._update_line_numbers()
            self._update_chars()

    def _on_focus_out(self, event=None):
        content = self.text_area.get("1.0", "end-1c").strip()
        if not content:
            self._placeholder_active = True
            self.text_area.delete("1.0", "end")
            self.text_area.insert("1.0", PLACEHOLDER_TEXT)
            self.text_area.configure(fg=C["text_muted"])
            self._update_line_numbers()
            self._update_chars()

    def _get_editor_text(self):
        if self._placeholder_active:
            return ""
        return self.text_area.get("1.0", "end-1c").strip()

    def _on_modified(self, e=None):
        if self.text_area.edit_modified():
            self.step_idx = 0
            if hasattr(self, 'btn_step'):
                self.btn_step.configure(text="⏭  STEP (F2)")
            self._update_line_numbers()
            self._update_chars()
            self.text_area.edit_modified(False)

    def _update_chars(self):
        if self._placeholder_active:
            self.lbl_chars.configure(text="0L·0C")
            return
        t = self.text_area.get("1.0", "end-1c")
        c, l = len(t), (t.count('\n') + 1 if t else 0)
        self.lbl_chars.configure(text=f"{l}L·{c}C")

    def _update_line_numbers(self, e=None):
        self.line_numbers.configure(state="normal")
        self.line_numbers.delete("1.0", "end")
        if self._placeholder_active:
            self.line_numbers.insert("1.0", "001")
        else:
            t = self.text_area.get("1.0", "end-1c")
            n = t.count('\n') + 1 if t else 1
            self.line_numbers.insert("1.0", "\n".join(f"{i:03d}" for i in range(1, n + 1)))
        self.line_numbers.configure(state="disabled")
        self.line_numbers.yview_moveto(self.text_area.yview()[0])

    def _sync_scroll(self, e=None):
        self.root.after(1, lambda: self.line_numbers.yview_moveto(self.text_area.yview()[0]))

    def _open_file(self):
        p = filedialog.askopenfilename(title="Open Script / Text", filetypes=[("All files", "*.*")])
        if p:
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.step_idx = 0
                if hasattr(self, 'btn_step'):
                    self.btn_step.configure(text="⏭  STEP (F2)")
                self._placeholder_active = False
                self.text_area.configure(fg=C["text"])
                self.text_area.delete("1.0", "end")
                self.text_area.tag_remove("typed", "1.0", "end")
                self.text_area.insert("1.0", content)
                self._update_line_numbers()
                self._update_chars()
                self.lbl_status.configure(text=f"● LOADED", text_color=C["green_fg"])
            except Exception as ex:
                self.lbl_status.configure(text=f"● ERR", text_color=C["red_fg"])

    def _clear_text(self):
        self.step_idx = 0
        if hasattr(self, 'btn_step'):
            self.btn_step.configure(text="⏭  STEP (F2)")
        self._placeholder_active = True
        self.text_area.delete("1.0", "end")
        self.text_area.tag_remove("typed", "1.0", "end")
        self.text_area.insert("1.0", PLACEHOLDER_TEXT)
        self.text_area.configure(fg=C["text_muted"])
        self._update_line_numbers()
        self._update_chars()
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="[ 0/0 · 0% ]")
        self.lbl_status.configure(text="● CLEARED", text_color=C["text_sec"])

    def _register_hotkeys(self):
        kb_listener.add_hotkey('F2', lambda: self.root.after(0, self._on_step), suppress=True)
        kb_listener.add_hotkey('F8', lambda: self.root.after(0, self._on_start), suppress=True)
        kb_listener.add_hotkey('F9', lambda: self.root.after(0, self._stop), suppress=True)

    def _get_line_delay(self) -> float:
        try:
            val = float(self.line_delay_var.get().replace(',', '.'))
            return max(0.0, val)
        except (ValueError, AttributeError):
            return 3.0

    def _inject_char(self, ch: str, mode: str, ad: float, nd: float, cd: float):
        if mode == "ALT+Numpad" and ord(ch) <= 255:
            code = str(ord(ch))
            pynput_kb.press(Key.alt)
            try:
                time.sleep(ad)
                for d in code:
                    if self.stop_flag:
                        break
                    k = KeyCode.from_vk(96 + int(d))
                    pynput_kb.press(k)
                    time.sleep(nd)
                    pynput_kb.release(k)
                    time.sleep(nd)
            finally:
                pynput_kb.release(Key.alt)
            time.sleep(cd)
        else:
            pynput_kb.type(ch)
            time.sleep(cd)

    def _send_enter(self, ad: float, ed: float):
        pynput_kb.press(Key.enter)
        time.sleep(ad)
        pynput_kb.release(Key.enter)
        time.sleep(ed)

    def _release_modifiers(self):
        try:
            pynput_kb.release(Key.alt)
            pynput_kb.release(Key.shift)
            pynput_kb.release(Key.ctrl)
        except Exception:
            pass

    # ── Step-by-Step Injection (F2) ──────────────────────────────────────

    def _on_step(self):
        if self.is_typing:
            return

        raw_text = self._get_editor_text()
        if not raw_text:
            self.lbl_status.configure(text="● EMPTY", text_color=C["red_fg"])
            return

        clean_text, sanitized_cnt = sanitize_text(raw_text)
        lines = clean_text.split('\n')
        total = len(lines)
        self._last_total = total

        if sanitized_cnt > 0 and self.step_idx == 0:
            self.lbl_status.configure(text=f"✨ Sanitized ({sanitized_cnt})", text_color=C["cyan"])

        # If previous step reached the end, reset to line 0
        if self.step_idx >= total:
            self.step_idx = 0
            self.text_area.tag_remove("typed", "1.0", "end")
            self.progress_bar.set(0)
            self.lbl_progress.configure(text=f"[ 0/{total} · 0% ]")

        curr_line_idx = self.step_idx
        line_to_type = lines[curr_line_idx]

        self.is_typing = True
        self.stop_flag = False
        self._set_buttons(True)

        speed = SPEED_PRESETS.get(self.speed_var.get(), SPEED_PRESETS["Normal"])
        ad, nd, cd, ed = speed
        mode = self.input_mode_var.get()
        enter_mode = self.enter_mode_var.get()

        if DEBUG_MODE:
            logging.debug(f"[STEP] Line {curr_line_idx + 1}/{total}: '{line_to_type}' | mode={mode}, speed={self.speed_var.get()}")

        # Initial countdown if triggered via UI button while window has focus
        needs_countdown = False
        try:
            focused = self.root.focus_get()
            if focused is not None and curr_line_idx == 0:
                needs_countdown = True
        except Exception:
            needs_countdown = False

        def run_step():
            try:
                if needs_countdown:
                    for s in range(2, 0, -1):
                        if self.stop_flag:
                            return self._done_step(True, curr_line_idx, total)
                        self.root.after(0, lambda sec=s: self.lbl_status.configure(
                            text=f"⏳ {sec}s (Switch to console)", text_color=C["amber"]))
                        self.root.after(0, lambda sec=s: self.btn_step.configure(text=f"[ ⏳ {sec}s ]"))
                        time.sleep(1)
                else:
                    time.sleep(0.15)

                if self.stop_flag:
                    return self._done_step(True, curr_line_idx, total)

                self.root.after(0, lambda: self.lbl_status.configure(
                    text=f"⚡ TYPING L{curr_line_idx + 1}...", text_color=C["green_fg"]))
                self.root.after(0, lambda: self.btn_step.configure(text="[ ⚡ TYPING ]"))

                col = 0
                for ch in line_to_type:
                    if self.stop_flag:
                        break
                    self._inject_char(ch, mode, ad, nd, cd)
                    col += 1
                    self.root.after(0, self._hl, f"{curr_line_idx + 1}.{col}")

                if not self.stop_flag:
                    should_enter = False
                    if enter_mode == "Each Line":
                        should_enter = True
                    elif enter_mode == "Except Last":
                        should_enter = (curr_line_idx < total - 1)

                    if should_enter:
                        self._send_enter(ad, ed)

                    self.step_idx = curr_line_idx + 1
                    self.root.after(0, self._hl, f"{curr_line_idx + 2}.0")
                    self._done_step(False, self.step_idx, total)
                else:
                    self._done_step(True, curr_line_idx, total)

            except Exception as ex:
                if DEBUG_MODE:
                    logging.exception(f"Unhandled exception in run_step: {ex}")
                self._done_step(True, curr_line_idx, total)
            finally:
                self._release_modifiers()

        threading.Thread(target=run_step, daemon=True).start()

    def _done_step(self, cancelled, next_line_idx, total):
        self.is_typing = False
        def ui():
            self._set_buttons(False)
            if cancelled:
                self.lbl_status.configure(text="⛔ STOPPED", text_color=C["red_fg"])
            elif next_line_idx >= total:
                self.lbl_status.configure(text=f"✔ ALL {total} LINES SENT", text_color=C["green_fg"])
                self.progress_bar.set(1.0)
                self.lbl_progress.configure(text="[ 100% ]")
                self.btn_step.configure(text="⏭  STEP (F2)")
            else:
                p = next_line_idx / total
                self.progress_bar.set(p)
                pct = int(p * 100)
                self.lbl_progress.configure(text=f"[ {next_line_idx}/{total} · {pct}% ]")
                self.lbl_status.configure(
                    text=f"⏸ L{next_line_idx}/{total} SENT · Press F2 for next",
                    text_color=C["cyan"]
                )
                self.btn_step.configure(text=f"⏭  STEP L{next_line_idx + 1} (F2)")
        self.root.after(0, ui)

    # ── Auto Injection Engine (F8) ───────────────────────────────────────

    def _on_start(self):
        if self.is_typing:
            return
        self._start()

    def _start(self):
        self.stop_flag = False
        raw_text = self._get_editor_text()
        if not raw_text:
            self.lbl_status.configure(text="● EMPTY", text_color=C["red_fg"])
            return

        clean_text, sanitized_cnt = sanitize_text(raw_text)
        lines = clean_text.split('\n')
        total = len(lines)
        self._last_total = total

        if sanitized_cnt > 0 and self.step_idx == 0:
            self.lbl_status.configure(text=f"✨ Sanitized ({sanitized_cnt})", text_color=C["cyan"])

        # Resume from current step if in-progress, or start from line 0
        start_line = self.step_idx if (0 <= self.step_idx < total) else 0
        if start_line == 0:
            self.text_area.tag_remove("typed", "1.0", "end")

        self.is_typing = True
        self._set_buttons(True)

        line_delay = self._get_line_delay()
        speed = SPEED_PRESETS.get(self.speed_var.get(), SPEED_PRESETS["Normal"])
        ad, nd, cd, ed = speed
        mode = self.input_mode_var.get()
        enter_mode = self.enter_mode_var.get()

        if DEBUG_MODE:
            logging.debug(f"[AUTO] Start from line {start_line + 1}/{total} | mode={mode}, speed={self.speed_var.get()}, line_delay={line_delay}s")

        def run_auto():
            try:
                # Initial countdown
                for s in range(5, 0, -1):
                    if self.stop_flag:
                        return self._done(True)
                    self.root.after(0, lambda sec=s: self.lbl_status.configure(
                        text=f"⏳ {sec}s (Switch to console)", text_color=C["amber"]))
                    self.root.after(0, lambda sec=s: self.btn_start.configure(text=f"[ ⏳ {sec}s ]"))
                    time.sleep(1)

                if self.stop_flag:
                    return self._done(True)

                self.root.after(0, lambda: self.btn_start.configure(text="[ ⚡ INJECTING ]"))
                self.root.after(0, lambda: self.lbl_status.configure(
                    text="⚡ INJECTING", text_color=C["green_fg"]))

                for ln_idx in range(start_line, total):
                    if self.stop_flag:
                        break

                    line = lines[ln_idx]
                    ln_num = ln_idx + 1

                    col = 0
                    for ch in line:
                        if self.stop_flag:
                            break
                        self._inject_char(ch, mode, ad, nd, cd)
                        col += 1
                        self.root.after(0, self._hl, f"{ln_num}.{col}")

                    if self.stop_flag:
                        break

                    should_enter = False
                    if enter_mode == "Each Line":
                        should_enter = True
                    elif enter_mode == "Except Last":
                        should_enter = (ln_num < total)

                    if should_enter:
                        self._send_enter(ad, ed)

                    self.step_idx = ln_num
                    self.root.after(0, self._hl, f"{ln_num + 1}.0")
                    prog = ln_num / total
                    self.root.after(0, self._tick_line, ln_num, total, prog)

                    # Line delay pause
                    if ln_num < total and line_delay > 0:
                        delay_end = time.time() + line_delay
                        self.root.after(0, lambda cur=ln_num: self.lbl_status.configure(
                            text=f"⏳ Line {cur}/{total} pause ({line_delay}s)...", text_color=C["amber"]))
                        while time.time() < delay_end:
                            if self.stop_flag:
                                break
                            time.sleep(0.05)
                        if not self.stop_flag:
                            self.root.after(0, lambda: self.lbl_status.configure(
                                text="⚡ INJECTING", text_color=C["green_fg"]))

                if self.step_idx >= total:
                    self.step_idx = 0

                self._done(self.stop_flag)
            except Exception as ex:
                if DEBUG_MODE:
                    logging.exception(f"Unhandled exception in run_auto: {ex}")
                self._done(True)
            finally:
                self._release_modifiers()

        threading.Thread(target=run_auto, daemon=True).start()

    def _stop(self):
        self.stop_flag = True
        self._release_modifiers()

    def _done(self, cancelled):
        self.is_typing = False
        def ui():
            self._set_buttons(False)
            if cancelled:
                self.lbl_status.configure(text="⛔ ABORTED", text_color=C["red_fg"])
            else:
                self.lbl_status.configure(text="✔ DONE", text_color=C["green_fg"])
                self.progress_bar.set(1.0)
                self.lbl_progress.configure(text=f"[ 100% ]")
        self.root.after(0, ui)

    def _set_buttons(self, typing):
        s = "disabled" if typing else "normal"
        ns = "normal" if typing else "disabled"
        self.btn_start.configure(state=s)
        self.btn_step.configure(state=s)
        if not typing:
            self.btn_start.configure(text="▶  AUTO (F8)")
            if self.step_idx > 0 and self.step_idx < getattr(self, '_last_total', 999):
                self.btn_step.configure(text=f"⏭  STEP L{self.step_idx + 1} (F2)")
            else:
                self.btn_step.configure(text="⏭  STEP (F2)")
        self.btn_open.configure(state=s)
        self.btn_clear.configure(state=s)
        self.btn_stop.configure(state=ns)
        self.opt_enter.configure(state=s)
        self.opt_mode.configure(state=s)
        self.opt_speed.configure(state=s)

    def _hl(self, idx):
        self.text_area.tag_add("typed", "1.0", idx)
        self.text_area.see(idx)

    def _tick_line(self, cur, total, prog):
        pct = int(prog * 100)
        self.lbl_progress.configure(text=f"[ {cur}/{total} · {pct}% ]")
        self.progress_bar.set(prog)

if __name__ == "__main__":
    RemoteTyperApp()