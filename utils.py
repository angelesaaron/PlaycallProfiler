import pandas as pd
import streamlit as st
import json
import requests
#from pandas import json_normalize
from datetime import datetime
import plotly.express as px

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
    pbp_clean['yardLine_bucket'] = pbp['start_ytez'].apply(categorize_yard_line)


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
    start_yard_line = row['start_ytez']
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
        (data['start_ytez'].isin(yard_line_range)) &
        (data['time_bucket'].isin(timesetting)) &
        (data['score_margin'].isin(margin)) &
        (data['score_status'].isin(score)) &
        (data['down'].isin(down)) &
        (data['distance'].isin(distance))
    ]

    return subset

# CALCULATING KPIS ---------------------------------------------------------------------------------

# Play Breakdown Chart
def create_play_breakdown_chart(data):

    # Define Play Type IDs
    pass_type_ids = [24, 3, 67, 24, 26, 51, 36, 7]
    run_type_ids = [68, 5, 39, 9, 29]
    punt_ids = [52, 17]
    fg_ids = [60, 59, 38, 18, 40]
    penalty_ids = [8]
    
    # Calculate KPIs
    passPlays = len(data[data['type_id'].isin(pass_type_ids)])
    runPlays = len(data[data['type_id'].isin(run_type_ids)])
    puntPlays = len(data[data['type_id'].isin(punt_ids)])
    fgPlays = len(data[data['type_id'].isin(fg_ids)])
    penaltyPlays = len(data[data['type_id'].isin(penalty_ids)])
    
    kpis = {
        "Pass": passPlays,
        "Run": runPlays,
        "FG": fgPlays,
        "Punt": puntPlays,
        "Penalty": penaltyPlays
    }

    filtered_kpis = {key: value for key, value in kpis.items() if value > 0}

    # Define fixed colors
    fixed_colors = {
        "Pass": "#1f77b4",  # Blue for pass plays
        "Run": "#2ca02c",   # Green for run plays
        "FG": "#FFD700",  # Yellow/Gold for field goals
        "Punt": "#808080",        # Gray for punts
        "Penalty": "#FF5722"     # Red for penalties
    }
    # Prepare Pie Chart
    labels = list(filtered_kpis.keys())
    values = list(filtered_kpis.values())

    fig = px.pie(
        values=values,
        names=labels,
        title="Play Breakdown",
        color=labels,  # Map labels to colors
        color_discrete_map=fixed_colors  # Apply fixed color mapping
    )

    # Update Pie Chart Appearance
    fig.update_traces(
        textinfo='percent+label',  # Show both percentage and label
        textfont_size=20          # Increase text font size for percentages
    )
    fig.update_layout(showlegend=False)  # Hide legend

    # Display Pie Chart
    st.plotly_chart(fig)

# Turnover % KPI, 
def create_kpis(data):
    turnover_ids = [36, 39, 29, 20, 26]
    interception_ids = [26, 36]
    fumble_ids = [39, 9, 29]
    punt_ids = [52, 17]
    fg_ids = [60, 59, 38, 18, 40]

    #-------------------------------

    totalplays = len(data)
    scoringPlays = len(data[data['scoringPlay']== True])

    withoutST = data[~data['type_id'].isin(punt_ids + fg_ids)]

    lenWithoutST = len(withoutST)
    explosivePlays = len(withoutST[withoutST['yardage'] >= 20])

    negativeplay = len(withoutST[withoutST['yardage'] < 0])

    turnovers = len(withoutST[withoutST['type_id'].isin(turnover_ids)])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Plays", totalplays)
    col1.metric("Explosive Plays", explosivePlays)
    if totalplays > 0:
        col2.metric("Scoring", f"{(scoringPlays / totalplays) * 100:.1f}%")
    else:
        col2.metric("Scoring", "0%") 
    if lenWithoutST > 0:
        col3.metric("Turnover", f"{(turnovers / totalplays) * 100:.1f}%")
        col4.metric("Negative Play", f"{(negativeplay / lenWithoutST) * 100:.1f}%")
    else:
        col4.metric("Negative Play", "0%")
        col3.metric("Turnover", "0%")


def create_key_plays(data):
    punt_ids = [52, 17]
    fg_ids = [60, 59, 38, 18, 40]
    withoutST = data[~data['type_id'].isin(punt_ids + fg_ids)]
    scoring_true = withoutST[withoutST['scoringPlay'] == True]
    scoring_false = withoutST[withoutST['scoringPlay'] == False]

    # Sort scoringFalse by yardage in descending order
    scoring_false_sorted = scoring_false.sort_values(by='yardage', ascending=False)

    # Concatenate the two DataFrames, scoringTrue comes first
    sorted_data = pd.concat([scoring_true, scoring_false_sorted])

    # Optionally reset index
    sorted_data.reset_index(drop=True, inplace=True)
    # Display the top 5 plays' text values using st.write
    top_plays = sorted_data['text'].head(5)
    
    st.subheader('Key Plays')
    # Loop through each play and display it
    for i, play_text in enumerate(top_plays, 1):
        st.write(f"{i}. {play_text}")
