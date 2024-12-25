import pandas as pd
import streamlit as st
import json
import requests
#from pandas import json_normalize
from datetime import datetime

# DATA SOURCING ------------------------------------------------------------

# Load List of NFL Teams
def load_teams():
    teams = pd.read_csv('data/nflTeamData.csv')
    return teams

# Map Yard Lines from st.slider
def map_yard_line(yard):
    if yard < 0:  # Own side
        return f"Own {50 - abs(yard)}"
    elif yard > 0:  # Opponent's side
        return f"Opposing {50 - yard}"
    else:  # Midfield
        return "Midfield (50-yard line)"
    
def calculate_yards_to_go(yard):
    if yard < 0:  # Own side (negative yard line)
        return 50 + abs(yard)  # Distance to the 50-yard line plus the remaining yards
    elif yard > 0:  # Opponent's side (positive yard line)
        return 50 - yard  # Distance to the opponent's end zone
    else:  # Midfield (0-yard line)
        return 50  # Halfway to the opponent's end zone
    
# Load Team Data
def load_team_data():
    # Load Team Data
    teamGameData = pd.read_csv('data/event_team_data.csv', index_col=False)
    teamGameData = teamGameData.drop_duplicates()

    # Load Team List
    teams = load_teams()

    # Join Data
    teamData = pd.merge(teamGameData, teams[['teamId', 'abbreviation']], on='teamId', how='left')

    # Process Data

    # 1. Pivot to flatten data
    df_home = teamData[teamData['homeAway'] == 'home'].rename(columns={
        'teamId': 'home_team_id',
        'final_score': 'home_score_final',
        'winner': 'home_winner',
        'total_record':'home_record',
        'abbreviation':'home_abbrev'
    })

    df_away = teamData[teamData['homeAway'] == 'away'].rename(columns={
        'teamId': 'away_team_id',
        'final_score': 'away_score_final',
        'winner': 'away_winner',
        'total_record': 'away_record',
        'abbreviation':'away_abbrev'
    })

    # 2. Merge the home and away DataFrames on 'gameId'
    df_flat = pd.merge(df_home[['gameId', 'home_team_id', 'home_score_final', 'home_winner', 'home_record', 'home_abbrev']],
                    df_away[['gameId', 'away_team_id', 'away_score_final', 'away_winner', 'away_record', 'away_abbrev']],
                    on='gameId', how='left')

    # 3. Determine the winning team based on the 'winner' column
    df_flat['winning_team_id'] = df_flat.apply(lambda row: row['home_team_id'] if row['home_winner'] else row['away_team_id'], axis=1)

    # 4. Drop the intermediate winner columns
    teamData_flat = df_flat.drop(columns=['home_winner', 'away_winner'])


    return teamData_flat

# Load Play By Play Data
def load_pbp_data():
    pbp = pd.read_csv('data/event_playbyplay.csv', index_col=False)

    # Clean Play Types
    excluded_types = [53, 74, 2, 75, 15, 66, 65, 32, 21, 12, 79, 2]
    pbp = pbp[~pbp['type_id'].isin(excluded_types)].drop_duplicates()

    return pbp

# Process + Clean Data
def data_processing():

    # Load Data
    teamData = load_team_data()
    pbp = load_pbp_data()

    # Join Data
    pbp_clean = pd.merge(pbp, teamData, how='left', on ='gameId')

    # Adding Home + Away Team Ids
    pbp_clean['is_home_team'] = (pbp_clean['start_team_id'] == pbp_clean['home_team_id'])

    # Adding Time in Seconds
    pbp_clean['time_in_seconds'] = pbp_clean.apply(convert_to_seconds, axis=1)

    # Adding Time Bucket
    pbp_clean['time_bucket'] = pbp_clean.apply(time_buckets, axis=1)

    # Adding Scoring Margin
    pbp_clean['score_margin'] = pbp_clean.apply(margin_bucket, axis=1)

    # Adding Game Status
    pbp_clean['score_status'] = pbp_clean.apply(game_status, axis=1)

    # Adding Transformed Yard Line
    pbp_clean['start_yardLine_transformed'] = pbp_clean.apply(transform_yard_line, axis=1)

    # Adding Yard Line Bucket
    pbp_clean['yardLine_bucket'] = pbp['start_yardLine'].apply(categorize_yard_line)

    return pbp_clean

# PROCESSING FUNCTIONS -----------------------------------------------------------------------------

# Handling Time + Clock
def convert_to_seconds(row):
    minutes, seconds = map(int, row['clock'].split(':'))
    total_seconds = minutes * 60 + seconds
    if row['period'] == 1:
        return total_seconds + 2700
    elif row['period'] == 2:
        return total_seconds + 1800 
    elif row['period'] == 3:
        return total_seconds + 900  
    elif row['period'] == 4:
        return total_seconds  

def time_buckets(row):
    if row['time_in_seconds'] >= 2700:
        return 1
    elif row['time_in_seconds'] >= 1950:
        return 2
    elif row['time_in_seconds'] >= 1800:
        return 5
    elif row['time_in_seconds'] >= 900:
        return 3
    elif row['time_in_seconds'] >= 150:
        return 4
    elif row['time_in_seconds'] >=0:
        return 5

# Handling Score Margin + Lead Status
def margin_bucket(row):
    # Calculate the absolute score margin
    margin = abs(row['homeScore'] - row['awayScore'])
    # Categorize margin into buckets
    if margin == 0:
        return 0
    elif margin <= 8:
        return 1
    elif margin <= 16:
        return 2
    else:
        return 3
    
def game_status(row):
    if row['is_home_team']:  # Home team is being considered
        if row['homeScore'] > row['awayScore']:
            return 1
        elif row['homeScore'] < row['awayScore']:
            return 2
        else:
            return 0
    else:  # Away team is being considered
        if row['awayScore'] > row['homeScore']:
            return 1
        elif row['awayScore'] < row['homeScore']:
            return 2
        else:
            return 0
        
# Handling Field Position
def transform_yard_line(row):
    start_yard_line = row['start_yardLine']
    if start_yard_line > 50:
        return 100 - start_yard_line
    else:
        return start_yard_line

def categorize_yard_line(yard_line):
    if 100 >= yard_line >= 90:
        return "Inside Own 10"
    elif 90 > yard_line >= 50:
        return "Own Territory"
    elif 50 > yard_line >= 20:
        return "Opposing Territory"
    elif 20 > yard_line >= 6:
        return "Red Zone"
    elif 5 >= yard_line >= 0:
        return "Inside Opponent's 5"
    else:
        return "Invalid Yard Line"
    
# FILTERING DATA ------------------------------------------------------------------------------------
def parameterized_data(parameters):

    # Load PBP Data
    data = data_processing()

    # Parameters ----------------------------------------

    # 1. Team
    selected_team_ids = parameters["selected_team_ids"]
    #st.write('Team IDS:', selected_team_ids)

    # 2. Home + Away
    homeaway = parameters["homeaway"]
    #st.write('HomeAway:', homeaway)

    # 3. Time Setting
    timesetting = parameters["timesetting"]
    #st.write('Time Setting:', timesetting)

    # 4. Margin
    margin = parameters["margin"]
    #st.write('Margin:', margin)

    # 5. Yard Line Range
    yard_line_range = parameters["yard_line_range"]
    #st.write('Yard Line Range:', yard_line_range)

    # 6. Score
    score = parameters["score"]
    #st.write('Score:', score)

    # 7. Down
    down = parameters["down"]
    #t.write('Down:', down)

    # 8. Distance
    distance = parameters["distance_range"]
    #st.write('Distance Range:', distance)


    # Filtered Data
    subset = data[
        (data['start_team_id'].isin(selected_team_ids)) &
        (data['is_home_team'].isin(homeaway)) &
        (data['start_yardLine'].isin(yard_line_range)) &
        (data['time_bucket'].isin(timesetting)) &
        (data['score_margin'].isin(margin)) &
        (data['score_status'].isin(score)) &
        (data['down'].isin(down)) &
        (data['distance'].isin(distance))
    ]

    return subset

# CALCULATING KPIS ---------------------------------------------------------------------------------
def calc_kpi_playbreakdown(subset):
    # Define KPIs
    totalPlays = len(subset)

    # Pass and Run Plays
    pass_type_ids = [24, 3, 67, 24]
    run_type_ids = [68, 5]

    # Calculating the KPIs
    passPlays = len(subset[subset['type_id'].isin(pass_type_ids)])
    runPlays = len(subset[subset['type_id'].isin(run_type_ids)])

    kpis = {
        "Pass Plays": passPlays,
        "Run Plays": runPlays,
    }

    return kpis