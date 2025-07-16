from Jungschar import Jungschar
import pandas as pd
import numpy as np
import random

from PySide6.QtWidgets import QProgressBar, QApplication
from typing import Callable


class ScheduleGenerator():

    def __init__(
        self,
        jungscharen: list[Jungschar],
        n_rounds: int,
        n_games: int,
        games_names: list[str],
        progress_update_callback: Callable
    ):
        self.jungscharen = jungscharen
        self.n_games = n_games
        self.game_names = games_names
        self.n_rounds = n_rounds

        self.progress_update_callback = progress_update_callback

        self.n_teams = sum([js.n_groups for js in self.jungscharen])
        
        # Create teams with clear assignment to Jungscharen
        self.team_names = []
        self.jungschar_teams = {}  # Maps jungschar_name -> list of team_numbers
        team_counter = 0
        
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

        self.n_tries = 100000000
        
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


    def generate_schedule(self):        
        # init
        best_schedule = self.generate_random_schedule()
        best_cost, team_matchups, game_counts, game_team_counts = self.check_schedule(best_schedule)  # Get initial cost
        tries = 1

        self.progress_update_callback(0)
        QApplication.processEvents()
        for _ in range(self.n_tries):
            random_schedule = self.generate_random_schedule()
            cost, team_matchups, game_counts, game_team_counts = self.check_schedule(random_schedule)
            if cost < best_cost:
                best_schedule = random_schedule
                best_cost = cost
                if cost < 0.01:
                    print(f"Found a perfect schedule after {tries} tries!")
                    self.progress_update_callback(100)
                    QApplication.processEvents()
                    break
            tries += 1
            if self.progress_update_callback and tries % 1000 == 0:  # Update every 1000 iterations to avoid too frequent updates
                self.progress_update_callback(int((tries / self.n_tries) * 100))
                QApplication.processEvents()  # Force GUI update

        print("Team matchups:")
        for teams, count in team_matchups.items():
            print(f"  Teams {teams[0]} and {teams[1]}: {count} times")

        print("Game counts:")
        for game, count in game_counts.items():
            print(f"  Game {game}: {count} times")

        print("Game team counts:")
        for game_number, counts in enumerate(game_team_counts, start=1):
            print(f"  Game {game_number}: {dict(enumerate(counts, start=1))}")


        return self.convert_schedule_to_names(best_schedule), self.convert_game_counts_to_names(game_counts), self.convert_team_matchups_to_names(team_matchups), self.convert_game_team_counts_to_names(game_team_counts)
    
    def convert_schedule_to_names(self, schedule: list) -> pd.DataFrame:
        # Create a table where columns are games and rows are rounds
        table = []
        for round in schedule:
            row = {}
            for game in round:
                game_number, team1, team2 = game
                team1_info = self.team_lookup.get(team1)
                team2_info = self.team_lookup.get(team2)
                team1_name = f"{team1_info['jungschar_name']}.{team1_info['group_name']}" if team1_info else "Unknown"
                team2_name = f"{team2_info['jungschar_name']}.{team2_info['group_name']}" if team2_info else "Unknown"
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
            team1_name = f"{team1_info['jungschar_name']}.{team1_info['group_name']}" if team1_info else "Unknown"
            team2_name = f"{team2_info['jungschar_name']}.{team2_info['group_name']}" if team2_info else "Unknown"
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
            f"{team['jungschar_name']}.{team['group_name']}" if team else f"Team {idx}"
            for idx, team in enumerate(self.team_names)
        ]
        game_names = [
            self.game_names[i] if i < len(self.game_names) else f"Game {i+1}"
            for i in range(game_team_counts.shape[0])
        ]
        df = pd.DataFrame(game_team_counts, columns=team_names)
        df.insert(0, "Game", game_names)
        return df


    def generate_random_schedule(self) -> list:
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
        # Generate schedule: only teams from different jungscharen play against each other
        # Use a proper round-robin algorithm with rotation to ensure variety
        
        # Shuffle the pairs to create variety
        random.shuffle(self.all_possible_pairs)
        
        schedule = []
        pairs_used = set()
        
        for round_num in range(self.n_rounds):
            round_schedule = []
            teams_used_this_round = set()
            
            # Try to find pairs for this round
            for pair in self.all_possible_pairs:
                team1, team2 = pair
                
                # Check if this pair hasn't been used and neither team is already scheduled this round
                if (pair not in pairs_used and 
                    (team2, team1) not in pairs_used and 
                    team1 not in teams_used_this_round and 
                    team2 not in teams_used_this_round):
                    
                    round_schedule.append(pair)
                    pairs_used.add(pair)
                    teams_used_this_round.add(team1)
                    teams_used_this_round.add(team2)
                    
                    # Limit the number of games per round based on available games or teams
                    if len(round_schedule) >= min(self.n_games, self.n_teams // 2):
                        break
            
            # If we couldn't find enough unique pairs, fill with available pairs
            if len(round_schedule) < min(self.n_games, self.n_teams // 2):
                for pair in self.all_possible_pairs:
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

    def check_schedule(self, schedule: list):
        # count how many times each team played against each other
        team_matchups = {(team1, team2): 0 for team1 in range(self.n_teams) for team2 in range(team1 + 1, self.n_teams)}

        # count how much each game was played by each team
        game_counts = {game: 0 for game in range(self.n_games)}
        game_team_counts = np.zeros((self.n_games, self.n_teams))

        for round in schedule:
            for game in round:
                game_number = game[0]
                team1 = game[1]
                team2 = game[2]

                game_counts[game_number] += 1
                game_team_counts[game_number, team1] += 1
                game_team_counts[game_number, team2] += 1
                if team1 > team2:
                    team1, team2 = team2, team1
                team_matchups[(team1, team2)] += 1

        diff_game_counts = max(game_counts.values()) - min(game_counts.values())
        diff_game_team_counts = np.amax(game_team_counts) - np.amin(game_team_counts)
        rounds_played_each_team = np.sum(game_team_counts, axis=0)
        diff_rounds_played_each_team = np.amax(rounds_played_each_team) - np.amin(rounds_played_each_team)
        diff_team_matchups = max(team_matchups.values()) - min(team_matchups.values())

        cost_value = diff_game_counts + diff_game_team_counts*40 + diff_rounds_played_each_team + diff_team_matchups

        return cost_value, team_matchups, game_counts, game_team_counts
        

