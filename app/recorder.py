"""Core screen-recording engine.

Captures the chosen monitor/region with mss, writes frames with OpenCV,
and optionally records microphone/system audio with `soundcard`, muxing
the result with ffmpeg (if available on PATH) once recording stops.
"""
from __future__ import annotations

import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import cv2
import numpy as np
import mss

try:
    import soundcard as sc
    SOUNDCARD_AVAILABLE = True
except Exception:
    SOUNDCARD_AVAILABLE = False


QUALITY_PRESETS = {
    "Low (720p-ish, small file)": {"scale": 0.5, "fps": 15, "bitrate_hint": "low"},
    "Medium (balanced)": {"scale": 0.75, "fps": 24, "bitrate_hint": "medium"},
    "High (native res)": {"scale": 1.0, "fps": 30, "bitrate_hint": "high"},
    "Ultra (native, 60fps)": {"scale": 1.0, "fps": 60, "bitrate_hint": "ultra"},
}

FORMATS = {
    "MP4 (recommended)": {"ext": ".mp4", "fourcc": "mp4v"},
    "AVI (larger, no re-encode)": {"ext": ".avi", "fourcc": "XVID"},
}


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


@dataclass
class RecordingConfig:
    monitor_index: int
    quality_label: str
    format_label: str
    output_path: str
    record_audio: bool
    audio_source: str  # "microphone" or "system"


class ScreenRecorder:
    def __init__(self, on_status: Optional[Callable[[str], None]] = None):
        self._thread: Optional[threading.Thread] = None
        self._audio_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._on_status = on_status or (lambda msg: None)

        self.is_recording = False
        self.is_paused = False
        self.elapsed_seconds = 0.0
        self.output_file: Optional[str] = None
        self._start_time = 0.0
        self._paused_accum = 0.0
        self._pause_started_at = 0.0

        self._audio_frames: "queue.Queue[np.ndarray]" = queue.Queue()
        self._audio_samplerate = 48000
        self._tmp_audio_path: Optional[str] = None
        self._tmp_video_path: Optional[str] = None

    # ------------------------------------------------------------------ #
    def start(self, config: RecordingConfig):
        if self.is_recording:
            return
        self._stop_event.clear()
        self._pause_event.clear()
        self.is_paused = False
        self._paused_accum = 0.0
        self.elapsed_seconds = 0.0

        fmt = FORMATS[config.format_label]
        final_path = config.output_path
        if not final_path.lower().endswith(fmt["ext"]):
            final_path += fmt["ext"]
        self.output_file = final_path

        use_audio = config.record_audio and SOUNDCARD_AVAILABLE and ffmpeg_available()
        if config.record_audio and not use_audio:
            self._on_status(
                "Audio requested but unavailable (needs ffmpeg on PATH) — recording video only."
            )

        if use_audio:
            tmp_dir = tempfile.gettempdir()
            stamp = str(int(time.time()))
            self._tmp_video_path = os.path.join(tmp_dir, f"scr_tmp_video_{stamp}.mp4")
            self._tmp_audio_path = os.path.join(tmp_dir, f"scr_tmp_audio_{stamp}.wav")
            video_target = self._tmp_video_path
        else:
            self._tmp_video_path = None
            self._tmp_audio_path = None
            video_target = final_path

        self._thread = threading.Thread(
            target=self._capture_loop,
            args=(config, video_target, use_audio),
            daemon=True,
        )
        self.is_recording = True
        self._start_time = time.time()
        self._thread.start()

        if use_audio:
            self._audio_thread = threading.Thread(
                target=self._audio_loop,
                args=(config.audio_source,),
                daemon=True,
            )
            self._audio_thread.start()

    def pause(self):
        if self.is_recording and not self.is_paused:
            self.is_paused = True
            self._pause_started_at = time.time()
            self._pause_event.set()
            self._on_status("Paused")

    def resume(self):
        if self.is_recording and self.is_paused:
            self.is_paused = False
            self._paused_accum += time.time() - self._pause_started_at
            self._pause_event.clear()
            self._on_status("Recording…")

    def stop(self) -> Optional[str]:
        if not self.is_recording:
            return None
        self._stop_event.set()
        self._pause_event.clear()
        if self._thread:
            self._thread.join(timeout=10)
        if self._audio_thread:
            self._audio_thread.join(timeout=10)
        self.is_recording = False
        self.is_paused = False

        if self._tmp_video_path and self._tmp_audio_path and self.output_file:
            self._on_status("Merging audio + video…")
            ok = self._mux(self._tmp_video_path, self._tmp_audio_path, self.output_file)
            for p in (self._tmp_video_path, self._tmp_audio_path):
                try:
                    os.remove(p)
                except OSError:
                    pass
            if not ok:
                self._on_status("Audio merge failed — video saved without audio.")

        self._on_status(f"Saved: {self.output_file}")
        return self.output_file

    # ------------------------------------------------------------------ #
    def _capture_loop(self, config: RecordingConfig, video_target: str, use_audio: bool):
        preset = QUALITY_PRESETS[config.quality_label]
        fmt = FORMATS[config.format_label]
        fps = preset["fps"]
        scale = preset["scale"]

        with mss.mss() as sct:
            monitor = sct.monitors[config.monitor_index]
            width = int(monitor["width"] * scale)
            height = int(monitor["height"] * scale)
            width -= width % 2
            height -= height % 2

            fourcc = cv2.VideoWriter_fourcc(*fmt["fourcc"])
            writer = cv2.VideoWriter(video_target, fourcc, fps, (width, height))

            frame_interval = 1.0 / fps
            next_frame_time = time.time()

            try:
                while not self._stop_event.is_set():
                    if self._pause_event.is_set():
                        time.sleep(0.05)
                        next_frame_time = time.time()
                        continue

                    now = time.time()
                    self.elapsed_seconds = now - self._start_time - self._paused_accum

                    if now < next_frame_time:
                        time.sleep(max(0.0, next_frame_time - now))

                    raw = sct.grab(monitor)
                    frame = np.array(raw)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    if scale != 1.0:
                        frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                    writer.write(frame)

                    next_frame_time += frame_interval
            finally:
                writer.release()

    def _audio_loop(self, audio_source: str):
        try:
            if audio_source == "system":
                speaker = sc.default_speaker()
                mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
            else:
                mic = sc.default_microphone()

            frames = []
            with mic.recorder(samplerate=self._audio_samplerate) as rec:
                while not self._stop_event.is_set():
                    if self._pause_event.is_set():
                        time.sleep(0.05)
                        continue
                    data = rec.record(numframes=self._audio_samplerate // 10)
                    frames.append(data)

            if frames and self._tmp_audio_path:
                audio = np.concatenate(frames, axis=0)
                self._write_wav(self._tmp_audio_path, audio, self._audio_samplerate)
        except Exception as exc:
            self._on_status(f"Audio capture error: {exc}")

    @staticmethod
    def _write_wav(path: str, audio: np.ndarray, samplerate: int):
        import wave

        audio_i16 = np.clip(audio, -1.0, 1.0)
        audio_i16 = (audio_i16 * 32767).astype(np.int16)
        channels = audio_i16.shape[1] if audio_i16.ndim > 1 else 1

        with wave.open(path, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(samplerate)
            wf.writeframes(audio_i16.tobytes())

    @staticmethod
    def _mux(video_path: str, audio_path: str, output_path: str) -> bool:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path,
        ]
        try:
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120
            )
            return result.returncode == 0
        except Exception:
            return False


def list_monitors():
    """Returns list of (index, label) for mss monitors, skipping the 'all' combo at index 0."""
    with mss.mss() as sct:
        monitors = sct.monitors
        labels = []
        for i, m in enumerate(monitors):
            if i == 0:
                labels.append((i, f"All displays ({m['width']}x{m['height']})"))
            else:
                labels.append((i, f"Display {i} ({m['width']}x{m['height']})"))
        return labels
