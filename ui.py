import ctypes
import math
import os
import queue
import time
import tkinter as tk
from typing import Callable

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

APP_NAME = "J.A.R.V.I.S."


class NeuralStudioHUD:
    """
    Minimalist dark-mode sci-fi HUD featuring ONLY the glowing concentric ring
    animation and real-time English grammar correction at the bottom.
    """

    STATE_THEMES = {
        "IDLE": {
            "primary": "#00f0ff",
            "label": "STANDBY // SAY 'HEY JARVIS'",
        },
        "LISTENING": {
            "primary": "#ff1e56",
            "label": "LISTENING // SPEAK FREELY",
        },
        "THINKING": {
            "primary": "#ffb703",
            "label": "NEURAL CORE // POLISHING...",
        },
        "SPEAKING": {
            "primary": "#00f59b",
            "label": "J.A.R.V.I.S. // SPEAKING",
        },
    }

    def __init__(
        self,
        width: int = 460,
        height: int = 520,
        on_awake_toggle: Callable[[bool], None] | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.on_awake_toggle = on_awake_toggle

        self._ui_queue: queue.SimpleQueue = queue.SimpleQueue()
        self._current_state = "IDLE"
        self._is_awake = False
        self._start_time = time.perf_counter()

        self._drag_x = 0
        self._drag_y = 0

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#05080c")

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pos_x = max(16, screen_w - self.width - 36)
        pos_y = max(24, (screen_h - self.height) // 2)
        self.root.geometry(f"{self.width}x{self.height}+{pos_x}+{pos_y}")

        self._build_layout()

    @staticmethod
    def _dim_color(hex_color: str, factor: float) -> str:
        hex_color = hex_color.lstrip("#")
        r = int(int(hex_color[0:2], 16) * factor)
        g = int(int(hex_color[2:4], 16) * factor)
        b = int(int(hex_color[4:6], 16) * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _build_layout(self) -> None:
        self.shell = tk.Frame(
            self.root,
            bg="#05080c",
            highlightthickness=1,
            highlightbackground="#132333",
        )
        self.shell.pack(fill=tk.BOTH, expand=True)

        # ── 1. MINIMAL DRAGGABLE TOP BAR ─────────────────────────────────────
        self.header = tk.Frame(self.shell, bg="#080d14", height=36)
        self.header.pack(fill=tk.X)
        self.header.pack_propagate(False)
        self.header.bind("<ButtonPress-1>", self._on_drag_start)
        self.header.bind("<B1-Motion>", self._on_drag_motion)

        title_lbl = tk.Label(
            self.header,
            text=f"◈ {APP_NAME}",
            bg="#080d14",
            fg="#67e8f9",
            font=("Consolas", 9, "bold"),
        )
        title_lbl.pack(side=tk.LEFT, padx=14)
        title_lbl.bind("<ButtonPress-1>", self._on_drag_start)
        title_lbl.bind("<B1-Motion>", self._on_drag_motion)

        close_btn = tk.Label(
            self.header,
            text="✕",
            bg="#080d14",
            fg="#64748b",
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            padx=12,
        )
        close_btn.pack(side=tk.RIGHT, fill=tk.Y)
        close_btn.bind("<Button-1>", lambda _e: self.shutdown())
        close_btn.bind("<Enter>", lambda _e: close_btn.config(fg="#ff1e56", bg="#141d29"))
        close_btn.bind("<Leave>", lambda _e: close_btn.config(fg="#64748b", bg="#080d14"))

        self.session_pill = tk.Label(
            self.header,
            text="SLEEPING",
            bg="#0d1b26",
            fg="#64748b",
            font=("Consolas", 8, "bold"),
            padx=8,
            pady=2,
            cursor="hand2",
        )
        self.session_pill.pack(side=tk.RIGHT, padx=6)
        self.session_pill.bind("<Button-1>", lambda _e: self._handle_pill_click())

        # ── 2. CENTER ROUND REACTOR ANIMATION CANVAS ─────────────────────────
        self.canvas_h = 335
        self.cx = self.width // 2
        self.cy = 152
        self.canvas = tk.Canvas(
            self.shell,
            width=self.width,
            height=self.canvas_h,
            bg="#05080c",
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.X)
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self._build_reactor_primitives()

        # ── 3. BOTTOM REAL-TIME CORRECTED GRAMMAR DISPLAY ────────────────────
        grammar_zone = tk.Frame(
            self.shell,
            bg="#091018",
            highlightthickness=1,
            highlightbackground="#162838",
            padx=16,
            pady=12,
        )
        grammar_zone.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        self.grammar_tag_lbl = tk.Label(
            grammar_zone,
            text="REAL-TIME ENGLISH GRAMMAR",
            bg="#091018",
            fg="#38bdf8",
            font=("Consolas", 8, "bold"),
            anchor="center",
        )
        self.grammar_tag_lbl.pack(fill=tk.X)

        self.grammar_text_lbl = tk.Label(
            grammar_zone,
            text="Say 'Hey Jarvis' to start our conversation...",
            bg="#091018",
            fg="#e2e8f0",
            font=("Segoe UI", 11, "bold"),
            wraplength=self.width - 68,
            justify="center",
            anchor="center",
        )
        self.grammar_text_lbl.pack(fill=tk.BOTH, expand=True, pady=(4, 2))

        self.grammar_tip_lbl = tk.Label(
            grammar_zone,
            text="Your corrected sentence appears here live as you speak",
            bg="#091018",
            fg="#64748b",
            font=("Segoe UI", 9, "italic"),
            wraplength=self.width - 68,
            justify="center",
            anchor="center",
        )
        self.grammar_tip_lbl.pack(fill=tk.X)

    def _build_reactor_primitives(self) -> None:
        primary = self.STATE_THEMES["IDLE"]["primary"]

        # Subtle sci-fi outer tick ring
        self.outer_static_ring = self.canvas.create_oval(0, 0, 0, 0, outline="#10222e", width=1.0)
        self.radar_1 = self.canvas.create_oval(0, 0, 0, 0, outline=primary, width=1.6)
        self.radar_2 = self.canvas.create_oval(0, 0, 0, 0, outline=primary, width=1.1)
        self.glow_outer = self.canvas.create_oval(0, 0, 0, 0, outline=self._dim_color(primary, 0.22), width=6)

        self.outer_arcs = [
            self.canvas.create_arc(0, 0, 0, 0, start=i * 120, extent=78, style=tk.ARC, outline=primary, width=2.8)
            for i in range(3)
        ]
        self.mid_arcs = [
            self.canvas.create_arc(
                0, 0, 0, 0, start=i * 90, extent=52, style=tk.ARC, outline=self._dim_color(primary, 0.85), width=2.2
            )
            for i in range(4)
        ]
        self.inner_arcs = [
            self.canvas.create_arc(0, 0, 0, 0, start=i * 180, extent=118, style=tk.ARC, outline=primary, width=2.8)
            for i in range(2)
        ]

        self.core_ring = self.canvas.create_oval(0, 0, 0, 0, outline=primary, width=2.0)
        self.core_dot = self.canvas.create_oval(0, 0, 0, 0, fill=primary, outline="")

        self.state_badge = self.canvas.create_text(
            self.cx,
            302,
            text=self.STATE_THEMES["IDLE"]["label"],
            fill=primary,
            font=("Consolas", 9, "bold"),
        )

    def _set_circle(self, item_id: int, radius: float) -> None:
        self.canvas.coords(
            item_id,
            self.cx - radius,
            self.cy - radius,
            self.cx + radius,
            self.cy + radius,
        )

    def _refresh_session_pill(self) -> None:
        if self._is_awake:
            self.session_pill.config(text="ACTIVE SESSION", bg="#082f26", fg="#00f59b")
        else:
            self.session_pill.config(text="SLEEPING", bg="#0d1b26", fg="#64748b")

    def _handle_pill_click(self) -> None:
        self._is_awake = not self._is_awake
        self._refresh_session_pill()
        if self.on_awake_toggle:
            self.on_awake_toggle(self._is_awake)

    def _on_drag_start(self, event: tk.Event) -> None:
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag_motion(self, event: tk.Event) -> None:
        x = self.root.winfo_x() + (event.x - self._drag_x)
        y = self.root.winfo_y() + (event.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    # ── THREAD-SAFE PUBLIC API ───────────────────────────────────────────────

    def set_state(self, state: str, status_text: str | None = None) -> None:
        normalized = state.strip().upper()
        if normalized not in self.STATE_THEMES:
            normalized = "IDLE"
        label = status_text if status_text is not None else self.STATE_THEMES[normalized]["label"]
        self._ui_queue.put(("STATE", (normalized, label)))

    def set_awake_state(self, awake: bool) -> None:
        self._ui_queue.put(("AWAKE", bool(awake)))

    def show_grammar_polish(self, has_mistake: bool, corrected: str, tip: str) -> None:
        self._ui_queue.put(("POLISH", (has_mistake, corrected, tip)))

    def reset_grammar_banner(self, message: str, subtext: str = "") -> None:
        self._ui_queue.put(("BANNER", (message, subtext)))

    def _drain_queue(self) -> None:
        while True:
            try:
                kind, payload = self._ui_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "STATE":
                state, label = payload
                self._current_state = state
                primary = self.STATE_THEMES[state]["primary"]
                self.canvas.itemconfig(self.state_badge, text=label, fill=primary)

            elif kind == "AWAKE":
                self._is_awake = payload
                self._refresh_session_pill()

            elif kind == "POLISH":
                has_mistake, corrected, tip = payload
                if has_mistake:
                    self.grammar_tag_lbl.config(text="✦ CORRECTED ENGLISH", fg="#ffb703")
                    self.grammar_text_lbl.config(text=f"\"{corrected}\"", fg="#fef08a")
                    self.grammar_tip_lbl.config(text=tip, fg="#fbbf24")
                else:
                    self.grammar_tag_lbl.config(text="✓ NATURAL ENGLISH", fg="#00f59b")
                    self.grammar_text_lbl.config(text=f"\"{corrected}\"", fg="#d1fae5")
                    self.grammar_tip_lbl.config(text=tip or "Spot on, Sir!", fg="#34d399")

            elif kind == "BANNER":
                message, subtext = payload
                self.grammar_tag_lbl.config(text="REAL-TIME ENGLISH GRAMMAR", fg="#38bdf8")
                self.grammar_text_lbl.config(text=message, fg="#e2e8f0")
                self.grammar_tip_lbl.config(text=subtext, fg="#64748b")

    def _animate(self) -> None:
        self._drain_queue()

        t = time.perf_counter() - self._start_time
        state = self._current_state
        primary = self.STATE_THEMES[state]["primary"]

        if state == "IDLE":
            breath = math.sin(t * 2.2)
            base_r = 78 + breath * 4.5
            outer_a = (t * 28) % 360
            mid_a = (-t * 42) % 360
            inner_a = (t * 55) % 360
            r1 = 44 + ((t * 30) % 76)
            r1_fade = max(0.0, 1.0 - (r1 - 44) / 76) * 0.35
            r2, r2_fade = 0, 0.0
            dot_r = 7.5 + breath * 1.5

        elif state == "LISTENING":
            pulse = math.sin(t * 9.0)
            base_r = 82 + pulse * 6.0
            outer_a = (t * 95) % 360
            mid_a = (-t * 130) % 360
            inner_a = (t * 160) % 360
            p1 = (t * 1.35) % 1.0
            p2 = (t * 1.35 + 0.5) % 1.0
            r1 = 36 + p1 * 96
            r1_fade = (1.0 - p1) * 0.9
            r2 = 36 + p2 * 96
            r2_fade = (1.0 - p2) * 0.9
            dot_r = 10.5 + pulse * 2.8

        elif state == "THINKING":
            osc = math.sin(t * 6.0)
            base_r = 76 + osc * 4.0
            outer_a = (t * 155 + math.sin(t * 4.0) * 32) % 360
            mid_a = (-t * 210 - math.cos(t * 4.0) * 44) % 360
            inner_a = (t * 260) % 360
            r1, r1_fade = 94 + osc * 9, 0.45
            r2, r2_fade = 60 - osc * 8, 0.35
            dot_r = 9.0 + abs(osc) * 3.8

        else:  # SPEAKING
            wave = math.sin(t * 11.0) * 0.65 + math.sin(t * 19.0) * 0.35
            base_r = 82 + wave * 10.0
            outer_a = (t * 65) % 360
            mid_a = (-t * 85) % 360
            inner_a = (t * 110) % 360
            r1, r1_fade = base_r + 24 + wave * 7, 0.65
            r2, r2_fade = base_r + 38 - wave * 5, 0.30
            dot_r = 11.5 + wave * 4.2

        self._set_circle(self.outer_static_ring, 128)
        self._set_circle(self.glow_outer, base_r + 20)
        self.canvas.itemconfig(self.glow_outer, outline=self._dim_color(primary, 0.24))

        if r1_fade > 0.02:
            self._set_circle(self.radar_1, r1)
            self.canvas.itemconfig(self.radar_1, outline=self._dim_color(primary, r1_fade))
        else:
            self._set_circle(self.radar_1, 0)

        if r2_fade > 0.02:
            self._set_circle(self.radar_2, r2)
            self.canvas.itemconfig(self.radar_2, outline=self._dim_color(primary, r2_fade))
        else:
            self._set_circle(self.radar_2, 0)

        for i, arc in enumerate(self.outer_arcs):
            self._set_circle(arc, base_r + 15)
            self.canvas.itemconfig(arc, start=(outer_a + i * 120) % 360, outline=primary)

        for i, arc in enumerate(self.mid_arcs):
            self._set_circle(arc, base_r)
            self.canvas.itemconfig(arc, start=(mid_a + i * 90) % 360, outline=self._dim_color(primary, 0.85))

        for i, arc in enumerate(self.inner_arcs):
            self._set_circle(arc, base_r - 20)
            self.canvas.itemconfig(arc, start=(inner_a + i * 180) % 360, outline=primary)

        self._set_circle(self.core_ring, base_r - 33)
        self.canvas.itemconfig(self.core_ring, outline=self._dim_color(primary, 0.7))
        self._set_circle(self.core_dot, max(4.0, dot_r))
        self.canvas.itemconfig(self.core_dot, fill=primary)

        self.root.after(30, self._animate)

    def run(self) -> None:
        self._animate()
        self.root.mainloop()

    def shutdown(self) -> None:
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)