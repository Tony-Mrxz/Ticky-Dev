"""
Smart voice dictation service for Ticky powered by OpenAI Whisper (faster-whisper).

Captures microphone audio via Qt (QAudioSource) and recognizes it locally and offline
with faster-whisper (CTranslate2 int8 on CPU).

Features:
- Runs 100% offline with AVX2 acceleration.
- Accurately capitalizes sentences and inserts proper punctuation.
- Background worker thread prevents any UI or visualizer stutter.
- Automatically injects finalized text into the focused desktop text field.
"""

from __future__ import annotations

import math
import os
import queue
import random
import struct
import sys
import time
from enum import Enum
from typing import List, Optional

import numpy as np
from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtMultimedia import QAudio, QAudioFormat, QAudioSource, QMediaDevices

from utils import config, text_inject

WHISPER_MODEL_NAME = "base.en"

# Runtime diagnostic log — tiny and append-only; lives next to the user config.
DEBUG_LOG_PATH = os.path.expanduser("~/.ticky_dictation_debug.log")


def _dbg(msg: str) -> None:
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


class DictationState(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    STOPPING = "stopping"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    ERROR = "error"


# Idle silence before auto-abort (seconds). Automatically aborts if no speech for a few seconds.
DEFAULT_IDLE_TIMEOUT_S = 3.5
# Abort the engine if the mic/model isn't up in time
DEFAULT_STARTUP_TIMEOUT_S = 15.0
# Grace period after start before warning that the mic delivers no audio
NO_SIGNAL_WARNING_AFTER_S = 5.0
# How often we rebuild organic bar heights from the latest mic level
VISUALIZER_HZ = 30
BAR_COUNT = 28

# Mic pump cadence and PCM -> visual level mapping
MIC_PUMP_MS = 15
LEVEL_RMS_GAIN = 8.0
# RMS below this counts as digital silence
SILENCE_RMS = 0.0004


class WhisperWorkerThread(QThread):
    """Dedicated background thread for off-main-thread speech recognition."""
    transcription_ready = Signal(str, int)  # (text, session_id)
    error_occurred = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = queue.Queue()
        self._running = True
        self._model = None

    def set_model(self, model):
        self._model = model

    def ensure_model(self):
        """Load Whisper model in background thread if not already in memory."""
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
            from utils.bundle import whisper_model_root
            _dbg("Loading WhisperModel in background worker thread...")
            bundled = whisper_model_root()
            if bundled:
                self._model = WhisperModel(WHISPER_MODEL_NAME, device="cpu", compute_type="int8",
                                           download_root=bundled, local_files_only=True)
            else:
                self._model = WhisperModel(WHISPER_MODEL_NAME, device="cpu", compute_type="int8")
            _dbg("WhisperModel successfully loaded into memory.")
        except Exception as exc:
            _dbg(f"whisper-load-exc: {exc}")
            self.error_occurred.emit(str(exc), 0)
        return self._model

    def enqueue(self, audio_data: np.ndarray, session_id: int):
        self._queue.put((audio_data, session_id))

    def run(self):
        # Asynchronously load model in this background thread without blocking the GUI
        self.ensure_model()

        while self._running:
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if item is None:
                break

            audio_data, session_id = item
            if self._model is None:
                self.ensure_model()
            if self._model is None:
                continue

            try:
                # Transcribe with tuned Silero Voice Activity Detection (VAD) filter
                vad_params = {
                    "threshold": 0.55,
                    "min_silence_duration_ms": 350,
                    "speech_pad_ms": 150,
                    "min_speech_duration_ms": 250,
                }
                segments, _ = self._model.transcribe(
                    audio_data,
                    language="en",
                    vad_filter=True,
                    vad_parameters=vad_params,
                    beam_size=1,
                    temperature=0.0,
                )
                text = " ".join(s.text.strip() for s in segments).strip()
                if text:
                    _dbg(f"whisper-result session={session_id} text={text!r}")
                    self.transcription_ready.emit(text, session_id)
            except Exception as exc:
                _dbg(f"whisper-exc session={session_id} err={exc!r}")
                self.error_occurred.emit(str(exc), session_id)

    def stop(self):
        self._running = False
        self._queue.put(None)


class DictationService(QObject):
    """Owns one dictation session at a time and coordinates voice transcription."""

    state_changed = Signal(str)
    levels_updated = Signal(list)          # list[float] bar amplitudes 0..1
    partial_updated = Signal(str)          # provisional transcript
    final_committed = Signal(str)          # finalized segment that was injected
    error_occurred = Signal(str)
    session_ended = Signal(str)            # reason: completed|cancelled|error

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = DictationState.IDLE
        self._session_id = 0
        self._target_hwnd: Optional[int] = None
        self._accept_transcripts = False
        self._last_activity_ts = 0.0
        self._current_level = 0.0
        self._bar_targets: List[float] = [0.0] * BAR_COUNT
        self._bar_values: List[float] = [0.0] * BAR_COUNT
        self._bar_phases = [random.random() * math.tau for _ in range(BAR_COUNT)]
        self._end_reason = "completed"
        self._pending_terminal: Optional[DictationState] = None
        self._listening_since: Optional[float] = None
        self._saw_audio = False
        self._no_signal_warned = False
        self._last_speech_ts = 0.0

        # Utterance buffering state
        self._pcm_buffer = bytearray()
        self._is_speaking = False
        self._speech_bytes = 0
        self._sample_rate = 16000

        self._media_devices = QMediaDevices(self)
        self._audio_source: Optional[QAudioSource] = None
        self._audio_io = None
        self._mic_pump_timer: Optional[QTimer] = None
        self._mic_device = None
        self._wave_fmt: Optional[QAudioFormat] = None

        # Whisper model & persistent worker
        self._model = None
        self._worker = WhisperWorkerThread(self)
        self._worker.transcription_ready.connect(self._on_transcription_ready)
        self._worker.error_occurred.connect(self._on_worker_error)
        # Pre-warm Whisper model asynchronously in background thread so first shortcut press has zero lag
        QTimer.singleShot(800, self._worker.start)

        self._startup_timer = QTimer(self)
        self._startup_timer.setSingleShot(True)
        self._startup_timer.timeout.connect(self._on_startup_timeout)

        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(400)
        self._idle_timer.timeout.connect(self._check_idle_timeout)

        self._viz_timer = QTimer(self)
        self._viz_timer.setInterval(int(1000 / VISUALIZER_HZ))
        self._viz_timer.timeout.connect(self._tick_visualizer)

        self.idle_timeout_s = DEFAULT_IDLE_TIMEOUT_S
        self.startup_timeout_s = DEFAULT_STARTUP_TIMEOUT_S

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def state(self) -> DictationState:
        return self._state

    @property
    def is_active(self) -> bool:
        return self._state in (
            DictationState.STARTING,
            DictationState.LISTENING,
            DictationState.TRANSCRIBING,
            DictationState.STOPPING,
        )

    def toggle(self) -> None:
        if self._state in (DictationState.LISTENING, DictationState.TRANSCRIBING):
            self.cancel()
        elif self._state == DictationState.IDLE:
            self.start()

    def start(self) -> None:
        if sys.platform != "win32":
            self._fail("Voice dictation is only available on Windows.")
            return
        if self.is_active:
            return

        self._session_id += 1
        session = self._session_id
        self._end_reason = "completed"
        self._accept_transcripts = True
        self._current_level = 0.0
        self._pcm_buffer.clear()
        self._is_speaking = False
        self._speech_bytes = 0
        self._bar_targets = [0.0] * BAR_COUNT
        self._bar_values = [0.0] * BAR_COUNT
        self._last_activity_ts = time.monotonic()
        self._listening_since = None
        self._saw_audio = False
        self._no_signal_warned = False

        # Capture the focused app BEFORE Ticky UI expands.
        self._target_hwnd = text_inject.get_foreground_hwnd()
        _dbg(f"start session={session} hwnd={self._target_hwnd}")
        self._set_state(DictationState.STARTING)
        self._startup_timer.start(int(self.startup_timeout_s * 1000))

        try:
            self._start_engine(session)
        except Exception as exc:
            self._fail(str(exc), session=session)

    def cancel(self) -> None:
        """Manual abort: stop mic, discard uncommitted audio."""
        if not self.is_active and self._state != DictationState.STARTING:
            if self._state == DictationState.IDLE:
                return
        self._end_reason = "cancelled"
        self._accept_transcripts = False
        self._pcm_buffer.clear()
        self._is_speaking = False
        self._speech_bytes = 0
        self._begin_stop(DictationState.CANCELLED)

    def complete(self) -> None:
        """Graceful end (idle timeout / hotkey stop). Commits any in-flight utterance."""
        if not self.is_active:
            return
        self._end_reason = "completed"
        # Flush whatever speech is buffered
        self._flush_and_transcribe()
        self._accept_transcripts = False
        self._begin_stop(DictationState.COMPLETED)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _set_state(self, state: DictationState) -> None:
        self._state = state
        _dbg(f"state={state.value}")
        self.state_changed.emit(state.value)

    def _fail(self, message: str, session: Optional[int] = None) -> None:
        if session is not None and session != self._session_id:
            return
        _dbg(f"FAIL session={session} msg={message!r}")
        self._accept_transcripts = False
        self._end_reason = "error"
        self.error_occurred.emit(message)
        self._begin_stop(DictationState.ERROR)

    def _get_model(self):
        if self._worker._model is not None:
            return self._worker._model
        return self._worker.ensure_model()

    def _resolve_input_device(self):
        wanted = config.load_mic_device_id("")
        if wanted:
            for d in self._media_devices.audioInputs():
                if d.id() == wanted:
                    return d
        return self._media_devices.defaultAudioInput()

    @staticmethod
    def _build_wave_format(device) -> QAudioFormat:
        fmt = QAudioFormat()
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        preferred_rate = int(device.preferredFormat().sampleRate()) or 48000
        for rate in (16000, 48000, 44100, preferred_rate):
            fmt.setSampleRate(rate)
            if device.isFormatSupported(fmt):
                return fmt
        return device.preferredFormat()

    @staticmethod
    def _to_int16(data: bytes, fmt: QAudioFormat) -> Optional[bytes]:
        if fmt.sampleFormat().value == QAudioFormat.SampleFormat.Float.value:
            n = len(data) // 4
            vals = struct.unpack(f"<{n}f", data[: n * 4])
            return struct.pack(f"<{n}h", *[max(-32768, min(32767, int(v * 32767.0))) for v in vals])
        return None

    @staticmethod
    def _level_from_pcm16(data: bytes) -> float:
        n = len(data) // 2
        if n == 0:
            return 0.0
        samples = struct.unpack(f"<{n}h", data[: n * 2])
        step = max(1, n // 2048)
        acc = 0
        cnt = 0
        for i in range(0, n, step):
            acc += samples[i] * samples[i]
            cnt += 1
        rms = (acc / cnt) ** 0.5 / 32768.0
        return min(1.0, rms * LEVEL_RMS_GAIN)

    def _pcm_to_float32_16k(self, data: bytes) -> np.ndarray:
        if not data:
            return np.array([], dtype=np.float32)
        n = len(data) // 2
        samples = np.frombuffer(data[: n * 2], dtype=np.int16).astype(np.float32) / 32768.0
        sr = self._sample_rate or 16000
        if sr != 16000 and len(samples) > 0:
            orig_len = len(samples)
            target_len = int(orig_len * 16000 / sr)
            if target_len > 0:
                samples = np.interp(
                    np.linspace(0, orig_len, target_len, endpoint=False),
                    np.arange(orig_len),
                    samples
                ).astype(np.float32)
        return samples

    def _start_engine(self, session: int) -> None:
        device = self._resolve_input_device()
        if device is None or device.isNull():
            raise RuntimeError("No microphone input device is available.")
        fmt = self._build_wave_format(device)
        self._sample_rate = fmt.sampleRate() or 16000

        # Ensure background worker thread is running (loads model in background)
        if not self._worker.isRunning():
            self._worker.start()

        self._mic_device = device
        self._wave_fmt = fmt
        self._audio_source = QAudioSource(device, fmt, self)
        self._audio_io = self._audio_source.start()
        if self._audio_io is None:
            raise RuntimeError("Could not start microphone capture.")

        self._mic_pump_timer = QTimer(self)
        self._mic_pump_timer.setInterval(MIC_PUMP_MS)
        self._mic_pump_timer.timeout.connect(self._pump_mic_audio)
        self._mic_pump_timer.start()

        self._viz_timer.start()
        self._idle_timer.start()

        _dbg(f"engine-up device={device.description()!r} rate={self._sample_rate}")
        self._mark_engine_ready(session)

    def _mark_engine_ready(self, session: int) -> None:
        if session != self._session_id or self._state != DictationState.STARTING:
            return
        self._startup_timer.stop()
        self._listening_since = time.monotonic()
        self._saw_audio = False
        self._no_signal_warned = False
        self._set_state(DictationState.LISTENING)
        self._last_activity_ts = time.monotonic()
        self._last_speech_ts = time.monotonic()

    def _pump_mic_audio(self) -> None:
        io = self._audio_io
        if io is None:
            return
        src = self._audio_source
        if src is not None and self.is_active:
            try:
                err_val = src.error().value
                state_val = src.state().value
                if err_val != QAudio.Error.NoError.value and state_val != QAudio.State.ActiveState.value:
                    _dbg(f"audio-err code={err_val} state={state_val}")
                    self._fail(f"Microphone error during dictation (code {err_val}).")
                    return
            except Exception as exc:
                _dbg(f"audio-check-exc {exc!r}")

        data = bytes(io.readAll())
        if not data:
            return

        if self._wave_fmt.sampleFormat().value != QAudioFormat.SampleFormat.Int16.value:
            converted = self._to_int16(data, self._wave_fmt)
            if converted is None:
                return
            data = converted

        level = self._level_from_pcm16(data)
        self._current_level = level

        # Append incoming PCM to audio buffer
        self._pcm_buffer.extend(data)

        # Voice activity threshold
        if level > (SILENCE_RMS * 1.5):
            self._saw_audio = True
            self._is_speaking = True
            self._last_activity_ts = time.monotonic()
            self._last_speech_ts = time.monotonic()
            self._speech_bytes += len(data)
        else:
            # Check for pause in speech
            if self._is_speaking:
                silent_gap = time.monotonic() - self._last_speech_ts
                min_bytes = int(self._sample_rate * 2 * 0.3)  # at least 300ms speech
                # If speaker paused for ~380ms after speaking, flush and transcribe
                if silent_gap >= 0.38 and self._speech_bytes >= min_bytes:
                    self._is_speaking = False
                    self._speech_bytes = 0
                    self._flush_and_transcribe()

    def _flush_and_transcribe(self) -> None:
        """Enqueue accumulated audio to the background Whisper worker."""
        if not self._pcm_buffer:
            return

        raw_pcm = bytes(self._pcm_buffer)
        self._pcm_buffer.clear()

        # Check if enough audio exists (at least 300ms)
        min_bytes = int(self._sample_rate * 2 * 0.3)
        if len(raw_pcm) < min_bytes:
            return

        audio_f32 = self._pcm_to_float32_16k(raw_pcm)
        if len(audio_f32) >= 16000 * 0.3:
            _dbg(f"enqueue-audio samples={len(audio_f32)} session={self._session_id}")
            self._set_state(DictationState.TRANSCRIBING)
            self._worker.enqueue(audio_f32, self._session_id)

    def _on_transcription_ready(self, text: str, session_id: int) -> None:
        if session_id != self._session_id or not self._accept_transcripts:
            return

        text = (text or "").strip()
        if not text:
            if self._state == DictationState.TRANSCRIBING:
                self._set_state(DictationState.LISTENING)
            return

        self._last_activity_ts = time.monotonic()
        self._last_speech_ts = time.monotonic()

        # Add a trailing space so consecutive spoken sentences flow naturally
        to_type = text if text.endswith((" ", "\n")) else text + " "
        _dbg(f"injecting-text {to_type!r} into hwnd={self._target_hwnd}")

        if text_inject.inject_text(to_type, self._target_hwnd):
            self.final_committed.emit(to_type)
            self.partial_updated.emit(text)

        if self.is_active:
            self._set_state(DictationState.LISTENING)

    def _on_worker_error(self, err_msg: str, session_id: int) -> None:
        if session_id == self._session_id and self.is_active:
            self._set_state(DictationState.LISTENING)

    def _teardown_audio(self) -> None:
        if self._mic_pump_timer is not None:
            self._mic_pump_timer.stop()
            self._mic_pump_timer = None
        if self._audio_source is not None:
            try:
                self._audio_source.stop()
            except Exception:
                pass
            self._audio_source.deleteLater()
            self._audio_source = None
        self._audio_io = None

    def _begin_stop(self, terminal_state: DictationState) -> None:
        if self._state in (DictationState.STOPPING, DictationState.IDLE):
            return

        self._pending_terminal = terminal_state
        self._set_state(DictationState.STOPPING)
        self._idle_timer.stop()
        self._viz_timer.stop()
        self._startup_timer.stop()
        self._emit_zero_levels()
        self._finish(terminal_state)

    def _finish(self, terminal_state: DictationState) -> None:
        if self._state in (
            DictationState.IDLE,
            DictationState.CANCELLED,
            DictationState.COMPLETED,
            DictationState.ERROR,
        ):
            return

        self._accept_transcripts = False
        self._pcm_buffer.clear()
        self._current_level = 0.0
        self._teardown_audio()
        self._idle_timer.stop()
        self._viz_timer.stop()
        self._startup_timer.stop()
        self._emit_zero_levels()

        self._set_state(terminal_state)
        reason = {
            DictationState.CANCELLED: "cancelled",
            DictationState.ERROR: "error",
            DictationState.COMPLETED: "completed",
        }.get(terminal_state, self._end_reason)
        self.session_ended.emit(reason)

        QTimer.singleShot(50, lambda: self._set_state(DictationState.IDLE) if self._state == terminal_state else None)
        self._pending_terminal = None

    def _on_startup_timeout(self) -> None:
        if self._state == DictationState.STARTING:
            self._fail(
                "Speech engine didn't start in time. "
                "Your microphone may be in use by another app."
            )

    def _check_idle_timeout(self) -> None:
        if self._state not in (DictationState.LISTENING, DictationState.TRANSCRIBING):
            return
        now = time.monotonic()
        silent_for = now - self._last_speech_ts
        if silent_for >= self.idle_timeout_s:
            _dbg(f"idle-timeout silent_for={silent_for:.2f}s saw_audio={self._saw_audio}")
            if self._saw_audio or self._speech_bytes > 0:
                self.complete()
            else:
                self.cancel()
            return
        if (
            not self._saw_audio
            and not self._no_signal_warned
            and self._listening_since is not None
            and now - self._listening_since >= NO_SIGNAL_WARNING_AFTER_S
        ):
            self._no_signal_warned = True
            self.partial_updated.emit("No microphone signal — is another app using your mic?")

    def _tick_visualizer(self) -> None:
        if not self.is_active:
            return

        level = self._current_level
        t = time.monotonic()
        for i in range(BAR_COUNT):
            phase = self._bar_phases[i]
            center_weight = 1.0 - abs((i / max(1, BAR_COUNT - 1)) - 0.5) * 1.2
            wave = 0.55 + 0.45 * math.sin(t * (3.2 + i * 0.17) + phase)
            noise = 0.85 + 0.15 * math.sin(t * 7.0 + phase * 2.1)
            base = 0.04 + 0.08 * wave
            target = base + (level ** 0.85) * wave * noise * max(0.25, center_weight)
            self._bar_values[i] += (target - self._bar_values[i]) * 0.35
            self._bar_targets[i] = target

        self.levels_updated.emit(list(self._bar_values))

    def _emit_zero_levels(self) -> None:
        self._bar_values = [0.0] * BAR_COUNT
        self.levels_updated.emit(list(self._bar_values))
