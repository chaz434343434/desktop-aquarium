"""Window helpers.
Windows: transparent, click-through, always-on-top, non-activating overlay (Win32 via ctypes).
macOS / others: there's no colour-key transparency, so the game uses a compact window that sits
just around the tank (see Game.layout); here we only place it, keep it on top and set its opacity."""
import ctypes
import os
import sys

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
COMPACT = not IS_WIN          # no see-through window: keep the window just around the tank
if IS_WIN:
    from ctypes import wintypes as wt

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
LWA_COLORKEY = 0x1
LWA_ALPHA = 0x2
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_FRAMECHANGED = 0x0020

if IS_WIN:
    user32 = ctypes.windll.user32
    user32.MonitorFromWindow.restype = ctypes.c_void_p
    user32.MonitorFromWindow.argtypes = [wt.HWND, wt.DWORD]
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.GetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int]
    user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.SetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_ssize_t]
    user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_uint]
    user32.SetLayeredWindowAttributes.argtypes = [wt.HWND, wt.COLORREF, wt.BYTE, wt.DWORD]


def set_dpi_aware():
    if not IS_WIN:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


if IS_WIN:
    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT), ("dwFlags", wt.DWORD)]


def monitors():
    """list of dicts: x,y,w,h (work area) and primary flag; primary first."""
    if not IS_WIN:
        return _other_monitors()
    out = []
    proc = ctypes.WINFUNCTYPE(ctypes.c_int, wt.HMONITOR, wt.HDC, ctypes.POINTER(wt.RECT), wt.LPARAM)

    def cb(hmon, hdc, rect, lp):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        r = mi.rcWork
        out.append(dict(x=r.left, y=r.top, w=r.right - r.left, h=r.bottom - r.top, primary=bool(mi.dwFlags & 1)))
        return 1

    user32.EnumDisplayMonitors(None, None, proc(cb), 0)
    out.sort(key=lambda m: not m["primary"])
    return out


def style_overlay(hwnd, colorkey, alpha, topmost=True):
    if not IS_WIN:
        set_alpha(hwnd, colorkey, alpha)
        set_topmost(hwnd, topmost)
        return
    ex = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    ex |= WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_APPWINDOW
    ex &= ~WS_EX_TOOLWINDOW
    user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex)
    set_alpha(hwnd, colorkey, alpha)
    set_topmost(hwnd, topmost)


def set_alpha(hwnd, colorkey, alpha):
    if not IS_WIN:
        w = _sdl_window()
        if w is not None:
            try:
                w.opacity = max(0.2, min(1.0, alpha / 255))
            except Exception:
                pass
        return
    r, g, b = colorkey
    user32.SetLayeredWindowAttributes(hwnd, r | (g << 8) | (b << 16), int(alpha), LWA_COLORKEY | LWA_ALPHA)


def set_topmost(hwnd, on):
    if not IS_WIN:
        _mac_topmost(on)
        return
    user32.SetWindowPos(hwnd, HWND_TOPMOST if on else HWND_NOTOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED)


def move(hwnd, x, y, w, h, topmost=True):
    if not IS_WIN:
        win = _sdl_window()
        if win is not None:
            try:
                win.position = (int(x), int(y))
            except Exception:
                pass
        return
    user32.SetWindowPos(hwnd, HWND_TOPMOST if topmost else HWND_NOTOPMOST, int(x), int(y), int(w), int(h),
                        SWP_NOACTIVATE | SWP_SHOWWINDOW)


def set_activatable(hwnd, on):
    """let the overlay take keyboard focus (for typing a fish name) or go back to never stealing it"""
    if not IS_WIN:
        if on and IS_MAC:
            try:
                from AppKit import NSApplication
                NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            except Exception:
                pass
        return
    if not hwnd:
        return
    ex = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    ex = ex & ~WS_EX_NOACTIVATE if on else ex | WS_EX_NOACTIVATE
    user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex)
    if on:
        user32.SetForegroundWindow(hwnd)


def foreground():
    return user32.GetForegroundWindow() if IS_WIN else None


def restore_foreground(hwnd):
    if IS_WIN and hwnd:
        user32.SetForegroundWindow(hwnd)


# ---------------------------------------------------------------- macOS / other
_WINDOW = None


def _sdl_window():
    """pygame's Window for the game window, made ONCE and kept.
    Window.from_display_module() leaves pygame holding a pointer to the object it returns; if that
    object is thrown away, the next window resize follows the stale pointer into freed memory.
    On Apple-chip Macs that crashed the game when the window changed size (Options > Tank width,
    opening the Shop...). DA_OLD_WINDOW=1 brings the old behaviour back, only for the crash test."""
    global _WINDOW
    try:
        from pygame._sdl2.video import Window
        if os.environ.get("DA_OLD_WINDOW"):
            return Window.from_display_module()
        if _WINDOW is None:
            _WINDOW = Window.from_display_module()
        return _WINDOW
    except Exception:
        return None


def _other_monitors():
    if IS_MAC:
        try:
            from AppKit import NSScreen
            scrs = list(NSScreen.screens())
            top = scrs[0].frame().size.height          # Cocoa counts y from the bottom of the main screen
            out = []
            for i, sc in enumerate(scrs):
                v = sc.visibleFrame()                    # without the menu bar and the Dock
                out.append(dict(x=int(v.origin.x), y=int(top - v.origin.y - v.size.height),
                                w=int(v.size.width), h=int(v.size.height), primary=i == 0))
            if out:
                return out
        except Exception:
            pass
    try:
        import pygame
        sizes = pygame.display.get_desktop_sizes()
        if sizes:
            menu = 25 if IS_MAC else 0
            return [dict(x=0, y=menu, w=w, h=h - menu, primary=i == 0) for i, (w, h) in enumerate(sizes)]
    except Exception:
        pass
    return [dict(x=0, y=0, w=1280, h=720, primary=True)]


def _mac_topmost(on):
    if not IS_MAC:
        return
    try:
        from AppKit import NSApplication
        for w in NSApplication.sharedApplication().windows():
            if str(w.title()) == "Desktop Aquarium":
                w.setLevel_(3 if on else 0)                   # NSFloatingWindowLevel / NSNormalWindowLevel
                w.setCollectionBehavior_((1 << 0) | (1 << 8))  # on every Space, and next to full-screen apps
                w.setHidesOnDeactivate_(False)
    except Exception:
        pass


# ---------------------------------------------------------------- staying out of the way
def set_low_priority():
    """below-normal CPU priority: if the computer is busy, Chrome and schoolwork go first"""
    try:
        if IS_WIN:
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)
        else:
            import os
            os.nice(5)
    except Exception:
        pass


def fullscreen_app_in_front(own=None):
    """True while another program fills its whole monitor (a full-screen video, a game, slides).
    The tank can barely be seen then, so the game slows right down."""
    if not IS_WIN:
        return False
    try:
        fg = user32.GetForegroundWindow()
        if not fg or fg == own:
            return False
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(fg, cls, 64)
        if cls.value in ("Progman", "WorkerW", "Shell_TrayWnd"):        # the desktop / taskbar
            return False
        r = wt.RECT()
        user32.GetWindowRect(fg, ctypes.byref(r))
        mon = user32.MonitorFromWindow(fg, 2)
        if own and user32.MonitorFromWindow(own, 2) != mon:      # it's on another screen: tank still visible
            return False
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(wt.HMONITOR(mon), ctypes.byref(mi))
        m = mi.rcMonitor
        return r.left <= m.left and r.top <= m.top and r.right >= m.right and r.bottom >= m.bottom
    except Exception:
        return False


# ---------------------------------------------------------------- shutdown / sleep
_hooks = {}


def on_session_end(hwnd, callback):
    """Windows only: call callback(msg, wparam) the moment Windows says it's shutting down, restarting,
    signing out (WM_QUERYENDSESSION / WM_ENDSESSION) or going to sleep (WM_POWERBROADCAST + PBT_APMSUSPEND).
    pygame doesn't pass these on, so the window's message handler is wrapped. The callback runs before
    Windows gets its answer, so the save is on disk before anything is shut down."""
    if not IS_WIN or not hwnd or hwnd in _hooks:
        return
    WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
    user32.CallWindowProcW.restype = ctypes.c_ssize_t
    user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    old = user32.GetWindowLongPtrW(hwnd, -4)              # GWLP_WNDPROC

    show = show_message_id()

    def proc(h, msg, wp, lp):
        if msg in (0x0011, 0x0016) or (msg == 0x0218 and wp == 0x0004) or (show and msg == show):
            try:
                callback(msg, wp)
            except Exception:
                pass
        return user32.CallWindowProcW(old, h, msg, wp, lp)

    cb = WNDPROC(proc)
    user32.SetWindowLongPtrW(hwnd, -4, ctypes.cast(cb, ctypes.c_void_p).value)
    _hooks[hwnd] = (cb, old)                             # keep the callback alive


# ---------------------------------------------------------------- one copy at a time
_lock = None


def single_instance(save_path):
    """True if this is the only copy of the game running on this save file.
    (Per save file, so two copies can't overwrite each other's progress; tests use their own saves.)
    Windows: a named mutex. Mac: a lock file next to the save. Released automatically when the game ends."""
    global _lock
    import hashlib
    key = hashlib.sha1(os.path.abspath(save_path).lower().encode("utf-8")).hexdigest()[:16]
    if IS_WIN:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)     # so the "already exists" code isn't lost
        k32.CreateMutexW.restype = wt.HANDLE
        k32.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
        h = k32.CreateMutexW(None, False, f"Local\\DesktopAquarium_{key}")
        if not h:
            return True                         # can't tell: let it run
        if ctypes.get_last_error() == 183:      # ERROR_ALREADY_EXISTS
            k32.CloseHandle(h)
            return False
        _lock = h                               # keep it open while the game runs
        return True
    try:
        import fcntl
        folder = os.path.dirname(os.path.abspath(save_path))
        os.makedirs(folder, exist_ok=True)
        fh = open(os.path.join(folder, f".running_{key}.lock"), "w")
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fh.close()
            return False
        _lock = fh
        return True
    except Exception:
        return True


SHOW_MESSAGE = "DesktopAquarium_ShowYourself"


def show_message_id():
    return user32.RegisterWindowMessageW(SHOW_MESSAGE) if IS_WIN else 0


def wake_running_copy():
    """the game is already open: ask it to come back on screen (un-hide, say hello)"""
    if not IS_WIN:
        return
    msg = show_message_id()
    proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(hwnd, lp):
        buf = ctypes.create_unicode_buffer(64)
        user32.GetWindowTextW(hwnd, buf, 64)
        if buf.value == "Desktop Aquarium":
            user32.PostMessageW(hwnd, msg, 0, 0)
        return True

    user32.EnumWindows(proc(cb), 0)


# ---------------------------------------------------------------- clipboard / Pictures folder
def set_clipboard(text):
    """copy text to the clipboard. Returns True if it worked."""
    try:
        if IS_WIN:
            k32 = ctypes.windll.kernel32
            k32.GlobalAlloc.restype = ctypes.c_void_p
            k32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
            k32.GlobalLock.restype = ctypes.c_void_p
            k32.GlobalLock.argtypes = [ctypes.c_void_p]
            k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            user32.SetClipboardData.restype = ctypes.c_void_p
            user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
            data = text.encode("utf-16-le") + b"\0\0"
            for _ in range(10):
                if user32.OpenClipboard(None):
                    break
                import time
                time.sleep(0.05)
            else:
                return False
            try:
                user32.EmptyClipboard()
                h = k32.GlobalAlloc(0x0002, len(data))          # GMEM_MOVEABLE
                p = k32.GlobalLock(h)
                ctypes.memmove(p, data, len(data))
                k32.GlobalUnlock(h)
                return bool(user32.SetClipboardData(13, h))     # CF_UNICODETEXT
            finally:
                user32.CloseClipboard()
        import subprocess
        subprocess.run(["pbcopy"] if IS_MAC else ["xclip", "-selection", "clipboard"], input=text.encode("utf-8"),
                       check=True, timeout=5)
        return True
    except Exception:
        return False


def get_clipboard():
    """text on the clipboard ('' if none)"""
    try:
        if IS_WIN:
            k32 = ctypes.windll.kernel32
            k32.GlobalLock.restype = ctypes.c_void_p
            k32.GlobalLock.argtypes = [ctypes.c_void_p]
            k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            user32.GetClipboardData.restype = ctypes.c_void_p
            user32.GetClipboardData.argtypes = [ctypes.c_uint]
            if not user32.OpenClipboard(None):
                return ""
            try:
                h = user32.GetClipboardData(13)
                if not h:
                    return ""
                p = k32.GlobalLock(h)
                try:
                    return ctypes.wstring_at(p) if p else ""
                finally:
                    k32.GlobalUnlock(h)
            finally:
                user32.CloseClipboard()
        import subprocess
        out = subprocess.run(["pbpaste"] if IS_MAC else ["xclip", "-selection", "clipboard", "-o"],
                             capture_output=True, timeout=5)
        return out.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def pictures_dir():
    """the user's Pictures folder (Windows may move it, e.g. into OneDrive)"""
    if IS_WIN:
        try:
            class GUID(ctypes.Structure):
                _fields_ = [("a", ctypes.c_uint32), ("b", ctypes.c_uint16), ("c", ctypes.c_uint16),
                            ("d", ctypes.c_ubyte * 8)]
            fid = GUID(0x33E28130, 0x4E1E, 0x4676, (ctypes.c_ubyte * 8)(0x83, 0x5A, 0x98, 0x39, 0x5C, 0x3B, 0xC3, 0xBB))
            p = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(fid), 0, None, ctypes.byref(p)) == 0:
                path = p.value
                ctypes.windll.ole32.CoTaskMemFree(p)
                if path and os.path.isdir(path):
                    return path
        except Exception:
            pass
    path = os.path.expanduser("~/Pictures")
    return path if os.path.isdir(path) else os.path.expanduser("~")


def open_folder(path):
    try:
        if IS_WIN:
            os.startfile(path)
        else:
            import subprocess
            subprocess.Popen(["open" if IS_MAC else "xdg-open", path])
    except Exception:
        pass
