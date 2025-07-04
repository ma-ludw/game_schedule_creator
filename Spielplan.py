import random
import pandas as pd
import numpy as np
from tqdm import tqdm


t = 16  # Number of teams
r = 10  # Number of rounds
g = 4  # Number of games per round

def generate_schedule(t, r, g):
    # Generate a round-robin schedule
    teams = list(range(1, t + 1))
    schedule = []
    for _ in range(r):  # Repeat until we reach the desired number of rounds
        round_schedule = []
        for i in range(t//2):
            round_schedule.append((teams[i], teams[t - 1 - i]))
        teams.insert(1, teams.pop())
        schedule.append(round_schedule)

    # Assign pairs of teams to games randomly
    game_schedule = []
    for round in schedule:
        game_numbers = list(range(1, g + 1))  # List of game numbers
        random.shuffle(game_numbers)  # Shuffle the game numbers
        random_numbers = random.sample(range(len(schedule[0])), len(game_numbers))
        game_round = []
        for _ in range(len(random_numbers)):
            random_index = random_numbers.pop()
            pair = round[random_index]
            game_number = game_numbers.pop()
            game_round.append((game_number, pair[0], pair[1]))

        # for pair in round:
        #     if game_numbers:  # If there are still game numbers left
        #         game_number = game_numbers.pop()  # Take a game number
        #         game_round.append((game_number, pair[0], pair[1]))  # Assign the game number to the pair of teams
        game_schedule.append(sorted(game_round))  # Sort the games by game number

    return game_schedule


def generate_and_check_schedule(n, m, t):
    best_schedule = None
    best_game_counts = None
    best_team_matchups = None
    best_diff = 0
    tries = 0

    for _ in tqdm(range(10000)):  # Repeat until the conditions are met or until 100000 iterations have been reached
        tries += 1
        schedule = generate_schedule(n, m, t)

        # Count how many times each team played against each other
        team_matchups = {(team1, team2): 0 for team1 in range(1, n + 1) for team2 in range(team1 + 1, n + 1)}
        game_counts = {game: 0 for game in range(1, t + 1)}
        game_team_counts = np.zeros((t, n))

        for round in schedule:
            for game in round:
                game_number, team1, team2 = game
                game_team_counts[game_number-1][team1-1] += 1
                game_team_counts[game_number-1][team2-1] += 1
                if team1 > team2:  # Ensure team1 is always the smaller team
                    team1, team2 = team2, team1
                team_matchups[(team1, team2)] += 1  # Increment the count for the team matchup
                game_counts[game_number] += 1  # Increment the count for the game

        diff_game_counts = max(game_counts.values()) - min(game_counts.values())
        diff_game_team_counts = np.amax(game_team_counts) - np.amin(game_team_counts)
        game_team_counts_sum = np.sum(game_team_counts, axis=0)
        diff_team_palays = np.amax(game_team_counts_sum) - np.amin(game_team_counts_sum)
        diff_team_matchups = max(team_matchups.values()) - min(team_matchups.values())
        # count number of equal plays and multiply by the number.
        diff =diff_team_palays# diff_game_counts + diff_game_team_counts + diff_team_matchups + 10*diff_team_palays

        if diff == 0:  # If the conditions are met
            print(f"Number of tries: {tries}")
            return schedule, game_counts, team_matchups, game_team_counts  # Return the schedule and the counts


        if best_schedule is None or best_diff > diff:  # If this schedule is better than the best one found so far
            best_schedule = schedule
            best_game_counts = game_counts
            best_team_matchups = team_matchups
            best_game_team_counts = game_team_counts
            best_diff = diff

    print(f"Number of tries: {tries}")
    return best_schedule, best_game_counts, best_team_matchups, best_game_team_counts  # Return the best schedule and the counts found so far

schedule, game_counts, team_matchups, game_team_counts = generate_and_check_schedule(t, r, g)

# Print the schedule and the counts in a human-readable format
for i, round in enumerate(schedule, 1):
    print(f"Round {i}:")
    for game in round:
        print(f"  Game {game[0]}: Team {game[1]} vs Team {game[2]}")
    print()

print("Team matchups:")
for teams, count in team_matchups.items():
    print(f"  Teams {teams[0]} and {teams[1]}: {count} times")

print("Game counts:")
for game, count in game_counts.items():
    print(f"  Game {game}: {count} times")

# Convert the schedule to a DataFrame
schedule_df = pd.DataFrame([(i + 1, game[0], game[1], game[2]) for i, round in enumerate(schedule) for game in round], columns=['Round', 'Game', 'Team 1', 'Team 2'])

# Convert the game counts to a DataFrame
game_counts_df = pd.DataFrame(list(game_counts.items()), columns=['Game', 'Count'])

# Convert game_team_counts to a DataFrame
game_team_counts_df = pd.DataFrame(game_team_counts)

# Convert the team matchups to a DataFrame
team_matchups_df = pd.DataFrame([(teams[0], teams[1], count) for teams, count in team_matchups.items()], columns=['Team 1', 'Team 2', 'Count'])

# Combine 'Team 1' and 'Team 2' into a single column
schedule_df['Teams'] = schedule_df['Team 1'].astype(str) + ' vs ' + schedule_df['Team 2'].astype(str)

# Pivot the DataFrame
pivot_df = schedule_df.pivot(index='Round', columns='Game', values='Teams')

# Write the pivoted DataFrame to an Excel file
with pd.ExcelWriter('schedule.xlsx') as writer:
    pivot_df.to_excel(writer, sheet_name='Schedule')
    game_counts_df.to_excel(writer, sheet_name='Game Counts', index=False)
    team_matchups_df.to_excel(writer, sheet_name='Team Matchups', index=False)
    game_team_counts_df.to_excel(writer, sheet_name='Game Team Counts', index=False)