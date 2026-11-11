# Ticky — Premium Desktop Companion for Windows

[![Version](https://img.shields.io/badge/version-1.3.4-00E5FF.svg?style=flat-square)](https://github.com/Tony-Mrxz/Ticky-Dev/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011%20x64-0078D4.svg?style=flat-square)](https://github.com/Tony-Mrxz/Ticky-Dev)
[![Python](https://img.shields.io/badge/python-3.14-3776AB.svg?style=flat-square)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt-41CD52.svg?style=flat-square)](https://www.qt.io/)

**Ticky** is a fluid, modern, and intelligent desktop companion built natively for Windows. Designed around a responsive dynamic notch concept, Ticky introduces an interactive **Dynamic Island** and **Top Notch** directly to your desktop, blending daily task tracking, live hardware telemetry, atmospheric weather, calendar awareness, media controls, and AI chat into a clean, distraction-free overlay.

Developed by **Tony Mrxz**.

---

## 🌟 Key Features

### 🏝️ Dynamic Island & Top Notch
- **Dual Placement Modes**: Choose between **Dynamic Island** (floating pill hovering elegantly below the display bezel) or **Top Notch** (anchored flush to the top edge).
- **Multi-State Fluid Dynamics**:
  - **State 1 (Idle)**: Ultra-compact status pill showing live time, date, and animated status expressions.
  - **State 2 (Hover Expansion)**: Automatically expands on hover into an interactive multi-page workspace.
- **Smart Idle Translucency (Ghost Island)**:
  - Fades to a discrete translucent glass state during periods of inactivity (configurable in Settings: 30s, 1m, 2m, 5m, or Off).
  - Wakes back to full opacity instantly on mouse hover, random task peeks, time announcements, or active reminder alerts.
- **High-Contrast Border Outline**: Dynamically balanced border brightness maintains crisp separation and visibility across both vibrant wallpapers and jet-black backgrounds.

### 📑 Multi-Page Interactive Carousel
Glide across dedicated utility pages right from within the expanded island:
- **Page 1 — Tasks & Action Hub**: Live digital clock, interactive task checklist with one-click completions, expandable quick-add capsule, and direct shortcuts to the AI Assistant, Timer, and Settings.
- **Page 2 — Live Weather & Indian Festivals**: Real-time ambient weather updates, temperature, condition icons, high/low forecasts, and cultural celebration banners.
- **Page 3 — System Telemetry & Mem Reduct**: Real-time CPU, GPU, RAM, Disk, and Battery diagnostics with built-in one-click memory optimization via Mem Reduct.

### ⏱️ Compact Floating Timer
- Streamlined floating timer pill with pause, resume, and reset controls.
- Optimized 50px height with balanced vertical spacing and adaptive width to keep your focus unobstructed.

### 🤖 Local & Cloud AI Assistant
- Integrated AI conversational companion supporting both local Ollama models and cloud AI providers.
- **Offline Voice Dictation**: Bundled with OpenAI's Whisper `base.en` speech recognition model, providing zero-latency speech-to-text with no cloud dependencies or subscriptions.

### 📅 Integrated Calendar & Reminders
- Compact, fluid monthly calendar with quick date selection, day-of-week highlights, and schedule integration.
- Custom desktop notifications and periodic task reminders that wake the Dynamic Island when action is required.

### 🎵 Media & Spotify Integration
- Embedded media controls with seekable timeline scrubbing, album metadata, and rotating vinyl cover art.

### 🛡️ Privacy & Streaming Protection
- **Window Capture Exclusion**: Automatically hide Ticky from OBS, Discord screenshares, and screen recordings via native Windows Graphics Capture API hooks.

---

## 🛠️ Tech Stack & Architecture

- **Core**: Python 3.14 + PySide6 (Qt 6 for Python)
- **Styling**: Custom QSS (Qt Style Sheets) hierarchy combined with real-time `QPainter` antialiased rendering and `QPropertyAnimation` dynamics.
- **Speech Engine**: OpenAI Whisper (`base.en`) running via direct C++/PyTorch bindings.
- **System APIs**: Windows `win32gui`, ctypes `user32` / `dwmapi` window attributes, and registry hooks for system startup.
- **Packaging Pipeline**: PyInstaller (onedir compilation) bundled into a standalone per-user installer via Inno Setup 6.

---

## 🚀 Installation

### Windows Installer (Recommended)
Download the latest `Ticky-Setup-1.3.4.exe` from [Releases](https://github.com/Tony-Mrxz/Ticky-Dev/releases/latest).

1. Run `Ticky-Setup-1.3.4.exe`.
2. Installs per-user into `%LOCALAPPDATA%\Programs\Ticky` (no administrator privileges required).
3. Completely self-contained: bundles the Python runtime, all Qt libraries, and the offline Whisper speech model.
4. Auto-update checks seamlessly alert you when newer builds are released.

---

## 💻 Building from Source

### Prerequisites
- Python 3.14+ (or 3.11+)
- Git
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (optional, for compiling the setup installer)

### Setup Virtual Environment
```powershell
# Clone the repository
git clone https://github.com/Tony-Mrxz/Ticky-Dev.git
cd Ticky-Dev

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Run Locally
```powershell
python main.py
```

### Compile Binary & Installer
```powershell
# Build standalone onedir bundle & installer
.\build_installer.ps1

# Fast build (skips packaging the 141 MB Whisper speech model):
.\build_installer.ps1 -SkipModel

# Skip initial smoke launch check:
.\build_installer.ps1 -SkipSmoke
```
The compiled installer will be written to `installer\output\Ticky-Setup-1.3.4.exe`.

---

## ⚙️ Configuration

Ticky stores user settings, custom themes, hotkeys, and task lists in your user profile:
```
~/.ticky_config.json
```
Settings are preserved across updates and clean uninstalls.

Key configurable options include:
- `notch_position`: `"dynamic_island"` (default) or `"top_notch"`
- `idle_translucent_timeout`: Seconds before inactivity fade (`60` default, `0` to disable)
- `dynamic_island_offset`: Vertical floating offset in pixels (`14` default)
- `stay_on_top`: Pinning behavior
- `hide_while_streaming`: Windows capture exclusion toggle

---

## 📜 What's New in v1.3.4

- **Dynamic Island as Default**: Position mode defaults to Dynamic Island (floating pill below the bezel) for all new installs and sessions.
- **Smart Idle Translucency**: Dynamic Island gracefully fades to 25% opacity when idle, preserving screen real estate, and wakes up instantly on hover or notifications.
- **Inactivity Fade Timer Settings**: Added customizable fade timeout dropdown in Settings (30s, 1m, 2m, 5m, Off).
- **Compact Timer Design**: Equalized top/bottom margins, lowered height to 50px, and streamlined element gaps.
- **Enhanced Border Contrast**: Polished border outlines for crisp contrast and visibility across dark wallpapers.
- **Adaptive Task Page Width**: Smooth Page 1 expansion that hugs content and task pill sizes dynamically.

---

## 📄 License & Credits

Designed and developed by **Tony Mrxz** ([@Tony-Mrxz](https://github.com/Tony-Mrxz)).  
All rights reserved.
