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

ACCENT = "#6C5CE7"
ACCENT_HOVER = "#5849c4"
RECORD_RED = "#e63946"
RECORD_RED_HOVER = "#c92e3a"
BG_CARD = "#1c1c26"
BG_APP = "#111117"
TEXT_MUTED = "#8b8b9a"


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
        self.geometry("560x680")
        self.minsize(520, 640)
        self.configure(fg_color=BG_APP)

        self.recorder = ScreenRecorder(on_status=self._on_recorder_status)
        self.monitors = list_monitors()
        self.output_dir = default_output_dir()
        self._timer_job = None

        self._build_ui()
        self._refresh_audio_hint()

    # ------------------------------------------------------------------ #
    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(28, 10))

        dot = ctk.CTkLabel(header, text="●", text_color=ACCENT, font=("Segoe UI", 22))
        dot.pack(side="left", padx=(0, 8))
        title = ctk.CTkLabel(
            header, text="ScreenCapture Pro",
            font=("Segoe UI Semibold", 22), text_color="#f4f4f8"
        )
        title.pack(side="left")

        subtitle = ctk.CTkLabel(
            self, text="Record your screen in a click — pick quality, pick a folder, go.",
            font=("Segoe UI", 12), text_color=TEXT_MUTED
        )
        subtitle.pack(anchor="w", padx=30, pady=(0, 18))

        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=16)
        card.pack(fill="x", padx=24, pady=(0, 16))
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)
        pad = {"padx": 18, "pady": (14, 4)}

        # Monitor
        ctk.CTkLabel(card, text="Display", font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).grid(
            row=0, column=0, sticky="w", **pad)
        self.monitor_var = ctk.StringVar(value=self.monitors[1][1] if len(self.monitors) > 1 else self.monitors[0][1])
        self.monitor_map = {label: idx for idx, label in self.monitors}
        self.monitor_menu = ctk.CTkOptionMenu(
            card, values=[label for _, label in self.monitors],
            variable=self.monitor_var, fg_color="#2a2a38", button_color=ACCENT,
            button_hover_color=ACCENT_HOVER, dropdown_fg_color="#2a2a38",
        )
        self.monitor_menu.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))

        # Format
        ctk.CTkLabel(card, text="Format", font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).grid(
            row=0, column=1, sticky="w", **pad)
        self.format_var = ctk.StringVar(value=list(FORMATS.keys())[0])
        self.format_menu = ctk.CTkOptionMenu(
            card, values=list(FORMATS.keys()), variable=self.format_var,
            fg_color="#2a2a38", button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            dropdown_fg_color="#2a2a38",
        )
        self.format_menu.grid(row=1, column=1, sticky="ew", padx=18, pady=(0, 12))

        # Quality
        ctk.CTkLabel(card, text="Quality", font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).grid(
            row=2, column=0, columnspan=2, sticky="w", **pad)
        self.quality_var = ctk.StringVar(value="High (native res)")
        self.quality_menu = ctk.CTkOptionMenu(
            card, values=list(QUALITY_PRESETS.keys()), variable=self.quality_var,
            fg_color="#2a2a38", button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            dropdown_fg_color="#2a2a38",
        )
        self.quality_menu.grid(row=3, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 14))

        # Audio
        audio_row = ctk.CTkFrame(card, fg_color="transparent")
        audio_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 6))
        self.audio_var = ctk.BooleanVar(value=False)
        self.audio_check = ctk.CTkCheckBox(
            audio_row, text="Record audio", variable=self.audio_var,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self._refresh_audio_hint,
        )
        self.audio_check.pack(side="left")

        self.audio_source_var = ctk.StringVar(value="Microphone")
        self.audio_source_menu = ctk.CTkOptionMenu(
            audio_row, values=["Microphone", "System audio"], variable=self.audio_source_var,
            fg_color="#2a2a38", button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            dropdown_fg_color="#2a2a38", width=140,
        )
        self.audio_source_menu.pack(side="right")

        self.audio_hint = ctk.CTkLabel(
            card, text="", font=("Segoe UI", 10), text_color=TEXT_MUTED, anchor="w", justify="left"
        )
        self.audio_hint.grid(row=5, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 16))

        # Save location card
        save_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=16)
        save_card.pack(fill="x", padx=24, pady=(0, 16))
        ctk.CTkLabel(
            save_card, text="Save to", font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED
        ).pack(anchor="w", padx=18, pady=(14, 4))

        path_row = ctk.CTkFrame(save_card, fg_color="transparent")
        path_row.pack(fill="x", padx=18, pady=(0, 10))
        self.path_var = ctk.StringVar(value=self.output_dir)
        self.path_entry = ctk.CTkEntry(path_row, textvariable=self.path_var, fg_color="#2a2a38")
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        browse_btn = ctk.CTkButton(
            path_row, text="Browse…", width=90, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._browse_folder,
        )
        browse_btn.pack(side="right")

        name_row = ctk.CTkFrame(save_card, fg_color="transparent")
        name_row.pack(fill="x", padx=18, pady=(0, 16))
        ctk.CTkLabel(name_row, text="File name", text_color=TEXT_MUTED, font=("Segoe UI", 11)).pack(anchor="w")
        self.filename_var = ctk.StringVar(value=self._default_filename())
        self.filename_entry = ctk.CTkEntry(name_row, textvariable=self.filename_var, fg_color="#2a2a38")
        self.filename_entry.pack(fill="x", pady=(4, 0))

        # Status + timer
        status_row = ctk.CTkFrame(self, fg_color="transparent")
        status_row.pack(fill="x", padx=30, pady=(4, 6))
        self.timer_label = ctk.CTkLabel(
            status_row, text="00:00:00", font=("Consolas", 28, "bold"), text_color="#f4f4f8"
        )
        self.timer_label.pack(side="left")
        self.status_label = ctk.CTkLabel(status_row, text="Ready", font=("Segoe UI", 12), text_color=TEXT_MUTED)
        self.status_label.pack(side="right")

        # Controls
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=24, pady=(6, 24))
        controls.grid_columnconfigure((0, 1, 2), weight=1)

        self.record_btn = ctk.CTkButton(
            controls, text="● Start Recording", height=48, font=("Segoe UI Semibold", 15),
            fg_color=RECORD_RED, hover_color=RECORD_RED_HOVER, corner_radius=12,
            command=self._toggle_record,
        )
        self.record_btn.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self.pause_btn = ctk.CTkButton(
            controls, text="⏸ Pause", height=40, fg_color="#2a2a38", hover_color="#34344a",
            corner_radius=10, command=self._toggle_pause, state="disabled",
        )
        self.pause_btn.grid(row=1, column=0, sticky="ew", padx=(0, 6))

        self.open_folder_btn = ctk.CTkButton(
            controls, text="📁 Open Folder", height=40, fg_color="#2a2a38", hover_color="#34344a",
            corner_radius=10, command=self._open_folder,
        )
        self.open_folder_btn.grid(row=1, column=1, sticky="ew", padx=6)

        self.quit_btn = ctk.CTkButton(
            controls, text="Quit", height=40, fg_color="#2a2a38", hover_color="#34344a",
            corner_radius=10, command=self._quit,
        )
        self.quit_btn.grid(row=1, column=2, sticky="ew", padx=(6, 0))

        self.protocol("WM_DELETE_WINDOW", self._quit)

    # ------------------------------------------------------------------ #
    def _default_filename(self) -> str:
        return f"Recording {datetime.now().strftime('%Y-%m-%d %H-%M-%S')}"

    def _refresh_audio_hint(self):
        if not SOUNDCARD_AVAILABLE:
            self.audio_hint.configure(text="Audio module not installed — video only.")
            self.audio_check.configure(state="disabled")
        elif not ffmpeg_available():
            self.audio_hint.configure(
                text="Install ffmpeg and add it to PATH to enable audio recording."
            )
            self.audio_check.configure(state="disabled")
        else:
            self.audio_hint.configure(text="")
            self.audio_check.configure(state="normal")

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

        self.record_btn.configure(text="■ Stop Recording", fg_color="#3a3a4a", hover_color="#45455a")
        self.pause_btn.configure(state="normal", text="⏸ Pause")
        self.status_label.configure(text="Recording…")
        self._lock_inputs(True)
        self._tick_timer()

    def _stop_recording(self):
        self.status_label.configure(text="Finishing up…")
        self.record_btn.configure(state="disabled")
        self.update_idletasks()

        saved_path = self.recorder.stop()

        self.record_btn.configure(state="normal", text="● Start Recording", fg_color=RECORD_RED, hover_color=RECORD_RED_HOVER)
        self.pause_btn.configure(state="disabled", text="⏸ Pause")
        self._lock_inputs(False)
        self.filename_var.set(self._default_filename())
        if self._timer_job:
            self.after_cancel(self._timer_job)
            self._timer_job = None
        self.timer_label.configure(text="00:00:00")

        if saved_path and os.path.exists(saved_path):
            self.status_label.configure(text="Saved ✓")
            if messagebox.askyesno("Recording saved", f"Saved to:\n{saved_path}\n\nOpen containing folder?"):
                os.startfile(os.path.dirname(saved_path))

    def _toggle_pause(self):
        if self.recorder.is_paused:
            self.recorder.resume()
            self.pause_btn.configure(text="⏸ Pause")
        else:
            self.recorder.pause()
            self.pause_btn.configure(text="▶ Resume")

    def _lock_inputs(self, locked: bool):
        state = "disabled" if locked else "normal"
        for widget in (
            self.monitor_menu, self.format_menu, self.quality_menu,
            self.audio_check, self.audio_source_menu, self.path_entry,
            self.filename_entry,
        ):
            try:
                widget.configure(state=state)
            except Exception:
                pass

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
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
