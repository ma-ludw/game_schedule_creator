import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from multiprocessing import Manager
from typing import Callable, Literal, NamedTuple, TypedDict, overload

import numpy as np
import pandas as pd

from Jungschar import Jungschar
from gpu_schedule_search import OpenCLScheduleSearch, OpenCLUnavailableError


DEFAULT_SEARCH_ATTEMPTS = 10_000_000
SEARCH_BATCHES_PER_WORKER = 2
PROGRESS_REPORT_INTERVAL = 1_000


class TeamInfo(TypedDict):
    team_number: int
    jungschar_name: str
    jungschar_id: int
    group_name: str
    group_id: int


class ScheduleResult(NamedTuple):
    schedule: pd.DataFrame
    game_counts: pd.DataFrame
    team_matchups: pd.DataFrame
    game_team_counts: pd.DataFrame
    team_game_totals: pd.DataFrame


Matchup = tuple[int, int]
ScheduledGame = tuple[int, int, int]
Schedule = list[list[ScheduledGame]]
DetailedMetrics = tuple[float, dict[Matchup, int], dict[int, int], np.ndarray]


def _search_schedule_batch(payload):
    """Search one independent batch in a worker process."""
    (
        jungscharen,
        n_rounds,
        n_games,
        game_names,
        attempts,
        deadline,
        seed,
        batch_id,
        progress_queue,
    ) = payload
    random.seed(seed)
    generator = ScheduleGenerator(
        jungscharen,
        n_rounds,
        n_games,
        game_names,
        progress_update_callback=None,
    )

    def report_progress(completed, best_cost):
        progress_queue.put((batch_id, completed, best_cost))

    return generator._find_best_schedule(
        attempts,
        deadline=deadline,
        progress_callback=report_progress,
    ) + (generator.total_tries,)


class ScheduleGenerator:

    @staticmethod
    def _merge_batch_progress(
        batch_progress: dict[int, tuple[int, float]],
        batch_id: int,
        completed_attempts: int,
        cost: float,
    ) -> None:
        previous_attempts, previous_cost = batch_progress.get(
            batch_id,
            (0, cost),
        )
        batch_progress[batch_id] = (
            max(previous_attempts, completed_attempts),
            min(previous_cost, cost),
        )

    def __init__(
        self,
        jungscharen: list[Jungschar],
        n_rounds: int,
        n_games: int,
        games_names: list[str],
        progress_update_callback: Callable[[int], None] | None = None,
        cancellation_callback: Callable[[], bool] | None = None,
        status_update_callback: Callable[[str], None] | None = None,
        parallel_workers: int | None = None,
        time_limit_seconds: int | None = None,
        use_gpu: bool = True,
    ) -> None:
        if time_limit_seconds is not None and time_limit_seconds < 1:
            raise ValueError("time_limit_seconds must be at least 1")
        self.jungscharen = jungscharen
        self.n_games = n_games
        self.game_names = games_names
        self.n_rounds = n_rounds
        self.progress_update_callback = progress_update_callback
        self.cancellation_callback = cancellation_callback
        self.status_update_callback = status_update_callback
        self.time_limit_seconds = time_limit_seconds
        self.use_gpu = use_gpu
        self.backend_name = "CPU"
        self._search_started_at: float | None = None
        self.parallel_workers = max(
            1,
            parallel_workers if parallel_workers is not None else (os.cpu_count() or 1),
        )
        self.n_teams = sum(js.n_groups for js in self.jungscharen)
        self.team_names, self.jungschar_teams = self._build_team_roster()
        self.jungschar_teams_lists = list(self.jungschar_teams.values())
        self.all_possible_pairs = self._build_possible_matchups()
        self.n_tries = DEFAULT_SEARCH_ATTEMPTS
        self.total_tries = 0
        self.team_lookup = {team["team_number"]: team for team in self.team_names}

    def _build_team_roster(self) -> tuple[list[TeamInfo], dict[str, list[int]]]:
        team_infos: list[TeamInfo] = []
        teams_by_jungschar: dict[str, list[int]] = {}
        team_number = 0

        for jungschar in self.jungscharen:
            teams_for_jungschar = []
            for group in jungschar.groups:
                team_infos.append({
                    "team_number": team_number,
                    "jungschar_name": jungschar.name,
                    "jungschar_id": jungschar.id,
                    "group_name": group.name,
                    "group_id": group.id,
                })
                teams_for_jungschar.append(team_number)
                team_number += 1
            teams_by_jungschar[jungschar.name] = teams_for_jungschar
        return team_infos, teams_by_jungschar

    def _build_possible_matchups(self) -> list[Matchup]:
        return [
            (team_from_first, team_from_second)
            for first_index, first_teams in enumerate(self.jungschar_teams_lists)
            for second_teams in self.jungschar_teams_lists[first_index + 1 :]
            for team_from_first in first_teams
            for team_from_second in second_teams
        ]

    def get_teams_by_jungschar(self, jungschar_name: str) -> list[int]:
        """Get all team numbers belonging to a specific Jungschar"""
        return self.jungschar_teams.get(jungschar_name, [])
    
    def get_jungschar_by_team(self, team_number: int) -> str:
        """Get the Jungschar name for a specific team number"""
        team_info = self.team_lookup.get(team_number)
        return team_info["jungschar_name"] if team_info else "Unknown"
    
    def print_team_assignments(self):
        """Print a clear overview of team assignments"""
        print("Team Assignments:")
        print("-" * 50)
        for jungschar_name, team_numbers in self.jungschar_teams.items():
            print(f"Jungschar {jungschar_name}:")
            for team_num in team_numbers:
                team_info = next(team for team in self.team_names if team["team_number"] == team_num)
                print(f"  Team {team_num}: {team_info['group_name']}")
            print()

    def _format_team_name(self, team_info: TeamInfo | None) -> str:
        """Return the export name for a team, omitting the group suffix for single groups."""
        if team_info is None:
            return "Unknown"
        if len(self.jungschar_teams.get(team_info["jungschar_name"], [])) == 1:
            return team_info["jungschar_name"]
        return f"{team_info['jungschar_name']}.{team_info['group_name']}"


    def generate_schedule(self) -> ScheduleResult:
        """Search for a balanced schedule and convert it to report tables."""
        best_schedule, best_cost = self._find_best_parallel()
        _, team_matchups, game_counts, game_team_counts = self.check_schedule(
            best_schedule,
            include_details=True,
        )

        if self.progress_update_callback:
            self.progress_update_callback(100)
        if self.status_update_callback:
            self.status_update_callback(
                f"Generierung abgeschlossen ({self.backend_name}) · "
                f"Qualitätswert: {best_cost:.4f} "
                f"(je niedriger, desto besser)"
            )

        print("Team matchups:")
        for teams, count in team_matchups.items():
            print(f"  Teams {teams[0]} and {teams[1]}: {count} times")

        print("Game counts:")
        for game, count in game_counts.items():
            print(f"  Game {game}: {count} times")

        print("Game team counts:")
        for game_number, counts in enumerate(game_team_counts, start=1):
            print(f"  Game {game_number}: {dict(enumerate(counts, start=1))}")

        print(f"Total tries: {self.total_tries:,}")

        return ScheduleResult(
            self.convert_schedule_to_names(best_schedule),
            self.convert_game_counts_to_names(game_counts),
            self.convert_team_matchups_to_names(team_matchups),
            self.convert_game_team_counts_to_names(game_team_counts),
            self.convert_team_game_totals_to_names(game_team_counts),
        )

    def _find_best_schedule(
        self,
        attempts: int | None,
        deadline: float | None = None,
        progress_callback: Callable[[int, float], None] | None = None,
    ) -> tuple[Schedule, float]:
        if attempts is None and deadline is None:
            raise ValueError("A deadline is required when attempts is unlimited")
        best_schedule = self.generate_random_schedule()
        best_cost = self.check_schedule(best_schedule, include_details=False)
        completed = 1
        while attempts is None or completed < attempts:
            if deadline is not None and time.monotonic() >= deadline:
                break
            candidate = self.generate_random_schedule()
            cost = self.check_schedule(candidate, include_details=False)
            if cost < best_cost:
                best_schedule = candidate
                best_cost = cost
                if deadline is None and cost < 0.01:
                    break
            completed += 1
            if progress_callback and (
                completed % PROGRESS_REPORT_INTERVAL == 0
                or completed == attempts
            ):
                progress_callback(completed, best_cost)
        if progress_callback and (completed == 1 or deadline is not None):
            progress_callback(completed, best_cost)
        self.total_tries = completed
        return best_schedule, best_cost

    def _find_best_parallel(self) -> tuple[Schedule, float]:
        time_limit_seconds = self.time_limit_seconds
        timed_search = time_limit_seconds is not None
        if self.use_gpu:
            try:
                if self.status_update_callback:
                    self.status_update_callback("OpenCL-GPU wird initialisiert …")
                gpu_search = OpenCLScheduleSearch(
                    self.all_possible_pairs,
                    self.n_teams,
                    self.n_games,
                    self.n_rounds,
                )
            except OpenCLUnavailableError as error:
                self.backend_name = "CPU (OpenCL nicht verfügbar)"
                if self.status_update_callback:
                    self.status_update_callback(
                        f"{error} Die Generierung wird auf der CPU fortgesetzt."
                    )
            else:
                self.backend_name = f"OpenCL-GPU: {gpu_search.device.name.strip()}"
                self._search_started_at = time.monotonic()
                deadline = (
                    self._search_started_at + time_limit_seconds
                    if timed_search
                    else None
                )
                if self.status_update_callback:
                    self.status_update_callback(
                        f"Suche auf {self.backend_name} gestartet."
                    )
                result = gpu_search.search(
                    deadline=deadline,
                    max_candidates=None if timed_search else self.n_tries,
                    cancellation_requested=(
                        self.cancellation_callback or (lambda: False)
                    ),
                    progress_callback=self._notify_progress,
                )
                self.total_tries = gpu_search.completed_candidates
                return result

        worker_count = (
            self.parallel_workers
            if timed_search
            else min(self.parallel_workers, max(1, self.n_tries))
        )
        batch_count = (
            worker_count
            if timed_search
            else worker_count * SEARCH_BATCHES_PER_WORKER
        )
        deadline = None
        if timed_search:
            self._search_started_at = time.monotonic()
            deadline = self._search_started_at + time_limit_seconds
            batch_attempts = [None] * batch_count
        else:
            base_attempts = self.n_tries // batch_count
            remainder = self.n_tries % batch_count
            batch_attempts = [
                base_attempts + (1 if batch_index < remainder else 0)
                for batch_index in range(batch_count)
            ]
        payloads = []
        for attempts in batch_attempts:
            if attempts is None or attempts > 0:
                payloads.append((
                    self.jungscharen,
                    self.n_rounds,
                    self.n_games,
                    self.game_names,
                    attempts,
                    deadline,
                    random.randrange(2**32),
                ))

        if worker_count == 1:
            if timed_search:
                return self._find_best_schedule(
                    None,
                    deadline=deadline,
                    progress_callback=lambda completed, cost: self._notify_progress(
                        completed,
                        cost,
                    ),
                )
            return self._find_best_schedule(self.n_tries)

        best_result = None
        completed_attempts = 0
        manager = Manager()
        progress_queue = manager.Queue()
        try:
            with ProcessPoolExecutor(max_workers=worker_count) as executor:
                future_attempts = {}
                future_batches = {}
                for batch_id, payload in enumerate(payloads):
                    future = executor.submit(
                        _search_schedule_batch,
                        (*payload, batch_id, progress_queue),
                    )
                    future_attempts[future] = payload[4]
                    future_batches[future] = batch_id

                pending = set(future_attempts)
                batch_progress = {}
                while pending:
                    if self.cancellation_callback and self.cancellation_callback():
                        for future in pending:
                            future.cancel()
                        break

                    finished, pending = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
                    while not progress_queue.empty():
                        batch_id, completed, cost = progress_queue.get()
                        self._merge_batch_progress(
                            batch_progress,
                            batch_id,
                            completed,
                            cost,
                        )
                        completed_attempts = sum(value[0] for value in batch_progress.values())
                        best_cost = min(
                            (value[1] for value in batch_progress.values()),
                            default=None,
                        )
                        self._notify_progress(completed_attempts, best_cost)

                    for future in finished:
                        schedule, cost, attempts = future.result()
                        batch_id = future_batches[future]
                        self._merge_batch_progress(
                            batch_progress,
                            batch_id,
                            attempts,
                            cost,
                        )
                        completed_attempts = sum(value[0] for value in batch_progress.values())
                        self.total_tries = completed_attempts
                        if best_result is None or cost < best_result[1]:
                            best_result = (schedule, cost)
                        best_cost = min(
                            value[1] for value in batch_progress.values()
                        )
                        self._notify_progress(completed_attempts, best_cost)
        finally:
            manager.shutdown()

        if best_result is None:
            return self._find_best_schedule(1)
        return best_result

    def _notify_progress(self, completed_attempts: int, best_cost: float | None) -> None:
        if self.progress_update_callback:
            if self.time_limit_seconds is not None and self._search_started_at is not None:
                elapsed = time.monotonic() - self._search_started_at
                percentage = min(
                    99,
                    int(elapsed / self.time_limit_seconds * 100),
                )
            else:
                percentage = int(completed_attempts / self.n_tries * 100)
            self.progress_update_callback(percentage)
        if self.status_update_callback and best_cost is not None:
            if self.time_limit_seconds is not None and self._search_started_at is not None:
                elapsed = time.monotonic() - self._search_started_at
                status = (
                    f"Suchzeit: {elapsed:.1f} / {self.time_limit_seconds} s · "
                    f"Qualitätswert: {best_cost:.4f} (je niedriger, desto besser)"
                )
            else:
                status = (
                    f"{completed_attempts:,} von {self.n_tries:,} Versuchen abgeschlossen · "
                    f"Qualitätswert: {best_cost:.4f} (je niedriger, desto besser)"
                )
            self.status_update_callback(status)

    def convert_schedule_to_names(self, schedule: Schedule) -> pd.DataFrame:
        """Convert scheduled team IDs into a round-by-game table."""
        rows = []
        for round_games in schedule:
            row = {}
            for game_number, first_team, second_team in round_games:
                first_name = self._format_team_name(self.team_lookup.get(first_team))
                second_name = self._format_team_name(self.team_lookup.get(second_team))
                row[self.game_names[game_number]] = f"{first_name} vs {second_name}"
            rows.append(row)
        return pd.DataFrame(rows, columns=self.game_names).fillna("")
    
    def convert_team_matchups_to_names(
        self,
        team_matchups: dict[Matchup, int],
    ) -> pd.DataFrame:
        rows = []
        for (team1, team2), count in team_matchups.items():
            first_name = self._format_team_name(self.team_lookup.get(team1))
            second_name = self._format_team_name(self.team_lookup.get(team2))
            rows.append({"Team 1": first_name, "Team 2": second_name, "Count": count})
        return pd.DataFrame(rows, columns=["Team 1", "Team 2", "Count"])
    
    def convert_game_counts_to_names(self, game_counts: dict[int, int]) -> pd.DataFrame:
        rows = []
        for game, count in game_counts.items():
            rows.append({"Game": self.game_names[game], "Count": count})
        return pd.DataFrame(rows, columns=["Game", "Count"])
    
    def convert_game_team_counts_to_names(
        self,
        game_team_counts: np.ndarray,
    ) -> pd.DataFrame:
        team_names = [
            self._format_team_name(team_info)
            for team_info in self.team_names
        ]
        game_names = self.game_names[: game_team_counts.shape[0]]
        game_names.extend(
            f"Game {index + 1}"
            for index in range(len(game_names), game_team_counts.shape[0])
        )
        result = pd.DataFrame(game_team_counts, columns=team_names)
        result.insert(0, "Game", game_names)
        return result

    def convert_team_game_totals_to_names(
        self,
        game_team_counts: np.ndarray,
    ) -> pd.DataFrame:
        """Return the total number of games played by each team."""
        team_names = [
            self._format_team_name(team) if team else f"Team {idx}"
            for idx, team in enumerate(self.team_names)
        ]
        totals = np.sum(game_team_counts, axis=0).astype(int)
        return pd.DataFrame({
            "Team": team_names,
            "Games played": totals,
        })


    def generate_random_schedule(self) -> Schedule:
        """Create one randomized schedule using the current matchup rotations."""
        schedule = self.generate_round_robin_schedule()

        game_schedule = []
        for round_matchups in schedule:
            game_numbers = list(range(self.n_games))
            random.shuffle(game_numbers)
            round_games = [
                (game_numbers.pop(), first_team, second_team)
                for first_team, second_team in round_matchups
            ]
            game_schedule.append(sorted(round_games))
        return game_schedule

    def generate_round_robin_schedule(self) -> list[list[Matchup]]:
        """Build rounds from distinct inter-Jungschar matchups."""
        pair_count = len(self.all_possible_pairs)
        if pair_count == 0:
            return [[] for _ in range(self.n_rounds)]
        pair_start = random.randrange(pair_count)
        pair_step = -1 if random.getrandbits(1) else 1
        max_matchups_per_round = min(self.n_games, self.n_teams // 2)
        schedule: list[list[Matchup]] = []
        matchups_used = set()

        for _ in range(self.n_rounds):
            round_matchups: list[Matchup] = []
            teams_used_this_round = set()
            self._add_unplayed_matchups(
                round_matchups,
                teams_used_this_round,
                matchups_used,
                pair_start,
                pair_step,
                max_matchups_per_round,
                only_unplayed=True,
            )
            self._add_unplayed_matchups(
                round_matchups,
                teams_used_this_round,
                matchups_used,
                pair_start,
                pair_step,
                max_matchups_per_round,
                only_unplayed=False,
            )
            schedule.append(round_matchups)
            if len(matchups_used) >= pair_count:
                matchups_used.clear()
        return schedule

    def _add_unplayed_matchups(
        self,
        round_matchups: list[Matchup],
        teams_used_this_round: set[int],
        matchups_used: set[Matchup],
        pair_start: int,
        pair_step: int,
        max_matchups: int,
        *,
        only_unplayed: bool,
    ) -> None:
        pair_count = len(self.all_possible_pairs)
        if len(round_matchups) >= max_matchups:
            return
        for offset in range(pair_count):
            pair_index = (pair_start + pair_step * offset) % pair_count
            matchup = self.all_possible_pairs[pair_index]
            first_team, second_team = matchup
            teams_are_available = (
                first_team not in teams_used_this_round
                and second_team not in teams_used_this_round
            )
            if not teams_are_available:
                continue
            if only_unplayed and matchup in matchups_used:
                continue

            round_matchups.append(matchup)
            teams_used_this_round.update(matchup)
            if only_unplayed:
                matchups_used.add(matchup)
            if len(round_matchups) >= max_matchups:
                return

    @overload
    def check_schedule(
        self,
        schedule: Schedule,
        include_details: Literal[False],
    ) -> float: ...

    @overload
    def check_schedule(
        self,
        schedule: Schedule,
        include_details: Literal[True] = True,
    ) -> DetailedMetrics: ...

    def check_schedule(
        self,
        schedule: Schedule,
        include_details: bool = True,
    ) -> float | DetailedMetrics:
        """Measure schedule balance and optionally return all matchup counts."""
        team_matchup_counts = np.zeros((self.n_teams, self.n_teams), dtype=np.int32)
        game_counts_array = np.zeros(self.n_games, dtype=np.int32)
        game_team_counts = np.zeros((self.n_games, self.n_teams))

        for round_games in schedule:
            for game_number, first_team, second_team in round_games:
                game_counts_array[game_number] += 1
                game_team_counts[game_number, first_team] += 1
                game_team_counts[game_number, second_team] += 1
                first_team, second_team = sorted((first_team, second_team))
                team_matchup_counts[first_team, second_team] += 1

        rounds_per_team = np.sum(game_team_counts, axis=0)
        game_count_variance = np.var(game_counts_array)
        team_round_variance = np.var(rounds_per_team)
        matchup_variance = np.var(
            team_matchup_counts[np.triu_indices(self.n_teams, k=1)]
        )
        game_team_variance = np.var(game_team_counts)
        cost_value = float(
            game_count_variance
            + game_team_variance * 10
            + team_round_variance * 10
            + matchup_variance
        )
        if not include_details:
            return cost_value

        team_matchups = {
            (team1, team2): int(team_matchup_counts[team1, team2])
            for team1 in range(self.n_teams)
            for team2 in range(team1 + 1, self.n_teams)
        }
        game_counts = {
            game: int(game_counts_array[game])
            for game in range(self.n_games)
        }
        return cost_value, team_matchups, game_counts, game_team_counts
        
