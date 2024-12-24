################################################################
################## Playcall Profiler ###########################
################################################################
from utils import *
import pandas as pd
import json
import requests
from datetime import datetime
import streamlit as st

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
    selected_team = st.selectbox("NFL Team:", options=teams['display_name'])
    selected_team_row = teams[teams['display_name'] == selected_team]
    selected_team_image = selected_team_row.iloc[0]['default_logo']
    st.image(selected_team_image, width = 150)


    # Home / Away ---------------------------
    st.multiselect("Setting: ", ['Home', 'Away'], default = ['Home', 'Away'])

    # Time Frame ----------------------------
    setting_list = {
        '1st Quarter': 1,
        '2nd Quarter': 2,
        '3rd Quarter': 3,
        '4th Quarter': 4,
        '2-Minute Drill': 5
        }
    setting_keys = setting_list.keys()
    st.multiselect("Time: ", options=setting_keys, default = setting_keys)

    # Scoring Margin -------------------------
    scoring_list ={
        'Tied': 0,
        '1-Score': 1,
        '2-Score': 2,
        '3-Score +': 3
    }
    scoring_keys = scoring_list.keys()
    st.multiselect("Margin", options=scoring_keys, default=scoring_keys)

    # Leading/Trailing/Tied ------------------
    leading_list = {
        'Tied': 0,
        'Leading': 1,
        'Trailing': 2
    }
    leading_keys = leading_list.keys()
    st.multiselect("Score:", options=leading_keys, default=leading_keys)

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

    # Down -----------------------------------
    downs = [1, 2, 3, 4]
    st.multiselect("Down: ", options = downs, default=downs)

    # Distance -------------------------------
    distances = list(range(1, 31))
    st.slider("Distance: ", min_value=1, max_value=30, value =(1, 10), step =1)

    # Disclaimer

    st.divider()
    st.markdown('''
                *I do not own the data. All data is sourced via NFL API (Rapid API) via ESPN Stats.*
                ''')