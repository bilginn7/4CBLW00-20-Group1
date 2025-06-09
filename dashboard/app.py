import json
import geopandas as gpd
import folium
import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd


JSON_FILE_PATH  = '../data/london_future_predictions.json'
LAD_SHAPE_PATH  = '../data/geo/LAD_shape.parquet'
WARD_SHAPE_PATH = '../data/geo/WARD_shape.parquet'
LSOA_SHAPE_PATH = '../data/geo/LSOA_shape.parquet'
CSS_FILE_PATH   = 'assets/style.css'

with open(JSON_FILE_PATH, 'r') as f:
    london_data = json.load(f)
london_lad_codes = list(london_data.keys())

gdf_lad_all = gpd.read_parquet(LAD_SHAPE_PATH)
london_boroughs_gdf = gdf_lad_all[gdf_lad_all['LAD22CD'].isin(london_lad_codes)].copy()

m = folium.Map(location=[51.5074, -0.1278], zoom_start=11, tiles='CartoDB positron')
folium.GeoJson(
    london_boroughs_gdf,
    style_function=lambda x: {
        'color': 'blue',
        'weight': 2,
        'fillOpacity': 0.1,
        'fillColor': 'lightblue',
        'className': 'borough-polygon'
    },
    highlight_function=lambda x: {
        'weight': 4,
        'color': '#ff4757',
        'fillOpacity': 0.7,
        'fillColor': '#ff6b6b'
    },
    tooltip=folium.GeoJsonTooltip(
        fields=['LAD22NM', 'LAD22CD'],
        aliases=['Borough:', 'Code:'],
        sticky=True,
        labels=True,
        style="""
            background-color: white;
            border: 2px solid black;
            border-radius: 3px;
            box-shadow: 3px;
        """
    )
).add_to(m)

# Get the HTML and inject external CSS
map_html_string = m._repr_html_()

# Read the CSS file
with open(CSS_FILE_PATH, 'r') as f:
    css_content = f.read()

# Inject the CSS into the HTML
css_link = f'<style>{css_content}</style>'
map_html_string = map_html_string.replace('<head>', f'<head>{css_link}')

app = dash.Dash(__name__)
server = app.server

app.layout = html.Div(
    style={
        'display': 'flex',
        'flexDirection': 'column',
        'height': '100vh',
        'width': '100vw',
        'margin': 0,
        'padding': 0,
        'overflow': 'hidden',
        'position': 'fixed',
        'top': 0,
        'left': 0,
    },
    children=[
        html.H1(
            children="London Burglary Predictor",
            style={
                'textAlign': 'center',
                'flex': '0 0 auto',
                'margin': '5px 0',
                'padding': 0,
                'fontSize': '24px',
                'height': '40px',
            }
        ),
        html.Iframe(
            id='map',
            srcDoc=map_html_string,
            style={
                'width': '100%',
                'height': 'calc(100vh - 50px)',
                'border': '5px solid black',
                'flex': '1 1 auto',
                'overflow': 'hidden',
                'margin': 0,
                'padding': 0,
            }
        )
    ]
)

if __name__ == '__main__':
    app.run_server(debug=True)