# UI with optional PySide6 window and GIF mouth. Falls back to console if
PySide6 isn't available.
from __future__ import annotations
import os, threading, sys
from datetime import datetime
# --- Console fallback ---
class _ConsoleUI:
def set_state(self, state: str):
print(f"[ui] state = {state}")
def show_user(self, text: str):
print(f" {text}")
def show_karen(self, text: str):
  print(f" {text}")
def toast(self, msg: str):
print(f"[toast] {msg}")
def error(self, msg: str):
print(f"[error] {msg}")
def ping(self):
print("[ui] *beep*")
# --- Try Qt UI ---
try:
from PySide6 import QtCore, QtGui, QtWidgets
class _KarenWindow(QtWidgets.QMainWindow):
def __init__(self, gif_path: str):
super().__init__()
self.setWindowTitle("Karen")
self.setCursor(QtCore.Qt.BlankCursor)
self.setStyleSheet("background: #070a0f; color: #d9f1ff; fontfamily: Inter, Arial;")
self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
self.showFullScreen()
# ESC and Ctrl+Alt+Q to quit cleanly (works under systemd too)
esc = QtGui.QShortcut(QtGui.QKeySequence("Esc"), self)
esc.activated.connect(QtWidgets.QApplication.quit)
quit_combo = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Alt+Q"), self)
quit_combo.activated.connect(QtWidgets.QApplication.quit)
# central layout
central = QtWidgets.QWidget()
self.setCentralWidget(central)
v = QtWidgets.QVBoxLayout(central)
v.setContentsMargins(40,40,40,40)
v.setSpacing(16)
# top bar: state + net dot
top = QtWidgets.QHBoxLayout()
self.state_lbl = QtWidgets.QLabel("IDLE")
self.state_lbl.setStyleSheet("font-size: 18pt; letter-spacing:
2px;")
top.addWidget(self.state_lbl)
top.addStretch(1)
self.net_dot = QtWidgets.QLabel("●")
self.net_dot.setStyleSheet("font-size: 18pt; color: #2ecc71;")
top.addWidget(self.net_dot)
v.addLayout(top)
# GIF mouth
self.gif_lbl = QtWidgets.QLabel()
self.gif_lbl.setAlignment(QtCore.Qt.AlignCenter)
v.addWidget(self.gif_lbl, 1)
if os.path.exists(gif_path):
self.movie = QtGui.QMovie(gif_path)
self.movie.setCacheMode(QtGui.QMovie.CacheAll)
self.movie.setSpeed(100)
self.gif_lbl.setMovie(self.movie)
self.movie.jumpToFrame(0)
else:
self.movie = None
self.gif_lbl.setText("(missing assets/karen_mouth.gif)")
# transcript
self.transcript = QtWidgets.QTextEdit()
self.transcript.setReadOnly(True)
self.transcript.setStyleSheet("background: #0c1118; border: 1px
solid #1c2430; font-size: 12pt;")
v.addWidget(self.transcript, 1)
def set_state(self, state: str):
self.state_lbl.setText(state.upper())
# Play GIF only while speaking
if self.movie:
if state.lower() == "speaking":
self.movie.start()
else:
self.movie.stop()
self.movie.jumpToFrame(0)
def append(self, who: str, text: str):
ts = datetime.now().strftime('%H:%M:%S')
self.transcript.append(f"<b>[{ts}] {who}:</b>
{QtGui.QGuiApplication.translate('', text)}")
self.transcript.moveCursor(QtGui.QTextCursor.End)
def set_net_ok(self, ok: bool):
self.net_dot.setStyleSheet("font-size: 18pt; color: %s;" %
("#2ecc71" if ok else "#e67e22"))
class _QtUI(QtCore.QObject):
_sig_state = QtCore.Signal(str)
_sig_user = QtCore.Signal(str)
_sig_karen = QtCore.Signal(str)
_sig_toast = QtCore.Signal(str)
_sig_error = QtCore.Signal(str)
_sig_netok = QtCore.Signal(bool)
def __init__(self, gif_path: str = "assets/karen_mouth.gif"):
super().__init__()
self._app = QtWidgets.QApplication.instance() or
QtWidgets.QApplication(sys.argv)
self.win = _KarenWindow(gif_path)
self._sig_state.connect(self.win.set_state)
self._sig_user.connect(lambda t: self.win.append("You", t))
self._sig_karen.connect(lambda t: self.win.append("Karen", t))
self._sig_toast.connect(lambda t: self.win.append("*", t))
self._sig_error.connect(lambda t: self.win.append("!", t))
self._sig_netok.connect(self.win.set_net_ok)
# run the Qt loop in a dedicated thread
self._thread = threading.Thread(target=self._app.exec, daemon=True)
self._thread.start()
# Public API used by the app
def set_state(self, state: str): self._sig_state.emit(state)
def show_user(self, text: str): self._sig_user.emit(text)
def show_karen(self, text: str): self._sig_karen.emit(text)
def toast(self, msg: str): self._sig_toast.emit(msg)
def error(self, msg: str): self._sig_error.emit(msg)
def ping(self): pass
def set_net_ok(self, ok: bool): self._sig_netok.emit(ok)
HAS_QT = True
except Exception:
HAS_QT = False
# exported UI class chooses Qt if available
class UI(_QtUI if 'HAS_QT' in globals() and HAS_QT else _ConsoleUI):
def __init__(self, *a, **k):
if 'HAS_QT' in globals() and HAS_QT:
super().__init__(*a, **k)
else:
super().__init__()

