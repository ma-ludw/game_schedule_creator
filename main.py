import sys
from multiprocessing import freeze_support

from PySide6.QtWidgets import QApplication

from application_window import Window
from ui_styles import configure_application_style


def main() -> None:
    application = QApplication(sys.argv)
    configure_application_style(application)
    window = Window()
    window.show()
    sys.exit(application.exec())


if __name__ == "__main__":
    freeze_support()
    main()
