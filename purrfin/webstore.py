"""Saving in a web browser (the web version runs Python inside the page, with no real disk).
The save lives in the browser's localStorage for this site, so it stays between visits."""
import sys

WEB = sys.platform == "emscripten"


def _storage():
    import platform                    # in the browser this is the page itself (window, localStorage...)
    return platform.window.localStorage


def read(key):
    try:
        v = _storage().getItem("desktop-aquarium:" + key)
    except Exception:
        return None
    if v is None:
        return None
    v = str(v)
    return None if v in ("null", "undefined") else v


def ask(message, default=""):
    """the browser's own text box (on a phone it brings up the keyboard). None if cancelled."""
    try:
        import platform
        v = platform.window.prompt(message, default)
    except Exception:
        return None
    if v is None:
        return None
    v = str(v)
    return None if v in ("null", "undefined") else v


COPY_JS = """
window.daCopyResult = null;
window.daCopy = function (text) {
  window.daCopyResult = null;
  try {
    navigator.clipboard.writeText(text).then(() => { window.daCopyResult = "ok"; },
                                             () => { window.daCopyResult = "fail"; });
  } catch (e) { window.daCopyResult = "fail"; }
};
"""
_copy_ready = [False]


def copy(text):
    """start copying text to the clipboard (the browser finishes it a moment later: see copy_result)"""
    try:
        import platform
        if not _copy_ready[0]:
            platform.window.eval(COPY_JS)
            _copy_ready[0] = True
        platform.window.daCopy(text)
        return True
    except Exception:
        return False


def copy_result():
    """None (not finished yet), 'ok' or 'fail'"""
    try:
        import platform
        v = platform.window.daCopyResult
    except Exception:
        return "fail"
    v = None if v is None else str(v)
    return v if v in ("ok", "fail") else None


def refit():
    """after the canvas changes size, the page has to scale it to the screen again"""
    try:
        import platform
        platform.window.window_resize()
    except Exception:
        pass


def write(key, text):
    try:
        _storage().setItem("desktop-aquarium:" + key, text)
        return True
    except Exception:
        return False
