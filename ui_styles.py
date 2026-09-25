from PySide6.QtWidgets import QApplication


WINDOW_STYLESHEET = """
QMainWindow {
    background: #0f172a;
    color: #e2e8f0;
}
QWidget {
    color: #e2e8f0;
}
QLabel {
    font-size: 13px;
    font-weight: 600;
    color: #cbd5e1;
    padding: 4px 0px;
}
QSpinBox, QLineEdit, QTableWidget {
    background: #111827;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 8px 10px;
    selection-background-color: #38bdf8;
    selection-color: #082f49;
    color: #f8fafc;
}
QSpinBox:focus, QTableWidget:focus, QLineEdit:focus {
    border: 1px solid #38bdf8;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0ea5e9, stop:1 #0284c7);
    border: none;
    border-radius: 12px;
    color: #f8fafc;
    font-size: 14px;
    font-weight: 700;
    min-height: 44px;
    padding: 0 22px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #0ea5e9);
}
QPushButton:checked {
    background: #047857;
    border: 2px solid #6ee7b7;
    color: #f8fafc;
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #075985);
}
QProgressBar {
    border: 1px solid #334155;
    border-radius: 8px;
    background: #111827;
    text-align: center;
    color: #e2e8f0;
    font-weight: 600;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
    border-radius: 7px;
}
QHeaderView::section {
    background: #1e293b;
    color: #f8fafc;
    font-weight: 700;
    padding: 8px 10px;
    border: 1px solid #334155;
}
QTableWidget {
    gridline-color: #334155;
    alternate-background-color: #0b1220;
}
QTableWidget::item {
    padding: 8px 6px;
    color: #f8fafc;
}
QTableWidget::item:selected {
    background: #0ea5e9;
    color: #f8fafc;
}
QMenuBar {
    background: #111827;
    color: #e2e8f0;
    border-bottom: 1px solid #334155;
}
QMenu {
    background: #111827;
    color: #e2e8f0;
    border: 1px solid #334155;
}
QMenu::item:selected {
    background: #0ea5e9;
}
.titleLabel {
    color: #f8fafc;
    font-size: 24px;
    font-weight: 700;
}
.subtitleLabel {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 500;
    margin-bottom: 4px;
}
"""

APPLICATION_STYLESHEET = """
QMainWindow { background: #0f172a; color: #e2e8f0; }
QWidget { background: #0f172a; color: #e2e8f0; }
QLabel { color: #e2e8f0; }
QSpinBox, QTableWidget {
    background: #111827;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 10px;
}
QPushButton {
    background: #0ea5e9;
    color: #f8fafc;
    border: none;
    border-radius: 12px;
}
QMenuBar, QMenu { background: #111827; color: #e2e8f0; }
QHeaderView::section { background: #1e293b; color: #f8fafc; }
"""


def configure_application_style(application: QApplication) -> None:
    application.setStyle("Fusion")
    application.setStyleSheet(APPLICATION_STYLESHEET)
