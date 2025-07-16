from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMessageBox

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
        

        # init variables
        self.jungscharen: list[Jungschar] = [Jungschar(0, 1)]
        self.n_jungscharen_changed(self.ui.spinBox_n_jungscharen.value())
        self.game_names = []
        self.n_rounds =  self.ui.spinBox_n_rounds.value()


        # disable group naming function
        self.ui.tableWidget_group_names_jungscharen.setEnabled(False)



        # show Main Window
        self.show()

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
        with pd.ExcelWriter('schedule.xlsx') as writer:
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
