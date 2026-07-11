"""Тёмная тема в духе Discord/Nord: плоские поверхности, blurple-акцент."""

from pathlib import Path

_ASSETS = Path(__file__).resolve().parent / "assets"
_ARROW_DOWN = (_ASSETS / "chevron-down.svg").as_posix()
_ARROW_UP = (_ASSETS / "chevron-up.svg").as_posix()

ACCENT = "#5865f2"
ACCENT_HOVER = "#4752c4"
BG = "#1e1f22"          # самый тёмный слой (как сайдбар Discord)
SURFACE = "#2b2d31"     # карточки и панели
SURFACE_2 = "#313338"   # поля ввода, ховеры
SURFACE_3 = "#383a40"   # ховер поверх SURFACE_2
BORDER = "#3f4147"
TEXT = "#dbdee1"
TEXT_DIM = "#949ba4"
OK = "#23a55a"
ERR = "#f23f43"
WARN = "#f0b232"

STYLESHEET = f"""
* {{
    font-family: "Inter", "Noto Sans", "Cantarell", sans-serif;
    font-size: 14px;
}}
QMainWindow, QWidget#central {{
    background: {BG};
    color: {TEXT};
}}
QLabel {{
    color: {TEXT};
    background: transparent;
}}
QLabel#appTitle {{
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
}}
QLabel#hint {{
    color: {TEXT_DIM};
    font-size: 15px;
}}
QLabel#dim {{
    color: {TEXT_DIM};
    font-size: 12px;
}}

QComboBox, QSpinBox {{
    background: {BG};
    color: {TEXT};
    border: none;
    border-radius: 6px;
    padding: 7px 12px;
    min-height: 22px;
}}
QComboBox:hover, QSpinBox:hover {{
    background: {SURFACE_2};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: url("{_ARROW_DOWN}");
    width: 10px;
    height: 6px;
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BG};
    border-radius: 8px;
    selection-background-color: {ACCENT};
    selection-color: #ffffff;
    outline: none;
    padding: 4px;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 18px;
    background: transparent;
    border: none;
    border-radius: 4px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background: {SURFACE_3};
}}
QSpinBox::up-arrow {{
    image: url("{_ARROW_UP}");
    width: 8px;
    height: 5px;
}}
QSpinBox::down-arrow {{
    image: url("{_ARROW_DOWN}");
    width: 8px;
    height: 5px;
}}

QPushButton {{
    background: {SURFACE_2};
    color: {TEXT};
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {SURFACE_3};
}}
QPushButton:pressed {{
    background: {BORDER};
}}
QPushButton:disabled {{
    color: #6d6f78;
    background: {SURFACE};
}}
QPushButton#primary {{
    background: {ACCENT};
    color: #ffffff;
    padding: 9px 22px;
}}
QPushButton#primary:hover {{
    background: {ACCENT_HOVER};
}}
QPushButton#primary:disabled {{
    background: {SURFACE_2};
    color: #6d6f78;
}}
QPushButton#danger:hover {{
    background: {ERR};
    color: #ffffff;
}}
QPushButton#outputField {{
    background: {BG};
    color: {TEXT};
    border: none;
    border-radius: 6px;
    padding: 7px 12px;
    font-weight: 400;
    text-align: left;
}}
QPushButton#outputField:hover {{
    background: {SURFACE_2};
    color: #ffffff;
}}
QPushButton#outputField:disabled {{
    color: #6d6f78;
    background: {BG};
}}
QPushButton#rowRemove {{
    background: transparent;
    border: none;
    color: {TEXT_DIM};
    font-size: 16px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 6px;
}}
QPushButton#rowRemove:hover {{
    background: {ERR};
    color: #ffffff;
}}

QFrame#fileRow {{
    background: {SURFACE_2};
    border: none;
    border-radius: 8px;
}}
QFrame#fileRow:hover {{
    background: {SURFACE_3};
}}
QFrame#dropZone {{
    background: {SURFACE};
    border: 2px dashed transparent;
    border-radius: 12px;
}}
QFrame#dropZone[dragActive="true"] {{
    border-color: {ACCENT};
    background: rgba(88, 101, 242, 0.08);
}}
QFrame#controlsBar {{
    background: {SURFACE};
    border: none;
    border-radius: 12px;
}}

QProgressBar {{
    background: {BG};
    border: none;
    border-radius: 3px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 3px;
}}

QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BG};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QStatusBar {{
    background: {BG};
    color: {TEXT_DIM};
    border-top: 1px solid {SURFACE};
}}
QStatusBar::item {{
    border: none;
}}
QToolTip {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BG};
    padding: 4px 8px;
    border-radius: 6px;
}}
"""
