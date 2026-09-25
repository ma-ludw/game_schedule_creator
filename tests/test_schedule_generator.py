from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from application_window import Window
from Jungschar import Jungschar
from ScheduleGenerator import ScheduleGenerator


class ScheduleGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        first = Jungschar(0, 2)
        second = Jungschar(1, 2)
        first.name = "Nord"
        second.name = "Sued"
        first.groups[0].name = "Nord A"
        first.groups[1].name = "Nord B"
        second.groups[0].name = "Sued A"
        second.groups[1].name = "Sued B"

        self.generator = ScheduleGenerator(
            [first, second],
            n_rounds=3,
            n_games=2,
            games_names=["Fangen", "Staffel"],
            parallel_workers=1,
        )
        self.generator.n_tries = 8

    def test_matchups_only_pair_teams_from_different_jungscharen(self) -> None:
        self.assertEqual(
            self.generator.all_possible_pairs,
            [(0, 2), (0, 3), (1, 2), (1, 3)],
        )

    def test_each_team_appears_at_most_once_per_round(self) -> None:
        for round_games in self.generator.generate_random_schedule():
            teams_in_round = [
                team_number
                for _, first_team, second_team in round_games
                for team_number in (first_team, second_team)
            ]
            self.assertEqual(len(teams_in_round), len(set(teams_in_round)))

    def test_schedule_generation_returns_all_report_tables(self) -> None:
        results = self.generator.generate_schedule()

        self.assertEqual(len(results), 5)
        self.assertEqual(list(results.schedule.columns), ["Fangen", "Staffel"])
        self.assertEqual(results.schedule.shape[0], 3)
        self.assertEqual(list(results.game_counts.columns), ["Game", "Count"])
        self.assertEqual(
            list(results.team_matchups.columns),
            ["Team 1", "Team 2", "Count"],
        )
        self.assertEqual(results.game_team_counts.shape, (2, 5))
        self.assertEqual(
            list(results.team_game_totals.columns),
            ["Team", "Games played"],
        )

    def test_excel_export_keeps_the_expected_sheet_names(self) -> None:
        results = self.generator.generate_schedule()

        with TemporaryDirectory() as directory:
            workbook_path = Path(directory) / "schedule.xlsx"
            Window._write_schedule_workbook(workbook_path, *results)
            with pd.ExcelFile(workbook_path) as workbook:
                self.assertEqual(
                    workbook.sheet_names,
                    [
                        "Schedule",
                        "Game Counts",
                        "Team Matchups",
                        "Game Team Counts",
                        "Team Game Totals",
                    ],
                )


if __name__ == "__main__":
    unittest.main()
