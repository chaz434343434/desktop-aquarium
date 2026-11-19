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


# Chrome's own prompt() boxes cut long text (over ~2000 letters it drops the middle and puts "..."), so long
# codes get this box instead: a full-screen page panel with a big text area and real Copy / Paste buttons.
MODAL_JS = """
window.daModalResult = null;
window.daModal = function (title, text, mode, okLabel) {
  const old = document.getElementById('daModal');
  if (old) old.remove();
  window.daModalResult = null;
  const finish = (r) => { window.daModalResult = JSON.stringify(r); wrap.remove(); };
  const wrap = document.createElement('div');
  wrap.id = 'daModal';
  wrap.style.cssText = 'position:fixed;inset:0;z-index:2147483647;background:rgba(12,16,30,0.96);display:flex;' +
    'flex-direction:column;gap:10px;padding:14px;box-sizing:border-box;font-family:sans-serif;color:#f4f6ff;';
  const h = document.createElement('div');
  h.textContent = title;
  h.style.cssText = 'font-size:17px;line-height:1.3;';
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.readOnly = mode === 'show';
  ta.spellcheck = false;
  ta.autocapitalize = 'off';
  ta.style.cssText = 'flex:1;width:100%;box-sizing:border-box;font:13px monospace;word-break:break-all;' +
    'background:#1c2238;color:#ffffff;border:2px solid #5a6aa0;border-radius:8px;padding:8px;resize:none;';
  const row = document.createElement('div');
  row.style.cssText = 'display:flex;gap:10px;';
  const btn = (label, colour, fn) => {
    const b = document.createElement('button');
    b.textContent = label;
    b.style.cssText = 'flex:1;font-size:17px;padding:12px;border:0;border-radius:8px;color:#fff;background:' + colour;
    b.onclick = fn;
    row.appendChild(b);
    return b;
  };
  for (const ev of ['keydown', 'keyup', 'keypress', 'touchstart', 'touchmove', 'touchend', 'mousedown', 'mouseup',
                    'pointerdown', 'pointerup', 'wheel']) {
    wrap.addEventListener(ev, (e) => e.stopPropagation());
  }
  if (mode === 'show') {
    const copy = btn('Copy', '#2f9e5b', () => {
      navigator.clipboard.writeText(ta.value).then(() => { copy.textContent = 'Copied!'; },
        () => { ta.select(); copy.textContent = 'Now press and hold the text to copy'; });
    });
    btn('Done', '#4a5580', () => finish({ok: true, text: ''}));
    try {
      navigator.clipboard.writeText(text).then(() => { copy.textContent = 'Copied!'; }, () => {});
    } catch (e) {}
  } else {
    btn('Paste', '#4a5580', () => {
      try {
        navigator.clipboard.readText().then((t) => { ta.value = t; }, () => { ta.focus(); });
      } catch (e) { ta.focus(); }
    });
    btn(okLabel || 'OK', '#2f9e5b', () => finish({ok: true, text: ta.value}));
    btn('Cancel', '#a04050', () => finish({ok: false}));
  }
  wrap.appendChild(h);
  wrap.appendChild(ta);
  wrap.appendChild(row);
  document.body.appendChild(wrap);
  if (mode !== 'show') setTimeout(() => ta.focus(), 50);
};
"""
_modal_ready = [False]


def modal(title, text="", mode="paste", ok_label="OK"):
    """open the long-text box. mode 'show' (read only, with Copy) or 'paste'. The answer comes later: modal_result()"""
    try:
        import platform
        if not _modal_ready[0]:
            platform.window.eval(MODAL_JS)
            _modal_ready[0] = True
        platform.window.daModal(title, text, mode, ok_label)
        return True
    except Exception:
        return False


def modal_result():
    """None while the box is open; then (True, text) or (False, None) if cancelled"""
    try:
        import platform
        v = platform.window.daModalResult
    except Exception:
        return False, None
    if v is None or str(v) in ("null", "undefined"):
        return None
    try:
        import json
        r = json.loads(str(v))
        platform.window.daModalResult = None
    except Exception:
        return False, None
    return (True, str(r.get("text") or "")) if r.get("ok") else (False, None)


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
