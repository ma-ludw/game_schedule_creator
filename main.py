from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMessageBox, QFileDialog, QHeaderView

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
        self.ui.tableWidget_n_groups.itemChanged.connect(self.group_names_numbers_changed)
        self.ui.tableWidget_group_names_jungscharen.itemChanged.connect(self.group_name_table_changed)
        self.ui.spinBox_n_games.valueChanged.connect(self.n_games_changed)
        self.ui.tableWidget_game_names.itemChanged.connect(self.game_names_changed)
        self.ui.spinBox_n_rounds.valueChanged.connect(self.n_rounds_changed)

        self.ui.tableWidget_n_groups.setColumnCount(2)
        self.ui.tableWidget_n_groups.setHorizontalHeaderLabels(["Jungschar Name", "Anzahl Gruppen"])
        self.ui.tableWidget_group_names_jungscharen.setColumnCount(2)
        self.ui.tableWidget_group_names_jungscharen.setHorizontalHeaderLabels(["Jungschar Name", "Gruppen Name"])
        self.ui.tableWidget_game_names.setColumnCount(1)
        self.ui.tableWidget_game_names.setHorizontalHeaderLabels(["Spielname"])

        self._configure_table(self.ui.tableWidget_n_groups)
        self._configure_table(self.ui.tableWidget_group_names_jungscharen)
        self._configure_table(self.ui.tableWidget_game_names)

        # init variables
        self.jungscharen: list[Jungschar] = [Jungschar(0, 1)]
        self.n_jungscharen_changed(self.ui.spinBox_n_jungscharen.value())
        self.game_names = []
        self.n_rounds = self.ui.spinBox_n_rounds.value()

        # disable group naming function
        self.ui.tableWidget_group_names_jungscharen.setEnabled(False)

        self.ui.pushButton_generate.setDefault(True)
        self.ui.pushButton_generate.setCursor(Qt.PointingHandCursor)

        # show Main Window
        self.show()

    def _apply_user_friendly_style(self):
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f4f7fb;
                color: #1f2937;
            }
            QWidget {
                color: #1f2937;
            }
            QLabel {
                font-size: 13px;
                font-weight: 600;
                color: #334155;
                padding: 4px 0px;
            }
            QSpinBox, QTableWidget {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 6px 8px;
                selection-background-color: #bfdbfe;
                selection-color: #0f172a;
            }
            QSpinBox:focus, QTableWidget:focus {
                border: 1px solid #60a5fa;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #1d4ed8);
                border: none;
                border-radius: 10px;
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
                min-height: 40px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #1e40af);
            }
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background: #e2e8f0;
                text-align: center;
                color: #0f172a;
                font-weight: 600;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
                border-radius: 7px;
            }
            QHeaderView::section {
                background: #e2e8f0;
                color: #0f172a;
                font-weight: 700;
                padding: 8px 10px;
                border: 1px solid #cbd5e1;
            }
            QTableWidget {
                gridline-color: #dbeafe;
                alternate-background-color: #f8fafc;
            }
            QTableWidget::item {
                padding: 8px 6px;
            }
            QTableWidget::item:selected {
                background: #dbeafe;
                color: #0f172a;
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


    def n_jungscharen_changed(self, n_jungscharen: int):
        self.ui.tableWidget_n_groups.setRowCount(n_jungscharen)
        while len(self.jungscharen) < n_jungscharen:
            self.jungscharen.append(Jungschar(len(self.jungscharen), 1))
        while len(self.jungscharen) > n_jungscharen:
            self.jungscharen.pop()

        # set up Group naming table
        self.set_upt_group_naming_table()

    def group_names_numbers_changed(self, item: QTableWidgetItem):
        row = item.row()
        if item.column() == 0:
            self.jungscharen[row].name = item.text()
        else:
            self.jungscharen[row].change_n_groups(int(item.text()))
        self.set_upt_group_naming_table()

    def set_upt_group_naming_table(self):
        n_groups = 0
        for js in self.jungscharen:
            n_groups = n_groups + js.n_groups
        
        self.ui.tableWidget_group_names_jungscharen.setRowCount(n_groups)
        
        row = 0
        for js in self.jungscharen:
            for g in js.groups:
                item = QTableWidgetItem(str(js.name))
                self.ui.tableWidget_group_names_jungscharen.setItem(row, 0, item)
                item = QTableWidgetItem(str(g.name))
                self.ui.tableWidget_group_names_jungscharen.setItem(row, 1, item)
                row = row + 1
    
    def n_games_changed(self, value: int):
        self.ui.tableWidget_game_names.setRowCount(value)
        while value > len(self.game_names):
            self.game_names.append(len(self.game_names))
        while value < len(self.game_names):
            self.game_names.pop()

            

    def game_names_changed(self, item: QTableWidgetItem):
        self.game_names[item.row()] = item.text()

    def group_name_table_changed(self, item: QTableWidgetItem):
        pass

    def n_rounds_changed(self, value: int):
        self.n_rounds = value
 


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

    window = Window()

    # start the app
    sys.exit(App.exec())



if __name__ == "__main__":
    main()
