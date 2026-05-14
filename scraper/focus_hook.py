"""
focus_hook.py — BE-2
Windows WinEvent hook for instant foreground window change detection.

Uses SetWinEventHook(EVENT_SYSTEM_FOREGROUND) via ctypes/win32.
The hook fires the moment the OS switches focus — no polling needed.

Usage:
    hook = FocusHook()
    hook.start()                  # starts message loop in a daemon thread

    if hook.consume_change():     # True if focus changed since last check
        title, hwnd = hook.last_foreground
        ...

    hook.stop()
"""

import ctypes
import ctypes.wintypes
import threading
import logging
import win32gui
import win32con

logger = logging.getLogger("focus_hook")

# WinEvent constants
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT   = 0x0000   # fires on hook thread, no in-process DLL needed
WINEVENT_SKIPOWNPROCESS = 0x0002   # ignore our own process focus changes

# WinEventProc signature
WinEventProc = ctypes.WINFUNCTYPE(
    None,
    ctypes.wintypes.HANDLE,   # hWinEventHook
    ctypes.wintypes.DWORD,    # event
    ctypes.wintypes.HWND,     # hwnd
    ctypes.wintypes.LONG,     # idObject
    ctypes.wintypes.LONG,     # idChild
    ctypes.wintypes.DWORD,    # idEventThread
    ctypes.wintypes.DWORD,    # dwmsEventTime
)


class FocusHook:
    """
    Installs a WinEvent hook for EVENT_SYSTEM_FOREGROUND.
    Runs its own Windows message loop in a background daemon thread.
    Thread-safe: _changed flag is set from hook thread, read from scraper thread.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._changed = False
        self._last_hwnd: int = 0
        self._last_title: str = ""
        self._hook_handle = None
        self._thread: threading.Thread | None = None
        self._running = False

        # Keep a reference to the callback so it isn't GC'd
        self._callback = WinEventProc(self._on_foreground_change)

    # ──────────────────────────────────────────────────────────────────────────
    # Callback (runs on hook thread)
    # ──────────────────────────────────────────────────────────────────────────

    def _on_foreground_change(self, hook, event, hwnd, id_object, id_child, event_thread, event_time):
        if hwnd == 0:
            return
        try:
            title = win32gui.GetWindowText(hwnd) or ""
        except Exception:
            title = ""

        with self._lock:
            # Only flag a real change — skip if same hwnd and same title
            if hwnd != self._last_hwnd or title != self._last_title:
                self._last_hwnd = hwnd
                self._last_title = title
                self._changed = True
                logger.debug("[focus_hook] Foreground → hwnd=%d '%s'", hwnd, title[:60])

    # ──────────────────────────────────────────────────────────────────────────
    # Message loop (runs on hook thread)
    # ──────────────────────────────────────────────────────────────────────────

    def _message_loop(self):
        user32 = ctypes.windll.user32

        self._hook_handle = user32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND,
            EVENT_SYSTEM_FOREGROUND,
            None,                        # no DLL — out-of-context
            self._callback,
            0,                           # any process
            0,                           # any thread
            WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
        )

        if not self._hook_handle:
            logger.error("[focus_hook] SetWinEventHook failed — focus detection disabled.")
            return

        logger.info("[focus_hook] Hook installed. Listening for foreground changes.")

        # Standard Windows message pump — required for out-of-context hooks
        msg = ctypes.wintypes.MSG()
        while self._running:
            ret = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, win32con.PM_REMOVE)
            if ret:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                # Sleep briefly to avoid spinning at 100% CPU
                threading.Event().wait(0.05)

        user32.UnhookWinEvent(self._hook_handle)
        self._hook_handle = None
        logger.info("[focus_hook] Hook removed.")

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def start(self):
        """Start the hook in a daemon background thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._message_loop,
            daemon=True,
            name="focus-hook",
        )
        self._thread.start()

    def stop(self):
        """Signal the message loop to exit."""
        self._running = False

    def consume_change(self) -> bool:
        """
        Returns True if a focus change was detected since the last call.
        Resets the flag — call once per scraper loop tick.
        """
        with self._lock:
            if self._changed:
                self._changed = False
                return True
            return False

    @property
    def last_foreground(self) -> tuple[str, int]:
        """Returns (window_title, hwnd) of the most recently focused window."""
        with self._lock:
            return self._last_title, self._last_hwnd
