from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import math
import time
import unittest

import pandas as pd

from application_window import Window
from Jungschar import Jungschar
from ScheduleGenerator import ScheduleGenerator
from gpu_schedule_search import OpenCLScheduleSearch, OpenCLUnavailableError


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

    def test_late_batch_progress_cannot_increase_best_cost_or_attempts(self) -> None:
        batch_progress = {0: (500, 2.5)}

        ScheduleGenerator._merge_batch_progress(batch_progress, 0, 250, 3.0)

        self.assertEqual(batch_progress[0], (500, 2.5))

    def test_time_limited_search_runs_until_deadline(self) -> None:
        started_at = time.monotonic()
        self.generator._find_best_schedule(
            None,
            deadline=started_at + 0.05,
        )
        elapsed = time.monotonic() - started_at

        self.assertGreaterEqual(elapsed, 0.05)
        self.assertLess(elapsed, 1.0)

    def test_cpu_search_can_be_selected_explicitly(self) -> None:
        generator = ScheduleGenerator(
            self.generator.jungscharen,
            n_rounds=3,
            n_games=2,
            games_names=["Fangen", "Staffel"],
            parallel_workers=1,
            use_gpu=False,
        )
        generator.n_tries = 8

        schedule, cost = generator._find_best_parallel()

        self.assertEqual(generator.backend_name, "CPU")
        self.assertTrue(math.isfinite(cost))
        self.assertEqual(len(schedule), 3)

    def test_schedule_generation_prints_actual_total_tries(self) -> None:
        generator = ScheduleGenerator(
            self.generator.jungscharen,
            n_rounds=3,
            n_games=2,
            games_names=["Fangen", "Staffel"],
            parallel_workers=1,
            use_gpu=False,
        )
        generator.n_tries = 8
        output = StringIO()

        with redirect_stdout(output):
            generator.generate_schedule()

        self.assertGreaterEqual(generator.total_tries, 1)
        self.assertIn(
            f"Total tries: {generator.total_tries:,}",
            output.getvalue(),
        )

    def test_opencl_search_generates_valid_schedule_when_gpu_is_available(self) -> None:
        try:
            gpu_search = OpenCLScheduleSearch(
                self.generator.all_possible_pairs,
                self.generator.n_teams,
                self.generator.n_games,
                self.generator.n_rounds,
            )
        except OpenCLUnavailableError as error:
            self.skipTest(str(error))

        progress_reports = []
        schedule, cost = gpu_search.search(
            deadline=time.monotonic() + 5,
            max_candidates=16,
            cancellation_requested=lambda: False,
            progress_callback=lambda completed, best_cost: progress_reports.append(
                (completed, best_cost)
            ),
        )

        self.assertTrue(math.isfinite(cost))
        self.assertEqual(progress_reports[-1][0], 16)
        self.assertAlmostEqual(
            cost,
            self.generator.check_schedule(schedule, include_details=False),
            places=4,
        )
        self.assertEqual(len(schedule), self.generator.n_rounds)
        for round_games in schedule:
            teams = [
                team
                for _, first_team, second_team in round_games
                for team in (first_team, second_team)
            ]
            self.assertEqual(len(teams), len(set(teams)))
            for _, first_team, second_team in round_games:
                self.assertNotEqual(
                    self.generator.get_jungschar_by_team(first_team),
                    self.generator.get_jungschar_by_team(second_team),
                )

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
