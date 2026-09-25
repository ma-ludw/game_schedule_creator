from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableWidgetItem,
    QMessageBox,
    QFileDialog,
    QHeaderView,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QGroupBox,
    QLabel,
    QPushButton,
    QSizePolicy,
    QLineEdit,
    QSpinBox,
    QScrollArea,
    QStackedWidget,
    QFormLayout,
)

import sys
import pandas as pd

from MainWindow import Ui_MainWindow
from Jungschar import Jungschar
from ScheduleGenerator import ScheduleGenerator


debug = False


class Window(QMainWindow):
    def __init__(self):
        super().__init__()

        # init window
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Spielplan Generator")
        self.setMinimumSize(1100, 700)
        self._apply_user_friendly_style()

        # init control elements
        self.ui.spinBox_n_jungscharen.valueChanged.connect(self.n_jungscharen_changed)
        self.ui.pushButton_generate.clicked.connect(self.generate)
        self.ui.spinBox_n_games.valueChanged.connect(self.n_games_changed)
        self.ui.spinBox_n_rounds.valueChanged.connect(self.n_rounds_changed)

        self._configure_spinboxes()

        # init variables
        self.jungscharen: list[Jungschar] = [Jungschar(0, 1)]
        self.n_jungscharen_changed(self.ui.spinBox_n_jungscharen.value())
        self.game_names = []
        self.n_games_changed(self.ui.spinBox_n_games.value())
        self.n_rounds = self.ui.spinBox_n_rounds.value()

        self.ui.pushButton_generate.setDefault(True)
        self.ui.pushButton_generate.setCursor(Qt.PointingHandCursor)
        self.ui.pushButton_generate.setToolTip("Generiert den Spielplan und speichert ihn als Excel-Datei.")

        self._build_dashboard_layout()
        self.refresh_summary()

        # show Main Window
        self.show()

    def _configure_spinboxes(self):
        self.ui.spinBox_n_jungscharen.setRange(1, 12)
        self.ui.spinBox_n_games.setRange(1, 30)
        self.ui.spinBox_n_rounds.setRange(1, 20)

        self.ui.spinBox_n_jungscharen.setToolTip("Anzahl der Jungscharen")
        self.ui.spinBox_n_games.setToolTip("Anzahl der Spiele")
        self.ui.spinBox_n_rounds.setToolTip("Anzahl der Spielrunden")

    def _build_dashboard_layout(self):
        old_layout = self.ui.centralwidget.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget() is not None:
                    item.widget().setParent(None)

        main_container = QWidget(self)
        self.setCentralWidget(main_container)

        main_layout = QHBoxLayout(main_container)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(18)

        sidebar = QWidget(main_container)
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(10)

        self.nav_buttons = []
        for label in ["Einrichtung", "Spiele", "Vorschau"]:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setChecked(label == "Einrichtung")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked, index=len(self.nav_buttons): self._show_page(index))
            self.nav_buttons.append(button)
            sidebar_layout.addWidget(button)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sidebar_layout.addWidget(spacer)

        main_layout.addWidget(sidebar, 0)

        content = QWidget(main_container)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self.ui.titleLabel)
        content_layout.addWidget(self.ui.subtitleLabel)

        self.pages = QStackedWidget(content)
        self.pages.addWidget(self._create_setup_page())
        self.pages.addWidget(self._create_games_page())
        self.pages.addWidget(self._create_preview_page())
        content_layout.addWidget(self.pages, 1)
        main_layout.addWidget(content, 1)

        self.ui.centralwidget = main_container
        self._sync_editors()

    def _create_setup_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)
        intro = QLabel("Lege zunächst die Jungscharen an. Die Gruppennamen werden automatisch erzeugt und können anschließend direkt angepasst werden.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        count_row = QHBoxLayout()
        count_row.setSpacing(12)
        count_row.addWidget(QLabel("Anzahl Jungscharen"))
        count_row.addWidget(self.ui.spinBox_n_jungscharen)
        count_row.addStretch()
        layout.addLayout(count_row)

        self.team_editor = QWidget()
        self.team_editor_layout = QVBoxLayout(self.team_editor)
        self.team_editor_layout.setContentsMargins(8, 8, 8, 8)
        self.team_editor_layout.setSpacing(12)
        team_scroll = QScrollArea()
        team_scroll.setWidgetResizable(True)
        team_scroll.setWidget(self.team_editor)
        layout.addWidget(team_scroll, 1)

        self.group_editor = QWidget()
        self.group_editor_layout = QFormLayout(self.group_editor)
        self.group_editor_layout.setContentsMargins(8, 8, 8, 8)
        self.group_editor_layout.setHorizontalSpacing(16)
        self.group_editor_layout.setVerticalSpacing(10)
        layout.addWidget(QLabel("Gruppennamen"))
        group_scroll = QScrollArea()
        group_scroll.setWidgetResizable(True)
        group_scroll.setMinimumHeight(220)
        group_scroll.setWidget(self.group_editor)
        layout.addWidget(group_scroll, 1)
        return page

    def _create_games_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        intro = QLabel("Vergib für jedes Spiel einen gut erkennbaren Namen.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        count_row = QHBoxLayout()
        count_row.addWidget(QLabel("Anzahl Spiele"))
        count_row.addWidget(self.ui.spinBox_n_games)
        count_row.addStretch()
        layout.addLayout(count_row)
        self.game_editor = QWidget()
        self.game_editor_layout = QFormLayout(self.game_editor)
        game_scroll = QScrollArea()
        game_scroll.setWidgetResizable(True)
        game_scroll.setWidget(self.game_editor)
        layout.addWidget(game_scroll, 1)
        return page

    def _create_preview_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Prüfe die Zusammenfassung und erstelle anschließend die Excel-Datei."))
        summary_box = QGroupBox("Übersicht")
        summary_layout = QVBoxLayout(summary_box)
        self.summary_groups = QLabel()
        self.summary_games = QLabel()
        self.summary_rounds = QLabel()
        for widget in [self.summary_groups, self.summary_games, self.summary_rounds]:
            summary_layout.addWidget(widget)
        layout.addWidget(summary_box)
        rounds_row = QHBoxLayout()
        rounds_row.addWidget(QLabel("Anzahl Runden"))
        rounds_row.addWidget(self.ui.spinBox_n_rounds)
        rounds_row.addStretch()
        layout.addLayout(rounds_row)
        layout.addStretch()
        layout.addWidget(self.ui.pushButton_generate)
        layout.addWidget(self.ui.progressBar_generate)
        return page

    def _show_page(self, index):
        self.pages.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)
                child_layout.deleteLater()

    def _sync_editors(self):
        if not hasattr(self, "team_editor_layout"):
            return
        self._clear_layout(self.team_editor_layout)
        self._clear_layout(self.group_editor_layout)
        self._clear_layout(self.game_editor_layout)

        self.team_name_inputs = []
        self.group_count_inputs = []
        for index, js in enumerate(self.jungscharen):
            name_input = QLineEdit(js.name)
            count_input = QSpinBox()
            count_input.setRange(1, 30)
            count_input.setValue(js.n_groups)
            name_input.editingFinished.connect(lambda i=index, w=name_input: self._team_name_changed(i, w))
            count_input.valueChanged.connect(lambda value, i=index: self._group_count_changed(i, value))
            self.team_name_inputs.append(name_input)
            self.group_count_inputs.append(count_input)
            row = QHBoxLayout()
            row.setSpacing(12)
            row.addWidget(QLabel(f"Jungschar {index + 1}"))
            name_input.setMinimumWidth(180)
            row.addWidget(name_input, 1)
            row.addWidget(QLabel("Gruppen"))
            row.addWidget(count_input)
            self.team_editor_layout.addLayout(row)

        for js in self.jungscharen:
            for group_index, group in enumerate(js.groups):
                input_widget = QLineEdit(group.name)
                input_widget.editingFinished.connect(
                    lambda j=js, g=group, w=input_widget: self._group_name_changed(j, g, w)
                )
                self.group_editor_layout.addRow(f"{js.name} {group_index + 1}", input_widget)

        self.game_name_inputs = []
        for index, game_name in enumerate(self.game_names):
            input_widget = QLineEdit(game_name)
            input_widget.editingFinished.connect(lambda i=index, w=input_widget: self._game_name_changed(i, w))
            self.game_name_inputs.append(input_widget)
            self.game_editor_layout.addRow(f"Spiel {index + 1}", input_widget)

    def _team_name_changed(self, index, widget):
        self.jungscharen[index].name = widget.text().strip() or self._default_jungschar_name(index)
        widget.setText(self.jungscharen[index].name)
        self.set_upt_group_naming_table()
        self._sync_editors()

    def _group_count_changed(self, index, value):
        self.jungscharen[index].change_n_groups(value)
        self.set_upt_group_naming_table()
        self._sync_editors()

    def _group_name_changed(self, js, group, widget):
        group.name = widget.text().strip() or self._default_group_name(js.name, js.groups.index(group))
        widget.setText(group.name)

    def _game_name_changed(self, index, widget):
        self.game_names[index] = widget.text().strip() or self._default_game_name(index)
        widget.setText(self.game_names[index])
        self.refresh_summary()

    def refresh_summary(self):
        if not hasattr(self, "summary_groups"):
            return
        total_groups = sum(js.n_groups for js in self.jungscharen)
        self.summary_groups.setText(f"Gesamtgruppen: {total_groups}")
        self.summary_games.setText(f"Spiele: {len(self.game_names)}")
        self.summary_rounds.setText(f"Runden: {self.n_rounds}")

    def _apply_user_friendly_style(self):
        self.setStyleSheet(
            """
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
            QSpinBox:focus, QTableWidget:focus {
                border: 1px solid #38bdf8;
            }
            QLineEdit:focus {
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
        )

    def _configure_table(self, table):
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(table.SelectionBehavior.SelectRows)
        table.setSelectionMode(table.SelectionMode.SingleSelection)
        table.setEditTriggers(table.EditTrigger.DoubleClicked | table.EditTrigger.EditKeyPressed)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def _default_jungschar_name(self, index: int) -> str:
        return f"Jungschar {index + 1}"

    def _default_group_name(self, js_name: str, index: int) -> str:
        return f"{js_name} Gruppe {index + 1}"

    def _default_game_name(self, index: int) -> str:
        return f"Spiel {index + 1}"

    def n_jungscharen_changed(self, n_jungscharen: int):
        while len(self.jungscharen) < n_jungscharen:
            self.jungscharen.append(Jungschar(len(self.jungscharen), 1))
        while len(self.jungscharen) > n_jungscharen:
            self.jungscharen.pop()

        for row in range(n_jungscharen):
            js = self.jungscharen[row]
            js.name = js.name.strip() if js.name and js.name.strip() else self._default_jungschar_name(row)
        self.set_upt_group_naming_table()
        self.refresh_summary()
        self._sync_editors()

    def set_upt_group_naming_table(self):
        for js in self.jungscharen:
            for g_idx, g in enumerate(js.groups):
                js_name = js.name.strip() if js.name and js.name.strip() else self._default_jungschar_name(
                    self.jungscharen.index(js)
                )
                g.name = g.name.strip() if g.name and g.name.strip() else self._default_group_name(js_name, g_idx)
        self.refresh_summary()
        if hasattr(self, "team_editor_layout"):
            self._sync_editors()

    def n_games_changed(self, value: int):
        while value > len(self.game_names):
            self.game_names.append(self._default_game_name(len(self.game_names)))
        while value < len(self.game_names):
            self.game_names.pop()
        self.refresh_summary()
        if hasattr(self, "game_editor_layout"):
            self._sync_editors()

    def n_rounds_changed(self, value: int):
        self.n_rounds = value
        self.refresh_summary()

    # def enable_multiple_jungscharen(self, enable: bool):
    #     self.ui.tableWidget_n_groups.setEnabled(enable)
    #     self.ui.tableWidget_group_names_jungscharen.setEnabled(enable)

    def generate(self):
        try:
            schedulegenerator = ScheduleGenerator(
                self.jungscharen,
                self.n_rounds,
                len(self.game_names),
                self.game_names,
                progress_update_callback=self.ui.progressBar_generate.setValue
            )
            schedule, game_counts, team_matchups, game_team_counts = schedulegenerator.generate_schedule()
            print(schedule)
        except Exception as e:
            if debug:
                raise e  # re-raise the exception for debugging
            else:
                QMessageBox.critical(self, "Error", f"An error occurred while generating the schedule: {e}")
            return
        
        # Save schedule to Excel file
        if debug:
            file_path = 'schedule.xlsx'
        else:
            # Ask the user where to save the schedule file
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Schedule", "schedule.xlsx", "Excel Files (*.xlsx)")
            if not file_path:
                file_path = 'schedule.xlsx'  # User cancelled

        with pd.ExcelWriter(file_path) as writer:
                schedule.to_excel(writer, sheet_name='Schedule')
                game_counts.to_excel(writer, sheet_name='Game Counts', index=False)
                team_matchups.to_excel(writer, sheet_name='Team Matchups', index=False)
                game_team_counts.to_excel(writer, sheet_name='Game Team Counts', index=False)





def main():
    App = QApplication(sys.argv)
    App.setStyle("Fusion")

    dark_palette = {
        "window": "#0f172a",
        "window_text": "#e2e8f0",
        "base": "#111827",
        "alternate_base": "#0b1220",
        "text": "#f8fafc",
        "button": "#0ea5e9",
        "button_text": "#f8fafc",
        "bright_text": "#f8fafc",
        "highlight": "#38bdf8",
        "highlighted_text": "#082f49",
        "placeholder_text": "#94a3b8",
    }

    App.setStyleSheet(
        f"""
        QMainWindow {{ background: {dark_palette['window']}; color: {dark_palette['window_text']}; }}
        QWidget {{ background: {dark_palette['window']}; color: {dark_palette['window_text']}; }}
        QLabel {{ color: {dark_palette['window_text']}; }}
        QSpinBox, QTableWidget {{ background: {dark_palette['base']}; color: {dark_palette['text']}; border: 1px solid #334155; border-radius: 10px; }}
        QPushButton {{ background: {dark_palette['button']}; color: {dark_palette['button_text']}; border: none; border-radius: 12px; }}
        QMenuBar, QMenu {{ background: {dark_palette['base']}; color: {dark_palette['window_text']}; }}
        QHeaderView::section {{ background: #1e293b; color: #f8fafc; }}
        """
    )

    window = Window()

    # start the app
    sys.exit(App.exec())



if __name__ == "__main__":
    main()
