# ScreenCapture Pro

A simple, good-looking Windows screen recorder built with Python and [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter).

Pick a display, a quality preset, a save folder — hit record.

## Features

- Record any connected display (or all of them)
- Quality presets: Low, Medium, High (native res), Ultra (native, 60fps)
- Output formats: MP4 or AVI
- Optional audio recording — microphone or system audio (requires `ffmpeg` on PATH)
- Pause / resume mid-recording
- Live elapsed-time counter
- Choose save folder and file name before recording
- One-click "Open Folder" after saving

## Requirements

- Windows
- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) on your PATH (only needed for audio recording)

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app/main.py
```

## Build a standalone .exe

```bash
build.bat
```

This uses PyInstaller to produce `dist/ScreenCapturePro.exe`.

## Project structure

```
app/
  main.py       # UI (CustomTkinter)
  recorder.py   # Capture engine (mss + OpenCV, optional soundcard/ffmpeg audio)
assets/         # Icon and other static assets
build.bat       # PyInstaller build script
```

## How it works

- Screen frames are grabbed with [`mss`](https://github.com/BoboTiG/python-mss) and written with OpenCV's `VideoWriter`.
- When audio is enabled, video and audio are captured to temporary files and muxed together with `ffmpeg` once recording stops.
