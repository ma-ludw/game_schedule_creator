from Jungschar import Jungschar
import pandas as pd
import numpy as np
import random
import os
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from multiprocessing import Manager

from typing import Callable


def _search_schedule_batch(payload):
    """Search one independent batch in a worker process."""
    jungscharen, n_rounds, n_games, game_names, attempts, seed, batch_id, progress_queue = payload
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

    return generator._find_best_schedule(attempts, progress_callback=report_progress)


class ScheduleGenerator():

    def __init__(
        self,
        jungscharen: list[Jungschar],
        n_rounds: int,
        n_games: int,
        games_names: list[str],
        progress_update_callback: Callable,
        cancellation_callback: Callable[[], bool] | None = None,
        status_update_callback: Callable[[str], None] | None = None,
        parallel_workers: int | None = None,
    ):
        self.jungscharen = jungscharen # List of Jungschar objects
        self.n_games = n_games # Number of games
        self.game_names = games_names # List of game names
        self.n_rounds = n_rounds # Number of rounds

        self.progress_update_callback = progress_update_callback
        self.cancellation_callback = cancellation_callback
        self.status_update_callback = status_update_callback
        self.parallel_workers = max(
            1,
            parallel_workers if parallel_workers is not None else (os.cpu_count() or 1),
        )

        self.n_teams = sum([js.n_groups for js in self.jungscharen]) # Total number of teams across all Jungscharen
        
        # Create teams with clear assignment to Jungscharen
        self.team_names = [] # List of dictionaries with team information
        self.jungschar_teams = {}  # Maps jungschar_name -> list of team_numbers
        team_counter = 0
        
        # Create a team for each group in each Jungschar
        # Each team is represented as a dictionary with team_number, jungschar_name, jungschar_id, group_name, and group_id
        # This allows for easy access to team information by team number or Jungschar name
        for js in self.jungscharen:
            jungschar_team_list = []
            for gr in js.groups:
                team_info = {
                    "team_number": team_counter,
                    "jungschar_name": js.name,
                    "jungschar_id": js.id,
                    "group_name": gr.name,
                    "group_id": gr.id
                }
                self.team_names.append(team_info)
                jungschar_team_list.append(team_counter)
                team_counter += 1
            
            self.jungschar_teams[js.name] = jungschar_team_list

        # Create a list of lists, where each sublist contains the team numbers for a Jungschar
        self.jungschar_teams_lists = list(self.jungschar_teams.values())

        # Create all possible inter-Jungschar pairs
        self.all_possible_pairs = []
        for i, jungschar1_teams in enumerate(self.jungschar_teams_lists):
            for j, jungschar2_teams in enumerate(self.jungschar_teams_lists):
                if i < j:  # Only consider each pair of Jungscharen once
                    for team1 in jungschar1_teams:
                        for team2 in jungschar2_teams:
                            self.all_possible_pairs.append((team1, team2))

        self.n_tries = 1000000
        
        # Create team lookup cache for faster access
        self.team_lookup = {team["team_number"]: team for team in self.team_names}

    def get_teams_by_jungschar(self, jungschar_name: str) -> list:
        """Get all team numbers belonging to a specific Jungschar"""
        return self.jungschar_teams.get(jungschar_name, [])
    
    def get_jungschar_by_team(self, team_number: int) -> str:
        """Get the Jungschar name for a specific team number"""
        team_info = next((team for team in self.team_names if team["team_number"] == team_number), None)
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

    def _format_team_name(self, team_info: dict | None) -> str:
        """Return the export name for a team, omitting the group suffix for single groups."""
        if team_info is None:
            return "Unknown"
        if len(self.jungschar_teams.get(team_info["jungschar_name"], [])) == 1:
            return team_info["jungschar_name"]
        return f"{team_info['jungschar_name']}.{team_info['group_name']}"


    def generate_schedule(self) -> tuple:
        """Generate a schedule based on the provided parameters"""

        best_schedule, best_cost = self._find_best_parallel()
        _, best_team_matchups, best_game_counts, best_game_team_counts = self.check_schedule(
            best_schedule,
            include_details=True,
        )

        self.progress_update_callback(100)
        if self.status_update_callback:
            self.status_update_callback(
                f"Parallele Generierung abgeschlossen · Qualitätswert: {best_cost:.4f} "
                f"(je niedriger, desto besser)"
            )

        print("Team matchups:")
        for teams, count in best_team_matchups.items():
            print(f"  Teams {teams[0]} and {teams[1]}: {count} times")

        print("Game counts:")
        for game, count in best_game_counts.items():
            print(f"  Game {game}: {count} times")

        print("Game team counts:")
        for game_number, counts in enumerate(best_game_team_counts, start=1):
            print(f"  Game {game_number}: {dict(enumerate(counts, start=1))}")


        return (
            self.convert_schedule_to_names(best_schedule),
            self.convert_game_counts_to_names(best_game_counts),
            self.convert_team_matchups_to_names(best_team_matchups),
            self.convert_game_team_counts_to_names(best_game_team_counts),
            self.convert_team_game_totals_to_names(best_game_team_counts),
        )

    def _find_best_schedule(self, attempts: int, progress_callback=None):
        best_schedule = self.generate_random_schedule()
        best_cost = self.check_schedule(best_schedule, include_details=False)
        completed = 1
        for _ in range(max(0, attempts - 1)):
            candidate = self.generate_random_schedule()
            cost = self.check_schedule(candidate, include_details=False)
            if cost < best_cost:
                best_schedule = candidate
                best_cost = cost
                if cost < 0.01:
                    break
            completed += 1
            if progress_callback and (completed % 1000 == 0 or completed == attempts):
                progress_callback(completed, best_cost)
        if progress_callback and completed == 1:
            progress_callback(completed, best_cost)
        return best_schedule, best_cost

    def _find_best_parallel(self):
        worker_count = min(self.parallel_workers, max(1, self.n_tries))
        batch_count = worker_count * 2
        base_attempts = self.n_tries // batch_count
        remainder = self.n_tries % batch_count
        payloads = []
        for batch_index in range(batch_count):
            attempts = base_attempts + (1 if batch_index < remainder else 0)
            if attempts:
                payloads.append((
                    self.jungscharen,
                    self.n_rounds,
                    self.n_games,
                    self.game_names,
                    attempts,
                    random.randrange(2**32),
                ))

        if worker_count == 1:
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
                        batch_progress[batch_id] = (completed, cost)
                        completed_attempts = sum(value[0] for value in batch_progress.values())
                        best_cost = min(
                            (value[1] for value in batch_progress.values()),
                            default=None,
                        )
                        if self.progress_update_callback:
                            self.progress_update_callback(int(completed_attempts / self.n_tries * 100))
                        if self.status_update_callback and best_cost is not None:
                            self.status_update_callback(
                                f"{completed_attempts:,} von {self.n_tries:,} Versuchen abgeschlossen · "
                                f"Qualitätswert: {best_cost:.4f} (je niedriger, desto besser)"
                            )

                    for future in finished:
                        schedule, cost = future.result()
                        batch_id = future_batches[future]
                        batch_progress[batch_id] = (future_attempts[future], cost)
                        completed_attempts = sum(value[0] for value in batch_progress.values())
                        if best_result is None or cost < best_result[1]:
                            best_result = (schedule, cost)
                        if self.progress_update_callback:
                            self.progress_update_callback(int(completed_attempts / self.n_tries * 100))
                        if self.status_update_callback and best_result:
                            self.status_update_callback(
                                f"{completed_attempts:,} von {self.n_tries:,} Versuchen abgeschlossen · "
                                f"Qualitätswert: {best_result[1]:.4f} (je niedriger, desto besser)"
                            )
        finally:
            manager.shutdown()

        if best_result is None:
            return self._find_best_schedule(1)
        return best_result

    def convert_schedule_to_names(self, schedule: list) -> pd.DataFrame:
        # Create a table where columns are games and rows are rounds
        table = []
        for round in schedule:
            row = {}
            for game in round:
                game_number, team1, team2 = game
                team1_info = self.team_lookup.get(team1)
                team2_info = self.team_lookup.get(team2)
                team1_name = self._format_team_name(team1_info)
                team2_name = self._format_team_name(team2_info)
                matchup = f"{team1_name} vs {team2_name}"
                row[self.game_names[game_number]] = matchup
            # Fill missing games with empty string
            for game_name in self.game_names:
                if game_name not in row:
                    row[game_name] = ""
            table.append(row)
        data = table
        schedule_df = pd.DataFrame(data)
        pivot_df = schedule_df[self.game_names]

        return pivot_df
    
    def convert_team_matchups_to_names(self, team_matchups: dict) -> pd.DataFrame:
        data = []
        for (team1, team2), count in team_matchups.items():
            team1_info = self.team_lookup.get(team1)
            team2_info = self.team_lookup.get(team2)
            team1_name = self._format_team_name(team1_info)
            team2_name = self._format_team_name(team2_info)
            data.append({"Team 1": team1_name, "Team 2": team2_name, "Count": count})
        return pd.DataFrame(data)
    
    def convert_game_counts_to_names(self, game_counts: dict) -> pd.DataFrame:
        data = []
        for game, count in game_counts.items():
            game_name = self.game_names[game]
            data.append({"Game": game_name, "Count": count})
        return pd.DataFrame(data)
    
    def convert_game_team_counts_to_names(self, game_team_counts: np.ndarray) -> pd.DataFrame:
        # Create a DataFrame where rows are games and columns are team names, values are counts
        team_names = [
            self._format_team_name(team) if team else f"Team {idx}"
            for idx, team in enumerate(self.team_names)
        ]
        game_names = [
            self.game_names[i] if i < len(self.game_names) else f"Game {i+1}"
            for i in range(game_team_counts.shape[0])
        ]
        df = pd.DataFrame(game_team_counts, columns=team_names)
        df.insert(0, "Game", game_names)
        return df

    def convert_team_game_totals_to_names(self, game_team_counts: np.ndarray) -> pd.DataFrame:
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


    def generate_random_schedule(self) -> list:
        """Generate a random schedule with the given parameters"""
        schedule = self.generate_round_robin_schedule()

        # Assign pairs of teams to games randomly
        game_schedule = []
        for round in schedule:
            game_numbers = list(range(self.n_games))  # List of game numbers
            random.shuffle(game_numbers)  # Shuffle the game numbers
            game_round = []
            for pair in round:
                game_number = game_numbers.pop()
                game_round.append((game_number, pair[0], pair[1]))

            game_schedule.append(sorted(game_round))  # Sort the games by game number

        return game_schedule
    

    def generate_round_robin_schedule(self) -> list:
        """Generate a round-robin schedule for the teams, where only teams from different jungscharen play against each other"""
        # Generate schedule: only teams from different jungscharen play against each other
        # Use a proper round-robin algorithm with rotation to ensure variety
        
        # Shuffle the pairs to create variety
        pair_count = len(self.all_possible_pairs)
        if pair_count == 0:
            return [[] for _ in range(self.n_rounds)]
        pair_start = random.randrange(pair_count)
        pair_step = -1 if random.getrandbits(1) else 1
        
        schedule = []
        pairs_used = set()
        
        # Iterate through the number of rounds
        # For each round, try to find pairs of teams that haven't played against each other yet
        for round_num in range(self.n_rounds):
            round_schedule = []
            teams_used_this_round = set()
            
            # Try to find pairs for this round
            for offset in range(pair_count):
                pair_index = (pair_start + pair_step * offset) % pair_count
                pair = self.all_possible_pairs[pair_index]
                team1, team2 = pair
                
                # Check if this pair hasn't been used and neither team is already scheduled this round
                if (pair not in pairs_used and 
                    (team2, team1) not in pairs_used and # check both directions for uniqueness
                    team1 not in teams_used_this_round and 
                    team2 not in teams_used_this_round):
                    
                    round_schedule.append(pair)
                    pairs_used.add(pair)
                    teams_used_this_round.add(team1)
                    teams_used_this_round.add(team2)

                    # Limit the number of games per round based on available games or teams and end the round if reached
                    if len(round_schedule) >= min(self.n_games, self.n_teams // 2):
                        break
            
            # If we couldn't find enough unique pairs, fill with available pairs
            if len(round_schedule) < min(self.n_games, self.n_teams // 2):
                for offset in range(pair_count):
                    pair_index = (pair_start + pair_step * offset) % pair_count
                    pair = self.all_possible_pairs[pair_index]
                    team1, team2 = pair
                    
                    if (team1 not in teams_used_this_round and 
                        team2 not in teams_used_this_round):
                        
                        round_schedule.append(pair)
                        teams_used_this_round.add(team1)
                        teams_used_this_round.add(team2)
                        
                        if len(round_schedule) >= min(self.n_games, self.n_teams // 2):
                            break
            
            schedule.append(round_schedule)
            
            # Reset pairs_used if we've used all possible combinations
            if len(pairs_used) >= len(self.all_possible_pairs):
                pairs_used.clear()

        return schedule

    def check_schedule(self, schedule: list, include_details: bool = True) -> tuple:
        """Check the schedule for balance and return a cost value"""
        # Use arrays in the hot path; dictionaries are only created for the final result.
        team_matchup_counts = np.zeros((self.n_teams, self.n_teams), dtype=np.int32)
        game_counts_array = np.zeros(self.n_games, dtype=np.int32)
        game_team_counts = np.zeros((self.n_games, self.n_teams))

        for round in schedule:
            for game in round:
                game_number = game[0]
                team1 = game[1]
                team2 = game[2]

                game_counts_array[game_number] += 1 # count how many times this game was played
                game_team_counts[game_number, team1] += 1 # count how many times this team played this game
                game_team_counts[game_number, team2] += 1 # count how many times this team played this game
                if team1 > team2:   # sort teams to ensure smallest team number is first
                    team1, team2 = team2, team1
                team_matchup_counts[team1, team2] += 1 # count how many times this matchup was played

        rounds_played_each_team = np.sum(game_team_counts, axis=0) # total rounds played by each team
        var_game_counts = np.var(game_counts_array) # variance of game counts across all games
        var_rounds_played_each_team = np.var(rounds_played_each_team) # variance of rounds played by each team
        var_team_matchups = np.var(team_matchup_counts[np.triu_indices(self.n_teams, k=1)]) # variance of team matchups across all pairs
        var_game_team_counts = np.var(game_team_counts)  # variance of game counts for each team

        cost_value = var_game_counts + var_game_team_counts*20 + var_rounds_played_each_team + var_team_matchups

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
        
