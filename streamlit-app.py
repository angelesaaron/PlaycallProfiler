################################################################
################## Playcall Profiler ###########################
################################################################
from utils import *
import pandas as pd
import json
import requests
from datetime import datetime
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="NFL Playcall Profiler", initial_sidebar_state="expanded")

##########################################
##     Title, Tabs, and Sidebar         ##
##########################################

# Title ----------------------------------
st.title("Playcall Profiler")

# Tabs -----------------------------------
tab_dashboard, tab_faq = st.tabs(["Playcall Analysis", 'FAQ'])

###########################################
##       1. Playcall Analysis            ##
###########################################
with tab_dashboard:
    st.write("Choose a scenario and identify offensive play-calling trends.")

    # Parameters --------------------------

    # Load Teams --------------------------
    teams = load_teams()

    # Select Team -------------------------
    selected_team = st.multiselect("NFL Team:", options=teams['display_name'], default='Arizona Cardinals')
    # Check if no team is selected
    if not selected_team:
        st.warning("Please select at least one NFL team!")
    selected_team_rows = teams[teams['display_name'].isin(selected_team)]
    selected_team_ids = selected_team_rows['teamId'].tolist()
    if not selected_team_rows.empty:
        for _, row in selected_team_rows.iterrows():
            st.image(row['default_logo'], width=150, caption=row['display_name'])


    # Home / Away ---------------------------
    homeaway = st.multiselect("Setting: ", ['Home', 'Away'], default = ['Home', 'Away'])
    # Map selections to True/False values
    homeaway_list = [True] if 'Home' in homeaway else []
    homeaway_list += [False] if 'Away' in homeaway else []

    # Time Frame ----------------------------
    setting_list = {
        '1st Quarter': 1,
        '2nd Quarter': 2,
        '3rd Quarter': 3,
        '4th Quarter': 4,
        '2-Minute Drill': 5
        }
    setting_keys = setting_list.keys()
    timesetting = st.multiselect("Time: ", options=setting_keys, default = setting_keys)
    timesetting_values = [setting_list[key] for key in timesetting]

    # Scoring Margin -------------------------
    scoring_list ={
        'Tied': 0,
        '1-Score': 1,
        '2-Score': 2,
        '3-Score +': 3
    }
    scoring_keys = scoring_list.keys()
    margin = st.multiselect("Margin", options=scoring_keys, default=scoring_keys)
    margin_values = [scoring_list[key] for key in margin]

    # Leading/Trailing/Tied ------------------
    leading_list = {
        'Tied': 0,
        'Leading': 1,
        'Trailing': 2
    }
    leading_keys = leading_list.keys()
    score = st.multiselect("Score:", options=leading_keys, default=leading_keys)
    score_values = [leading_list[key] for key in score]
    # Select Yardage -------------------------
    yard_line_range = st.slider(
        "Select a range of yard lines",
        min_value=-50,
        max_value=50,
        value=(-25, 25),
        step=1,
        format=""
    )
    # Print Mapped Yardage
    start_yard, end_yard = yard_line_range
    start_position = map_yard_line(start_yard)
    end_position = map_yard_line(end_yard)
    st.write(f"{start_position} to {end_position}")
    # Calculate Yardage to Go

    start_yards_to_go = calculate_yards_to_go(start_yard)
    end_yards_to_go = calculate_yards_to_go(end_yard)
    yard_line_range = list(range(end_yards_to_go, start_yards_to_go + 1))

    # Down -----------------------------------
    downs = [1, 2, 3, 4]
    down = st.multiselect("Down: ", options = downs, default=downs)

    # Distance -------------------------------
    distances = list(range(1, 31))
    distance = st.slider("Distance: ", min_value=1, max_value=30, value =(1, 10), step =1)
    start_distance, end_distance = distance
    distance_range = list(range(start_distance, end_distance + 1))
    # Consolidate Parameters
    parameters = {
    "selected_team_ids": selected_team_ids,
    "homeaway": homeaway_list,
    "timesetting": timesetting_values,
    "margin": margin_values,
    "yard_line_range": yard_line_range,
    "score": score_values,
    "down": down,
    "distance_range": distance_range
}

    data = parameterized_data(parameters)


    # DATA VISUALIZATION

    # Calculate KPIs
    kpis = calc_kpi_playbreakdown(data)
    labels = list(kpis.keys())
    values = list(kpis.values())
    # Create Pie Chart
    fig = px.pie(values=values, names=labels, title="Play Breakdown")

    # Display Pie Chart in Streamlit
    st.plotly_chart(fig)







    # Disclaimer

    st.divider()
    st.markdown('''
                *I do not own the data. All data is sourced via NFL API (Rapid API) via ESPN Stats.*
                ''')
    