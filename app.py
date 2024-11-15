#!/usr/bin/env python3

from dash import dcc, html
from dash.dependencies import Input, Output

import dash
import numpy as np
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET

# List of stations
stalst = ['AJAC' , 'ARBF', 'ARTF', 'BELV' , 'BLAF', 'BSTF', 'CAGN' , 'CALF' , 'EILF'  , 'ENAUX', 'ESCA',
          'GLAN' , 'ISO' , 'LEPF', 'MCECU', 'MENA', 'MFC' , 'MIGAL', 'MLYF' , 'MORSI' , 'MVIF' , 'NALS',
          'NCAD' , 'NCAU', 'NIMR', 'NLIB' , 'NOCA', 'NPOR', 'NSJA' , 'PIAF' , 'PRESIS', 'REVF' , 'RUSF',
          'SALSA', 'SAOF', 'SAUF', 'SLAF' , 'SMPL', 'SPIF', 'STROF', 'TRIGF', 'TURF'  ]

# Download the stationsXML
url = "https://sismoazur.oca.eu/fdsnws/station/1/query?net=FR,RA&station="
for i in range(len(stalst)): url += f"{stalst[i]},"
url      = url[:-1]
response = requests.get(url)

# Parse XML with namespace
ns = {'fdsn': 'http://www.fdsn.org/xml/station/1'}
root = ET.fromstring(response.content)

staname  = []
stalat   = []
stalon   = []
stanet   = []
postcode = []
for network in root.findall(".//fdsn:Network", ns):
    for station in network.findall(".//fdsn:Station", ns):
        staname.append( station.get('code') )
        stalat .append( float(station.find("fdsn:Latitude" , ns).text) )
        stalon .append( float(station.find("fdsn:Longitude", ns).text) )
        stanet .append( network.get('code') )
        name = station.find("fdsn:Site" , ns).find("fdsn:Name" , ns).text
        if "administrative code" in name: 
            postcode.append( name.split(":"  )[1].strip()[:2] )
        elif " - " in name:
            postcode.append( name.split(" - ")[1].strip()[:2] )
        else:
            postcode.append( "06" )

# Load your seismic station data into a DataFrame
data = {
    'Station'  : staname,
    'Latitude' : stalat,
    'Longitude': stalon,
    'Network'  : stanet,
    'Postal'   : postcode}
df = pd.DataFrame(data)

# Initialize Dash app
app = dash.Dash(__name__)

# Define layout with dropdown for selecting stations by Network or CENALT stations
app.layout = html.Div([
    # Dropdown for selecting stations based on Network (RA or FR), CENALT stations, or CD06 stations
    html.Div([
        html.Label("Critère de Selection:"),
        dcc.Dropdown(
            id="station-select",
            options=[
                {"label": "Code RA", "value": "RA"},
                {"label": "Code FR ", "value": "FR"},
                {"label": "Stations CENALT", "value": "CENALT"},
                {"label": "Stations CD06", "value": "CD06"}
            ],
            placeholder="RA, FR, CENALT, or CD06",
        )
    ], style={'width': '20%', 'display': 'inline-block', 'vertical-align': 'top', 'margin-right': '2%'}),

    # Main map container with a small top margin
    html.Div([
        dcc.Graph(id="main-map", style={'width': '65%', 'display': 'inline-block', 'height': '600px', 'margin-top': '20px', 'border': '1px solid lightgray'})
    ], style={'width': '65%', 'display': 'inline-block', 'vertical-align': 'top'}),

    # Inset maps for Nice and Corsica with consistent margin on top
    html.Div([
        dcc.Graph(id="inset-nice", style={
            'width': '100%', 'height': '300px', 'border': '1px solid lightgray', 'margin-top': '20px'
        }),
        dcc.Graph(id="inset-corsica", style={
            'width': '100%', 'height': '300px', 'border': '1px solid lightgray', 'margin-top': '10px'
        })
    ], style={'position': 'absolute', 'top': '0', 'width': '25%', 'height': '55%', 'left': '65%'}),
])

# Main map plot with highlighted stations from selected criteria (Network, CENALT, or CD06)
@app.callback(
    Output("main-map", "figure"),
    Input("station-select", "value")
)
def update_main_map(selected_criteria):
    if selected_criteria == "RA":
        filtered_df = df[df['Network'] == "RA"]
        filtered_color = "rgb(239,134,54)"
    elif selected_criteria == "FR":
        filtered_df = df[df['Network'] == "FR"]
        filtered_color = "rgb(81,158,62)"
    elif selected_criteria == "CENALT":
        cenalt_stations = ["CALF", "SMPL", "ISO", "ATE"]
        filtered_df = df[df['Station'].isin(cenalt_stations)]
        filtered_color = "rgb(197,58,50)"
    elif selected_criteria == "CD06":
        filtered_df = df[df['Postal'] == "06"]
        filtered_color = "rgb(141,105,184)"
    else:
        filtered_df = df

    # Create the figure
    fig = px.scatter_mapbox(
        df, lat="Latitude", lon="Longitude",
        hover_name="Station", hover_data={'Latitude': False, 'Longitude': False},  # No extra hover data
        zoom=6, height=600
    )

    # Default opacity to 1 for all stations
    opacity = 1 if not selected_criteria else 0.3
    # Update traces to fade unselected stations
    fig.update_traces(marker=dict(size=10, color="rgb(59, 117, 175)", opacity=opacity), showlegend=False)

    # Highlight selected stations with full opacity
    if selected_criteria:
        highlighted_df = filtered_df
        fig.add_scattermapbox(
            lat=highlighted_df['Latitude'], lon=highlighted_df['Longitude'],
            mode='markers', marker=dict(size=10, color=filtered_color, opacity=1),
            hoverinfo="text", text=highlighted_df['Station'], showlegend=False
        )

    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox=dict(center=dict(lat=43.5, lon=6.35), zoom=7),
        margin={"r":0, "t":0, "l":0, "b":0}
    )
    return fig

# Nice inset map (with default color and zoom)
@app.callback(
    Output("inset-nice", "figure"),
    Input("station-select", "value")  # We can use the same selection if highlighting is needed
)
def update_inset_nice(selected_criteria):
    if selected_criteria == "RA":
        filtered_df = df[df['Network'] == "RA"]
        filtered_color = "rgb(239,134,54)"
    elif selected_criteria == "FR":
        filtered_df = df[df['Network'] == "FR"]
        filtered_color = "rgb(81,158,62)"
    elif selected_criteria == "CENALT":
        cenalt_stations = ["CALF", "SMPL", "ISO", "ATE"]
        filtered_df = df[df['Station'].isin(cenalt_stations)]
        filtered_color = "rgb(197,58,50)"
    elif selected_criteria == "CD06":
        filtered_df = df[df['Postal'] == "06"]
        filtered_color = "rgb(141,105,184)"
    else:
        filtered_df = df

    fig = px.scatter_mapbox(
        df, lat="Latitude", lon="Longitude",
        hover_name="Station", hover_data={'Latitude': False, 'Longitude': False},  # No extra hover data
        zoom=10, height=300
    )
    # Default opacity to 1 for all stations
    opacity = 1 if not selected_criteria else 0.3
    # Update all markers to be dimmed (opacity = 0.3)
    fig.update_traces(marker=dict(size=10, color="rgb(59, 117, 175)", opacity=opacity), showlegend=False)

    # Highlight selected stations with full opacity (opacity = 1)
    if selected_criteria:
        highlighted_df = filtered_df
        fig.add_scattermapbox(
            lat=highlighted_df['Latitude'], lon=highlighted_df['Longitude'],
            mode='markers', marker=dict(size=10, color=filtered_color, opacity=1),
            hoverinfo="text", text=highlighted_df['Station'], showlegend=False
        )

    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox=dict(center=dict(lat=43.7, lon=7.257), zoom=10),
        margin={"r":0, "t":0, "l":0, "b":0},
        title="Nice Region"
    )
    return fig

# Corsica inset map (with updated zoom level to 6 and default color)
@app.callback(
    Output("inset-corsica", "figure"),
    Input("station-select", "value")  # We can use the same selection if highlighting is needed
)
def update_inset_corsica(selected_criteria):
    if selected_criteria == "RA":
        filtered_df = df[df['Network'] == "RA"]
        filtered_color = "rgb(239,134,54)"
    elif selected_criteria == "FR":
        filtered_df = df[df['Network'] == "FR"]
        filtered_color = "rgb(81,158,62)"
    elif selected_criteria == "CENALT":
        cenalt_stations = ["CALF", "SMPL", "ISO", "ATE"]
        filtered_df = df[df['Station'].isin(cenalt_stations)]
        filtered_color = "rgb(197,58,50)"
    elif selected_criteria == "CD06":
        filtered_df = df[df['Postal'] == "06"]
        filtered_color = "rgb(141,105,184)"
    else:
        filtered_df = df

    fig = px.scatter_mapbox(
        df, lat="Latitude", lon="Longitude",
        hover_name="Station", hover_data={'Latitude': False, 'Longitude': False},  # No extra hover data
        zoom=6, height=300  # Updated zoom level to 6
    )
    # Default opacity to 1 for all stations
    opacity = 1 if not selected_criteria else 0.3
    # Update all markers to be dimmed (opacity = 0.3)
    fig.update_traces(marker=dict(size=10, color="rgb(59, 117, 175)", opacity=opacity), showlegend=False)

    # Highlight selected stations with full opacity (opacity = 1)
    if selected_criteria:
        highlighted_df = filtered_df
        fig.add_scattermapbox(
            lat=highlighted_df['Latitude'], lon=highlighted_df['Longitude'],
            mode='markers', marker=dict(size=10, color=filtered_color, opacity=1),
            hoverinfo="text", text=highlighted_df['Station'], showlegend=False
        )

    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox=dict(center=dict(lat=42.170, lon=9.105), zoom=6.5),
        margin={"r":0, "t":0, "l":0, "b":0},
        title="Corsica"
    )
    return fig

# Run Dash app
if __name__ == "__main__":
    app.run_server(debug=True)
                                
