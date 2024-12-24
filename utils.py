import pandas as pd
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