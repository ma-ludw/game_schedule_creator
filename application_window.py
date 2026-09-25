from pathlib import Path

import pandas as pd
from PySide6.QtCore import QThread, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QButtonGroup,
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
    QLayout,
)

from Group import Group
from Jungschar import Jungschar
from MainWindow import Ui_MainWindow
from ScheduleGenerator import ScheduleResult
from manual_dialog import ManualDialog
from resources import resource_path
from schedule_worker import ScheduleWorker
from ui_styles import WINDOW_STYLESHEET


DEBUG = False


class Window(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.menuBar().hide()
        self.manual_window: ManualDialog | None = None
        self.worker_thread: QThread | None = None
        self.worker: ScheduleWorker | None = None
        self.setWindowTitle("Spielplan Generator")
        self.setWindowIcon(QIcon(str(resource_path("app_icon.ico"))))
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(WINDOW_STYLESHEET)

        self.ui.spinBox_n_jungscharen.valueChanged.connect(self.n_jungscharen_changed)
        self.ui.pushButton_generate.clicked.connect(self.generate)
        self.ui.spinBox_n_games.valueChanged.connect(self.n_games_changed)
        self.ui.spinBox_n_rounds.valueChanged.connect(self.n_rounds_changed)
        self._configure_spinboxes()

        self.jungscharen: list[Jungschar] = [Jungschar(0, 1)]
        self._set_spinbox_value(self.ui.spinBox_n_jungscharen, 2)
        self.n_jungscharen_changed(self.ui.spinBox_n_jungscharen.value())
        self.game_names: list[str] = []
        self.n_games_changed(self.ui.spinBox_n_games.value())
        self.n_rounds = self.ui.spinBox_n_rounds.value()

        self.ui.pushButton_generate.setDefault(True)
        self.ui.pushButton_generate.setToolTip("Generiert den Spielplan und speichert ihn als Excel-Datei.")

        self._build_dashboard_layout()
        self.refresh_summary()
        self.show()

    @staticmethod
    def _set_spinbox_value(spinbox: QSpinBox, value: int) -> None:
        was_blocked = spinbox.blockSignals(True)
        spinbox.setValue(value)
        spinbox.blockSignals(was_blocked)

    def _configure_spinboxes(self) -> None:
        self.ui.spinBox_n_jungscharen.setRange(1, 12)
        self.ui.spinBox_n_games.setRange(1, 30)
        self.ui.spinBox_n_rounds.setRange(1, 20)

        self.ui.spinBox_n_jungscharen.setToolTip("Anzahl der Jungscharen")
        self.ui.spinBox_n_games.setToolTip("Anzahl der Spiele")
        self.ui.spinBox_n_rounds.setToolTip("Anzahl der Spielrunden")

    def open_manual(self) -> None:
        if self.manual_window is None:
            self.manual_window = ManualDialog(self)

        self.manual_window.show()
        self.manual_window.raise_()
        self.manual_window.activateWindow()

    def _build_dashboard_layout(self) -> None:
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

        manual_button = QPushButton("Anleitung")
        manual_button.setCursor(Qt.CursorShape.PointingHandCursor)
        manual_button.setToolTip("Öffnet das deutschsprachige Benutzerhandbuch.")
        manual_button.clicked.connect(self.open_manual)
        sidebar_layout.addWidget(manual_button)

        sidebar_layout.addSpacing(30)

        self.nav_buttons: list[QPushButton] = []
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.idClicked.connect(self._show_page)
        for index, label in enumerate(["Gruppen", "Spiele", "Runden"]):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.nav_group.addButton(button, index)
            self.nav_buttons.append(button)
            sidebar_layout.addWidget(button)

        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
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

    def _create_setup_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)
        intro = QLabel(
            "Lege zunächst die Jungscharen an. Ändere den Jungschar-Namen im "
            "Eingabefeld neben „Jungschar … – Name“ und die Teamnamen im Abschnitt "
            "„Teamnamen (hier ändern)“ weiter unten. Teams derselben Jungschar "
            "spielen nicht gegeneinander. Sollen alle Teams gegeneinander spielen "
            "können, lege jedes Team als eigene Jungschar mit einem Team an."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        count_row = QHBoxLayout()
        count_row.setSpacing(12)
        count_row.addWidget(QLabel("Anzahl Jungscharen"))
        count_row.addWidget(self.ui.spinBox_n_jungscharen)
        count_row.addStretch()
        layout.addLayout(count_row)

        layout.addWidget(QLabel("Jungschar-Namen und Anzahl Teams"))
        self.team_editor = QWidget()
        self.team_editor_layout = QVBoxLayout(self.team_editor)
        self.team_editor_layout.setContentsMargins(8, 8, 8, 8)
        self.team_editor_layout.setSpacing(12)
        self.team_editor_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        team_scroll = QScrollArea()
        team_scroll.setWidgetResizable(True)
        team_scroll.setWidget(self.team_editor)
        layout.addWidget(team_scroll, 1)

        self.group_editor = QWidget()
        self.group_editor_layout = QFormLayout(self.group_editor)
        self.group_editor_layout.setContentsMargins(8, 8, 8, 8)
        self.group_editor_layout.setHorizontalSpacing(16)
        self.group_editor_layout.setVerticalSpacing(10)
        layout.addWidget(QLabel("Teamnamen (hier ändern)"))
        group_scroll = QScrollArea()
        group_scroll.setWidgetResizable(True)
        group_scroll.setMinimumHeight(220)
        group_scroll.setWidget(self.group_editor)
        layout.addWidget(group_scroll, 1)
        return page

    def _create_games_page(self) -> QWidget:
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

    def _create_preview_page(self) -> QWidget:
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
        search_time_row = QHBoxLayout()
        search_time_row.addWidget(QLabel("Suchzeit (Sekunden)"))
        self.search_time_input = QSpinBox()
        self.search_time_input.setRange(1, 86_400)
        self.search_time_input.setValue(60)
        self.search_time_input.setToolTip(
            "Legt fest, wie lange nach einem möglichst ausgewogenen Spielplan gesucht wird."
        )
        search_time_row.addWidget(self.search_time_input)
        search_time_row.addStretch()
        layout.addLayout(search_time_row)
        layout.addStretch()
        layout.addWidget(self.ui.pushButton_generate)
        self.cancel_button = QPushButton("Generierung abbrechen")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_generation)
        layout.addWidget(self.cancel_button)
        self.generation_status = QLabel("Bereit zur Generierung.")
        self.generation_status.setWordWrap(True)
        self.generation_status.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.generation_status)
        self.reset_button = QPushButton("Eingaben zurücksetzen")
        self.reset_button.clicked.connect(self.reset_form)
        layout.addWidget(self.reset_button)
        layout.addWidget(self.ui.progressBar_generate)
        return page

    def _show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)

    def _clear_layout(self, layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)
                child_layout.deleteLater()

    def _sync_editors(self) -> None:
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
            name_input.editingFinished.connect(
                lambda i=index, widget=name_input: self._team_name_changed(i, widget)
            )
            count_input.valueChanged.connect(lambda value, i=index: self._group_count_changed(i, value))
            self.team_name_inputs.append(name_input)
            self.group_count_inputs.append(count_input)
            row = QHBoxLayout()
            row.setSpacing(12)
            row.addWidget(QLabel(f"Jungschar {index + 1} – Name"))
            name_input.setMinimumWidth(180)
            name_input.setToolTip("Hier den Namen dieser Jungschar ändern.")
            row.addWidget(name_input, 1)
            row.addWidget(QLabel("Teams"))
            row.addWidget(count_input)
            self.team_editor_layout.addLayout(row)

        for js in self.jungscharen:
            for group_index, group in enumerate(js.groups):
                input_widget = QLineEdit(group.name)
                input_widget.editingFinished.connect(
                    lambda j=js, g=group, w=input_widget: self._group_name_changed(j, g, w)
                )
                input_widget.setToolTip("Hier den Namen dieses Teams ändern.")
                self.group_editor_layout.addRow(
                    f"{js.name} – Team {group_index + 1}", input_widget
                )

        self.game_name_inputs = []
        for index, game_name in enumerate(self.game_names):
            input_widget = QLineEdit(game_name)
            input_widget.editingFinished.connect(
                lambda i=index, widget=input_widget: self._game_name_changed(i, widget)
            )
            self.game_name_inputs.append(input_widget)
            self.game_editor_layout.addRow(f"Spiel {index + 1}", input_widget)

    def _team_name_changed(self, index: int, widget: QLineEdit) -> None:
        self.jungscharen[index].name = (
            widget.text().strip() or self._default_jungschar_name(index)
        )
        widget.setText(self.jungscharen[index].name)
        self._update_team_names()
        self._sync_editors()

    def _group_count_changed(self, index: int, value: int) -> None:
        self.jungscharen[index].change_n_groups(value)
        self._update_team_names()
        self._sync_editors()

    def _group_name_changed(
        self,
        js: Jungschar,
        group: Group,
        widget: QLineEdit,
    ) -> None:
        group.name = (
            widget.text().strip()
            or self._default_group_name(js.groups.index(group))
        )
        widget.setText(group.name)

    def _game_name_changed(self, index: int, widget: QLineEdit) -> None:
        self.game_names[index] = widget.text().strip() or self._default_game_name(index)
        widget.setText(self.game_names[index])
        self.refresh_summary()

    def refresh_summary(self) -> None:
        if not hasattr(self, "summary_groups"):
            return
        total_groups = sum(js.n_groups for js in self.jungscharen)
        self.summary_groups.setText(f"Gesamtgruppen: {total_groups}")
        self.summary_games.setText(f"Spiele: {len(self.game_names)}")
        self.summary_rounds.setText(f"Runden: {self.n_rounds}")

    @staticmethod
    def _default_jungschar_name(index: int) -> str:
        return f"Jungschar {index + 1}"

    @staticmethod
    def _default_group_name(index: int) -> str:
        return f"Team {index + 1}"

    @staticmethod
    def _default_game_name(index: int) -> str:
        return f"Spiel {index + 1}"

    def n_jungscharen_changed(self, n_jungscharen: int) -> None:
        while len(self.jungscharen) < n_jungscharen:
            self.jungscharen.append(Jungschar(len(self.jungscharen), 1))
        while len(self.jungscharen) > n_jungscharen:
            self.jungscharen.pop()

        for row in range(n_jungscharen):
            js = self.jungscharen[row]
            js.name = (
                js.name.strip()
                if js.name and js.name.strip()
                else self._default_jungschar_name(row)
            )
        self._update_team_names()
        self.refresh_summary()
        self._sync_editors()

    def _update_team_names(self) -> None:
        for js in self.jungscharen:
            for g_idx, g in enumerate(js.groups):
                g.name = (
                    g.name.strip()
                    if g.name and g.name.strip()
                    else self._default_group_name(g_idx)
                )
        self.refresh_summary()

    def n_games_changed(self, value: int) -> None:
        while value > len(self.game_names):
            self.game_names.append(self._default_game_name(len(self.game_names)))
        while value < len(self.game_names):
            self.game_names.pop()
        self.refresh_summary()
        if hasattr(self, "game_editor_layout"):
            self._sync_editors()

    def n_rounds_changed(self, value: int) -> None:
        self.n_rounds = value
        self.refresh_summary()

    def validate_inputs(self) -> str | None:
        if len(self.jungscharen) < 2:
            return "Mindestens zwei Jungscharen werden benötigt."
        if any(not js.name.strip() for js in self.jungscharen):
            return "Bitte benennen Sie alle Jungscharen."
        if any(not group.name.strip() for js in self.jungscharen for group in js.groups):
            return "Bitte benennen Sie alle Gruppen."
        if not self.game_names or any(not name.strip() for name in self.game_names):
            return "Bitte benennen Sie alle Spiele."
        return None

    def reset_form(self) -> None:
        answer = QMessageBox.question(
            self,
            "Eingaben zurücksetzen",
            "Möchten Sie alle Eingaben auf die Standardwerte zurücksetzen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.jungscharen = []
        for index in range(2):
            jungschar = Jungschar(index, 1)
            jungschar.name = self._default_jungschar_name(index)
            jungschar.groups[0].name = self._default_group_name(0)
            self.jungscharen.append(jungschar)

        self.game_names = [self._default_game_name(0)]
        self.n_rounds = 1

        self._set_spinbox_value(self.ui.spinBox_n_jungscharen, 2)
        self._set_spinbox_value(self.ui.spinBox_n_games, 1)
        self._set_spinbox_value(self.ui.spinBox_n_rounds, 1)
        self.search_time_input.setValue(60)

        self._update_team_names()
        self._sync_editors()
        self._show_page(0)
        self.refresh_summary()

    def cancel_generation(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.cancel_button.setEnabled(False)

    def generate(self) -> None:
        validation_error = self.validate_inputs()
        if validation_error:
            QMessageBox.warning(self, "Eingaben prüfen", validation_error)
            return

        self.ui.pushButton_generate.setEnabled(False)
        self.reset_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.ui.progressBar_generate.setValue(0)
        self.generation_status.setText(
            "Generierung läuft. Die Anzeige hilft bei der Entscheidung, "
            "ob sich weiteres Warten lohnt."
        )
        self.worker_thread = QThread(self)
        self.worker = ScheduleWorker(
            self.jungscharen,
            self.n_rounds,
            list(self.game_names),
            time_limit_seconds=self.search_time_input.value(),
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.ui.progressBar_generate.setValue)
        self.worker.status.connect(self.generation_status.setText)
        self.worker.completed.connect(self.generation_finished)
        self.worker.failed.connect(self.generation_failed)
        self.worker.completed.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.generation_cleanup)
        self.worker_thread.start()

    def generation_cleanup(self) -> None:
        if self.worker is not None:
            self.worker.deleteLater()
        if self.worker_thread is not None:
            self.worker_thread.deleteLater()
        self.worker = None
        self.worker_thread = None
        self.ui.pushButton_generate.setEnabled(True)
        self.reset_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def generation_failed(self, message: str) -> None:
        if message != "Generation cancelled":
            QMessageBox.critical(
                self,
                "Fehler",
                f"Der Spielplan konnte nicht erstellt werden: {message}",
            )
            self.generation_status.setText("Generierung fehlgeschlagen.")

    def generation_finished(self, results: ScheduleResult) -> None:
        schedule, game_counts, team_matchups, game_team_counts, team_game_totals = results
        self.generation_status.setText("Generierung abgeschlossen. Wählen Sie einen Speicherort.")
        if DEBUG:
            file_path = "schedule.xlsx"
        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Spielplan speichern", "schedule.xlsx", "Excel-Dateien (*.xlsx)"
            )
            if not file_path:
                return

        try:
            self._write_schedule_workbook(
                Path(file_path),
                schedule,
                game_counts,
                team_matchups,
                game_team_counts,
                team_game_totals,
            )
            QMessageBox.information(
                self,
                "Spielplan gespeichert",
                f"Die Datei wurde gespeichert unter:\n{file_path}",
            )
            self.generation_status.setText(f"Gespeichert: {file_path}")
        except Exception as error:
            QMessageBox.critical(
                self,
                "Fehler",
                f"Die Excel-Datei konnte nicht gespeichert werden: {error}",
            )

    @staticmethod
    def _write_schedule_workbook(
        file_path: Path,
        schedule: pd.DataFrame,
        game_counts: pd.DataFrame,
        team_matchups: pd.DataFrame,
        game_team_counts: pd.DataFrame,
        team_game_totals: pd.DataFrame,
    ) -> None:
        with pd.ExcelWriter(file_path) as writer:
            schedule.to_excel(writer, sheet_name="Schedule")
            game_counts.to_excel(writer, sheet_name="Game Counts", index=False)
            team_matchups.to_excel(writer, sheet_name="Team Matchups", index=False)
            game_team_counts.to_excel(writer, sheet_name="Game Team Counts", index=False)
            team_game_totals.to_excel(writer, sheet_name="Team Game Totals", index=False)
