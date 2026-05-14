"""
idle_detector.py — BE-2
Detects mouse/keyboard inactivity using pynput.
If the user has been idle beyond IDLE_THRESHOLD_SECONDS, the scraper skips the cycle.
"""

import time
import threading
from pynput import mouse, keyboard

# Default idle threshold — can be overridden at runtime by reading settings
IDLE_THRESHOLD_SECONDS = 120  # 2 minutes


class IdleDetector:
    """
    Tracks last input time using low-level mouse and keyboard hooks via pynput.
    Thread-safe: _last_input_time updated from listener threads, read from scraper thread.
    """

    def __init__(self, threshold_seconds: int = IDLE_THRESHOLD_SECONDS):
        self.threshold = threshold_seconds
        self._last_input_time = time.time()
        self._lock = threading.Lock()
        self._mouse_listener = None
        self._keyboard_listener = None

    # ------------------------------------------------------------------ #
    # Internal event handlers — called by pynput on its own threads       #
    # ------------------------------------------------------------------ #

    def _on_activity(self, *args, **kwargs):
        with self._lock:
            self._last_input_time = time.time()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def start(self):
        """Start background listeners. Call once at process startup."""
        self._mouse_listener = mouse.Listener(
            on_move=self._on_activity,
            on_click=self._on_activity,
            on_scroll=self._on_activity,
        )
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_activity,
        )
        self._mouse_listener.start()
        self._keyboard_listener.start()

    def stop(self):
        """Stop listeners cleanly."""
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()

    def is_idle(self) -> bool:
        """Returns True if the user has been idle beyond the threshold."""
        with self._lock:
            idle_for = time.time() - self._last_input_time
        return idle_for >= self.threshold

    def idle_seconds(self) -> float:
        """Returns how many seconds the user has been idle."""
        with self._lock:
            return time.time() - self._last_input_time

    def set_threshold(self, seconds: int):
        self.threshold = seconds
