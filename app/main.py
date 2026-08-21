"""ScreenCapture Pro — a beautiful, simple Windows screen recorder."""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime

import customtkinter as ctk
from tkinter import filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.recorder import (
    ScreenRecorder,
    RecordingConfig,
    QUALITY_PRESETS,
    FORMATS,
    list_monitors,
    ffmpeg_available,
    SOUNDCARD_AVAILABLE,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---------------------------------------------------------------- palette
# Studio purple + record red on deep navy (UI/UX Pro Max: creative-tool profile)
BG_APP = "#0B1120"
BG_CARD = "#171F32"
BG_FIELD = "#1E293B"
BG_FIELD_HOVER = "#2A3548"
BORDER = "#2A3348"

ACCENT = "#7C3AED"
ACCENT_HOVER = "#6D28D9"
ACCENT_SOFT = "#241B3E"

RECORD_RED = "#EF4444"
RECORD_RED_HOVER = "#DC2626"
RECORD_GLOW = "#3A1620"

SUCCESS = "#22C55E"

TEXT_PRIMARY = "#F8FAFC"
TEXT_MUTED = "#94A3B8"
TEXT_FAINT = "#5B6479"

FONT_TITLE = ("Segoe UI Semibold", 21)
FONT_LABEL = ("Segoe UI", 10, "bold")
FONT_BODY = ("Segoe UI", 12)
FONT_SMALL = ("Segoe UI", 10)
FONT_TIMER = ("Consolas", 38, "bold")

QUALITY_BLURBS = {
    "Low (720p-ish, small file)": "Smaller files · great for quick shares",
    "Medium (balanced)": "Good balance of quality and size",
    "High (native res)": "Full resolution · 30 fps",
    "Ultra (native, 60fps)": "Full resolution · 60 fps · largest files",
}


def default_output_dir() -> str:
    docs = os.path.join(os.path.expanduser("~"), "Videos", "ScreenCapture Pro")
    try:
        os.makedirs(docs, exist_ok=True)
    except OSError:
        docs = os.path.expanduser("~")
    return docs


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ScreenCapture Pro")
        self.geometry("580x760")
        self.minsize(540, 720)
        self.configure(fg_color=BG_APP)

        self.recorder = ScreenRecorder(on_status=self._on_recorder_status)
        self.monitors = list_monitors()
        self.output_dir = default_output_dir()
        self._timer_job = None

        self._build_ui()
        self._refresh_audio_hint()
        self._update_quality_blurb()

    # ------------------------------------------------------------------ #
    def _card(self, parent, pady=(0, 16)):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=28, pady=pady)
        return card

    def _section_heading(self, card, text):
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(16, 10))
        ctk.CTkLabel(row, text=text, font=("Segoe UI Semibold", 13), text_color=TEXT_PRIMARY).pack(side="left")
        return row

    def _build_ui(self):
        # ---------- Header --------------------------------------------
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(28, 4))

        badge = ctk.CTkFrame(header, fg_color=ACCENT_SOFT, corner_radius=12, width=40, height=40)
        badge.pack(side="left", padx=(0, 12))
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text="●", text_color=RECORD_RED, font=("Segoe UI", 18)).pack(expand=True)

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="ScreenCapture Pro", font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(
            title_box, text="Record your screen in a click.", font=FONT_BODY, text_color=TEXT_MUTED,
        ).pack(anchor="w")

        status_pill = ctk.CTkFrame(header, fg_color=BG_FIELD, corner_radius=20, height=32)
        status_pill.pack(side="right", anchor="e")
        self.status_dot = ctk.CTkLabel(status_pill, text="●", text_color=TEXT_FAINT, font=("Segoe UI", 12))
        self.status_dot.pack(side="left", padx=(14, 4), pady=6)
        self.status_label = ctk.CTkLabel(status_pill, text="Ready", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.status_label.pack(side="left", padx=(0, 14), pady=6)

        ctk.CTkFrame(self, fg_color="transparent", height=8).pack()

        # ---------- Capture settings card -------------------------------
        card = self._card(self)
        self._section_heading(card, "Capture settings")

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=18)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(grid, text="DISPLAY", font=FONT_LABEL, text_color=TEXT_FAINT).grid(
            row=0, column=0, sticky="w", pady=(0, 4))
        self.monitor_var = ctk.StringVar(value=self.monitors[1][1] if len(self.monitors) > 1 else self.monitors[0][1])
        self.monitor_map = {label: idx for idx, label in self.monitors}
        self.monitor_menu = ctk.CTkOptionMenu(
            grid, values=[label for _, label in self.monitors], variable=self.monitor_var,
            fg_color=BG_FIELD, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            dropdown_fg_color=BG_FIELD, corner_radius=10, height=36, font=FONT_BODY,
        )
        self.monitor_menu.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 16))

        ctk.CTkLabel(grid, text="FORMAT", font=FONT_LABEL, text_color=TEXT_FAINT).grid(
            row=0, column=1, sticky="w", pady=(0, 4))
        self.format_var = ctk.StringVar(value=list(FORMATS.keys())[0])
        self.format_seg = ctk.CTkSegmentedButton(
            grid, values=list(FORMATS.keys()), variable=self.format_var,
            fg_color=BG_FIELD, selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            unselected_color=BG_FIELD, unselected_hover_color=BG_FIELD_HOVER,
            height=36, corner_radius=10, font=FONT_SMALL,
        )
        self.format_seg.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 16))

        ctk.CTkLabel(grid, text="QUALITY", font=FONT_LABEL, text_color=TEXT_FAINT).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self.quality_var = ctk.StringVar(value="High (native res)")
        self.quality_seg = ctk.CTkSegmentedButton(
            grid, values=list(QUALITY_PRESETS.keys()), variable=self.quality_var,
            fg_color=BG_FIELD, selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            unselected_color=BG_FIELD, unselected_hover_color=BG_FIELD_HOVER,
            height=36, corner_radius=10, font=FONT_SMALL,
            command=lambda _=None: self._update_quality_blurb(),
        )
        self.quality_seg.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 2))

        self.quality_blurb = ctk.CTkLabel(grid, text="", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.quality_blurb.grid(row=4, column=0, columnspan=2, sticky="w", pady=(2, 16))

        # Audio row
        audio_row = ctk.CTkFrame(card, fg_color=BG_FIELD, corner_radius=12)
        audio_row.pack(fill="x", padx=18, pady=(0, 18))
        inner = ctk.CTkFrame(audio_row, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)

        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        self.audio_var = ctk.BooleanVar(value=False)
        self.audio_switch = ctk.CTkSwitch(
            left, text="Record audio", variable=self.audio_var, onvalue=True, offvalue=False,
            progress_color=ACCENT, button_color="#ffffff", font=FONT_BODY,
            command=self._refresh_audio_hint,
        )
        self.audio_switch.pack(anchor="w")
        self.audio_hint = ctk.CTkLabel(
            left, text="", font=FONT_SMALL, text_color=TEXT_FAINT, anchor="w", justify="left"
        )
        self.audio_hint.pack(anchor="w", pady=(2, 0))

        self.audio_source_var = ctk.StringVar(value="Microphone")
        self.audio_source_seg = ctk.CTkSegmentedButton(
            inner, values=["Microphone", "System audio"], variable=self.audio_source_var,
            fg_color=BG_APP, selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            unselected_color=BG_APP, unselected_hover_color=BG_FIELD_HOVER, height=32,
            corner_radius=8, font=FONT_SMALL,
        )
        self.audio_source_seg.pack(side="right")

        # ---------- Save location card -----------------------------------
        save_card = self._card(self)
        self._section_heading(save_card, "Save location")

        path_row = ctk.CTkFrame(save_card, fg_color="transparent")
        path_row.pack(fill="x", padx=18, pady=(0, 10))
        self.path_var = ctk.StringVar(value=self.output_dir)
        self.path_entry = ctk.CTkEntry(
            path_row, textvariable=self.path_var, fg_color=BG_FIELD, border_width=0,
            corner_radius=10, height=38, font=FONT_BODY,
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.browse_btn = ctk.CTkButton(
            path_row, text="Browse…", width=96, height=38, corner_radius=10, font=FONT_BODY,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self._browse_folder,
        )
        self.browse_btn.pack(side="right")

        name_row = ctk.CTkFrame(save_card, fg_color="transparent")
        name_row.pack(fill="x", padx=18, pady=(0, 18))
        ctk.CTkLabel(name_row, text="FILE NAME", font=FONT_LABEL, text_color=TEXT_FAINT).pack(anchor="w", pady=(0, 4))
        self.filename_var = ctk.StringVar(value=self._default_filename())
        self.filename_entry = ctk.CTkEntry(
            name_row, textvariable=self.filename_var, fg_color=BG_FIELD, border_width=0,
            corner_radius=10, height=38, font=FONT_BODY,
        )
        self.filename_entry.pack(fill="x")

        # ---------- Timer --------------------------------------------------
        timer_box = ctk.CTkFrame(self, fg_color="transparent")
        timer_box.pack(fill="x", padx=28, pady=(4, 6))
        self.timer_label = ctk.CTkLabel(timer_box, text="00:00:00", font=FONT_TIMER, text_color=TEXT_PRIMARY)
        self.timer_label.pack()

        # ---------- Controls -------------------------------------------
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(pady=(6, 4))

        self.pause_btn = self._circle_button(controls, "⏸", 54, BG_FIELD, BG_FIELD_HOVER, self._toggle_pause)
        self.pause_btn.configure(state="disabled")
        self.pause_btn.grid(row=0, column=0, padx=16)

        # Glow ring behind the record button
        glow = ctk.CTkFrame(controls, fg_color=RECORD_GLOW, corner_radius=48, width=96, height=96)
        glow.grid(row=0, column=1, padx=16)
        glow.grid_propagate(False)
        self.record_btn = self._circle_button(
            glow, "●", 84, RECORD_RED, RECORD_RED_HOVER, self._toggle_record, font_size=26,
        )
        self.record_btn.place(relx=0.5, rely=0.5, anchor="center")

        self.open_folder_btn = self._circle_button(controls, "📁", 54, BG_FIELD, BG_FIELD_HOVER, self._open_folder)
        self.open_folder_btn.grid(row=0, column=2, padx=16)

        label_row = ctk.CTkFrame(self, fg_color="transparent")
        label_row.pack(pady=(6, 4))
        ctk.CTkLabel(label_row, text="Pause", font=FONT_SMALL, text_color=TEXT_FAINT, width=86).grid(row=0, column=0)
        ctk.CTkLabel(label_row, text="Start / Stop", font=FONT_SMALL, text_color=TEXT_FAINT, width=116).grid(row=0, column=1)
        ctk.CTkLabel(label_row, text="Open folder", font=FONT_SMALL, text_color=TEXT_FAINT, width=86).grid(row=0, column=2)

        self.quit_btn = ctk.CTkButton(
            self, text="Quit", height=34, width=90, font=FONT_SMALL,
            fg_color="transparent", hover_color=BG_FIELD, text_color=TEXT_FAINT,
            corner_radius=10, command=self._quit,
        )
        self.quit_btn.pack(pady=(6, 20))

        self.protocol("WM_DELETE_WINDOW", self._quit)

    def _circle_button(self, parent, text, size, fg, hover, command, font_size=18, state="normal"):
        return ctk.CTkButton(
            parent, text=text, width=size, height=size, corner_radius=size // 2,
            fg_color=fg, hover_color=hover, font=("Segoe UI", font_size), command=command,
            state=state, text_color="#ffffff",
        )

    # ------------------------------------------------------------------ #
    def _default_filename(self) -> str:
        return f"Recording {datetime.now().strftime('%Y-%m-%d %H-%M-%S')}"

    def _update_quality_blurb(self):
        self.quality_blurb.configure(text=QUALITY_BLURBS.get(self.quality_var.get(), ""))

    def _refresh_audio_hint(self):
        can_use_audio = SOUNDCARD_AVAILABLE and ffmpeg_available()
        if not SOUNDCARD_AVAILABLE:
            self.audio_hint.configure(text="Audio module not installed — video only.")
        elif not ffmpeg_available():
            self.audio_hint.configure(text="Install ffmpeg (added to PATH) to enable audio.")
        else:
            self.audio_hint.configure(text="Captures alongside your video.")

        self.audio_switch.configure(state="normal" if can_use_audio else "disabled")
        if not can_use_audio:
            self.audio_var.set(False)
        self.audio_source_seg.configure(state="normal" if (can_use_audio and self.audio_var.get()) else "disabled")

    def _browse_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.path_var.get() or self.output_dir)
        if chosen:
            self.path_var.set(chosen)

    def _open_folder(self):
        path = self.path_var.get()
        if os.path.isdir(path):
            os.startfile(path)

    def _on_recorder_status(self, msg: str):
        self.after(0, lambda: self.status_label.configure(text=msg))

    # ------------------------------------------------------------------ #
    def _toggle_record(self):
        if not self.recorder.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        folder = self.path_var.get().strip()
        name = self.filename_var.get().strip() or self._default_filename()
        if not folder:
            messagebox.showerror("Missing folder", "Please choose a save location first.")
            return
        os.makedirs(folder, exist_ok=True)
        output_path = os.path.join(folder, name)

        monitor_idx = self.monitor_map.get(self.monitor_var.get(), 1)
        audio_source = "system" if self.audio_source_var.get() == "System audio" else "microphone"

        config = RecordingConfig(
            monitor_index=monitor_idx,
            quality_label=self.quality_var.get(),
            format_label=self.format_var.get(),
            output_path=output_path,
            record_audio=bool(self.audio_var.get()),
            audio_source=audio_source,
        )
        self.recorder.start(config)

        self.record_btn.configure(text="■", fg_color="#3a3849", hover_color="#454259")
        self.pause_btn.configure(state="normal", text="⏸")
        self.status_label.configure(text="Recording…")
        self.status_dot.configure(text_color=RECORD_RED)
        self._lock_inputs(True)
        self._tick_timer()

    def _stop_recording(self):
        self.status_label.configure(text="Finishing up…")
        self.status_dot.configure(text_color=ACCENT)
        self.record_btn.configure(state="disabled")
        self.update_idletasks()

        saved_path = self.recorder.stop()

        self.record_btn.configure(state="normal", text="●", fg_color=RECORD_RED, hover_color=RECORD_RED_HOVER)
        self.pause_btn.configure(state="disabled", text="⏸")
        self._lock_inputs(False)
        self.filename_var.set(self._default_filename())
        if self._timer_job:
            self.after_cancel(self._timer_job)
            self._timer_job = None
        self.timer_label.configure(text="00:00:00")

        if saved_path and os.path.exists(saved_path):
            self.status_label.configure(text="Saved ✓")
            self.status_dot.configure(text_color=SUCCESS)
            if messagebox.askyesno("Recording saved", f"Saved to:\n{saved_path}\n\nOpen containing folder?"):
                os.startfile(os.path.dirname(saved_path))
        else:
            self.status_dot.configure(text_color=TEXT_FAINT)

    def _toggle_pause(self):
        if self.recorder.is_paused:
            self.recorder.resume()
            self.pause_btn.configure(text="⏸")
            self.status_dot.configure(text_color=RECORD_RED)
        else:
            self.recorder.pause()
            self.pause_btn.configure(text="▶")
            self.status_dot.configure(text_color=TEXT_FAINT)

    def _lock_inputs(self, locked: bool):
        state = "disabled" if locked else "normal"
        for widget in (
            self.monitor_menu, self.format_seg, self.quality_seg,
            self.audio_switch, self.path_entry, self.filename_entry, self.browse_btn,
        ):
            try:
                widget.configure(state=state)
            except Exception:
                pass
        if not locked:
            self._refresh_audio_hint()
        else:
            self.audio_source_seg.configure(state="disabled")

    def _tick_timer(self):
        if self.recorder.is_recording:
            secs = int(self.recorder.elapsed_seconds)
            h, rem = divmod(secs, 3600)
            m, s = divmod(rem, 60)
            self.timer_label.configure(text=f"{h:02d}:{m:02d}:{s:02d}")
            self._timer_job = self.after(250, self._tick_timer)

    def _quit(self):
        if self.recorder.is_recording:
            if not messagebox.askyesno("Recording in progress", "Stop recording and quit?"):
                return
            self.recorder.stop()
        if self._timer_job:
            self.after_cancel(self._timer_job)
            self._timer_job = None
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
