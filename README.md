# game_schedule_creator
Create a game schedule for multiple teams, rounds and games

## Overview
This tool helps you create balanced game schedules for events where multiple "Jungscharen" (youth groups) with different numbers of teams compete in various games across multiple rounds. The application ensures fair distribution of games among teams and balanced matchups between different youth groups.

## Features
- **Multi-Group Support**: Handle multiple Jungscharen with different numbers of teams
- **Balanced Scheduling**: Ensures fair distribution of games and matchups
- **Excel Export**: Automatically generates detailed Excel reports
- **Real-time Progress**: Shows optimization progress with a progress bar
- **Customizable Games**: Define your own game names and quantities

## Installation & Requirements

### Prerequisites
- Python 3.8 or higher
- Required Python packages:
  ```bash
  pip install PySide6 pandas numpy openpyxl
  ```

### Running the Application
1. Download or clone the repository
2. Install the required dependencies
3. Run the application:
   ```bash
   python main.py
   ```

## Usage Instructions

### Step 1: Configure Jungscharen
1. **Set Number of Jungscharen**: Use the spin box to specify how many Jungscharen will participate
2. **Configure Each Jungschar**:
   - In the "Jungschar Name" column, enter the name of each Jungschar
   - In the "Anzahl Gruppen" column, specify how many teams each Jungschar has
   - The tool will automatically update the group naming table

### Step 2: Configure Games
1. **Set Number of Games**: Use the spin box to specify how many different games will be played simultaneously in each round
2. **Name Your Games**: In the game names table, enter descriptive names for each game (e.g., "Football", "Basketball", "Volleyball")

### Step 3: Set Number of Rounds
1. **Configure Rounds**: Use the spin box to set how many rounds the tournament will have

### Step 4: Generate Schedule
1. **Click "Generate"**: Press the generate button to start the optimization process
2. **Monitor Progress**: Watch the progress bar as the algorithm finds the optimal schedule
3. **Wait for Completion**: The process typically takes a few minutes depending on complexity

### Step 5: Review Results
After generation, the tool will:
- Display the final cost/quality score in the console
- Show statistics about team matchups and game distribution
- Automatically save results to `schedule.xlsx`

## Output Files

The tool generates an Excel file (`schedule.xlsx`) with multiple sheets:

### 1. Schedule Sheet
- **Rows**: Each round of the tournament
- **Columns**: Each game type
- **Content**: Team matchups in format "Jungschar.Team vs Jungschar.Team"

### 2. Game Counts Sheet
- Shows how many times each game was played
- Helps verify balanced game distribution

### 3. Team Matchups Sheet
- Lists all team pairings and how often they played against each other
- Ensures fair matchup distribution

### 4. Game Team Counts Sheet
- Shows how many times each team played each game
- Verifies that all teams get equal opportunities

## Understanding the Results

### Quality Metrics
The algorithm optimizes for:
- **Balanced Game Distribution**: Each game should be played roughly the same number of times
- **Fair Team Participation**: Each team should play approximately the same number of games
- **Diverse Matchups**: Teams should play against different opponents
- **Equal Game Exposure**: Each team should experience all game types fairly

## Tips for Best Results

### 1. Optimal Configuration
- **Team Numbers**: Try to have similar numbers of teams per Jungschar
- **Sufficient Rounds**: More rounds allow better balance (aim for at least 3-5 rounds)
