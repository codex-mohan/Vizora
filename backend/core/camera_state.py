"""Camera-level preprocessing state machine.

See PLAN.md §5. A camera has a sticky MODE re-evaluated every ~5s via
EWMA over frame metrics + weather API + sun position. Per-frame switching
causes tracking flicker and is explicitly forbidden.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque

from core.config import CameraMode, Settings


class _Signal(str, Enum):
    NONE = "NONE"
    LOWLIGHT = "LOWLIGHT"
    HAZE = "HAZE"
    RAIN = "RAIN"


@dataclass
class FrameQuality:
    brightness: float
    blur: float
    haze: float
    noise: float


@dataclass
class CameraState:
    camera_id: str
    mode: CameraMode = CameraMode.CLEAN
    _enter_streak: int = 0
    _exit_streak: int = 0
    _brightness_ewma: float = 128.0
    _haze_ewma: float = 0.0
    _noise_ewma: float = 0.0
    _history: Deque[FrameQuality] = field(default_factory=lambda: deque(maxlen=30))
    _last_eval: float = field(default_factory=time.time)
    _weather_signal: _Signal = _Signal.NONE
    _sun_signal: _Signal = _Signal.NONE

    def update(self, quality: FrameQuality, settings: Settings) -> None:
        self._history.append(quality)
        alpha = 0.1
        self._brightness_ewma = (1 - alpha) * self._brightness_ewma + alpha * quality.brightness
        self._haze_ewma = (1 - alpha) * self._haze_ewma + alpha * quality.haze
        self._noise_ewma = (1 - alpha) * self._noise_ewma + alpha * quality.noise

        now = time.time()
        if now - self._last_eval < settings.camera_eval_interval_s:
            return
        self._last_eval = now
        self._evaluate(settings)

    def update_weather(self, signal: _Signal) -> None:
        self._weather_signal = signal

    def update_sun(self, signal: _Signal) -> None:
        self._sun_signal = signal

    def _evaluate(self, settings: Settings) -> None:
        desired = self._compute_desired_mode(settings)
        if desired == CameraMode.CLEAN:
            if self.mode != CameraMode.CLEAN:
                self._exit_streak += 1
                self._enter_streak = 0
                if self._exit_streak >= settings.degraded_exit_evals:
                    self.mode = CameraMode.CLEAN
                    self._exit_streak = 0
        else:
            self._enter_streak += 1
            self._exit_streak = 0
            if self._enter_streak >= settings.degraded_enter_evals:
                self.mode = desired
                self._enter_streak = 0

    def _compute_desired_mode(self, settings: Settings) -> CameraMode:
        signals: list[_Signal] = []
        if self._brightness_ewma < 60:
            signals.append(_Signal.LOWLIGHT)
        if self._haze_ewma > 0.4:
            signals.append(_Signal.HAZE)
        if self._weather_signal == _Signal.RAIN:
            signals.append(_Signal.RAIN)
        if self._sun_signal == _Signal.LOWLIGHT:
            signals.append(_Signal.LOWLIGHT)

        counts: dict[_Signal, int] = {}
        for s in signals:
            counts[s] = counts.get(s, 0) + 1

        active = [s for s, c in counts.items() if c >= 2 or s == self._weather_signal]
        if not active:
            return CameraMode.CLEAN
        if len(active) > 1:
            return CameraMode.MULTI
        mapping = {
            _Signal.LOWLIGHT: CameraMode.LOWLIGHT,
            _Signal.HAZE: CameraMode.HAZE,
            _Signal.RAIN: CameraMode.RAIN,
        }
        return mapping.get(active[0], CameraMode.CLEAN)


class CameraStateRegistry:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cameras: dict[str, CameraState] = {}

    def get(self, camera_id: str) -> CameraState:
        if camera_id not in self._cameras:
            self._cameras[camera_id] = CameraState(camera_id=camera_id)
        return self._cameras[camera_id]

    def update(self, camera_id: str, quality: FrameQuality) -> CameraMode:
        state = self.get(camera_id)
        state.update(quality, self._settings)
        return state.mode
