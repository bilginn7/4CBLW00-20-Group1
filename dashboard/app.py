"""
London Burglary Predictor Dashboard – Plotly version
----------------------------------------------------
Replaces Folium + <iframe> with Plotly choropleth maps embedded in dcc.Graph.
"""

import os
import json
from datetime import datetime

import dash
from dash import dcc, html, Input, Output, callback

import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ─────────────────────────── FILE PATHS ──────────────────────────── #
JSON_FILE_PATH  = "../data/london_future_predictions.json"
LAD_SHAPE_PATH  = "../data/geo/LAD_shape.parquet"
WARD_SHAPE_PATH = "../data/geo/WARD_shape.parquet"
LSOA_SHAPE_PATH = "../data/geo/LSOA_shape.parquet"
Y_TRAIN_PATH    = "../data/y_train"
Y_TEST_PATH     = "../data/y_test"

# ────────────────────────── LOAD THE DATA ─────────────────────────── #
with open(JSON_FILE_PATH, "r") as f:
    london_data = json.load(f)

gdf_lad_all  = gpd.read_parquet(LAD_SHAPE_PATH)
gdf_ward_all = gpd.read_parquet(WARD_SHAPE_PATH)
gdf_lsoa_all = gpd.read_parquet(LSOA_SHAPE_PATH)

# keep only the boroughs that exist in the JSON
london_lad_codes     = list(london_data.keys())
london_boroughs_gdf  = gdf_lad_all[gdf_lad_all["LAD22CD"].isin(london_lad_codes)].copy()

# convert GeoDataFrames → GeoJSON once (Plotly wants dicts, not strings)
boroughs_geojson = json.loads(london_boroughs_gdf.to_json())
wards_geojson    = json.loads(gdf_ward_all.to_json())
lsoas_geojson    = json.loads(gdf_lsoa_all.to_json())


def load_burglary_data() -> pd.DataFrame:
    """Load y_train/y_test CSVs, tag them, and stack into one DataFrame."""
    all_frames = []
    for root in (Y_TRAIN_PATH, Y_TEST_PATH):
        if not os.path.exists(root):
            continue
        tag = os.path.basename(root).replace("y_", "")  # 'train' or 'test'
        for fn in os.listdir(root):
            if fn.endswith(".csv"):
                df = pd.read_csv(os.path.join(root, fn))
                df["dataset"] = tag
                all_frames.append(df)

    return pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()


burglary_data = load_burglary_data()

# ────────────────────── MAP-BUILDING HELPERS ──────────────────────── #
def create_london_map(height_px: int = 700) -> go.Figure:
    """Show every London borough boundary."""
    fig = px.choropleth_map(
        london_boroughs_gdf,  # now a Mapbox trace
        geojson=boroughs_geojson,
        locations="LAD22CD",
        hover_name="LAD22NM",
        color_discrete_sequence=["rgba(0,0,0,0)"],
        opacity=0.2,
        center=dict(lat=51.5074, lon=-0.1278),
        zoom=9.7,
    )
    fig.update_traces(marker_line_width=2, marker_line_color="blue")

    fig.update_layout(
        mapbox_style="carto-positron",
        height=height_px,
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig


def create_ward_map(ward_code: str | None, height_px: int = 700) -> go.Figure:
    """Ward-focused map: ward boundary in red, its LSOAs in light blue."""
    if not ward_code:
        return create_london_map(height_px)

    ward_poly = gdf_ward_all[gdf_ward_all["WD24CD"] == ward_code]
    if ward_poly.empty:
        return create_london_map(height_px)

    ward_geo = {
        "type": "FeatureCollection",
        "features": json.loads(ward_poly.to_json())["features"],
    }

    # LSOAs that live inside this ward, according to the JSON structure
    ward_lsoas = []
    for lad in london_data.values():
        ward_json = lad.get("wards", {}).get(ward_code)
        if ward_json:
            ward_lsoas = list(ward_json.get("lsoas", {}).keys())
            break

    lsoa_poly = gdf_lsoa_all[gdf_lsoa_all["LSOA21CD"].isin(ward_lsoas)]
    lsoa_geo  = {
        "type": "FeatureCollection",
        "features": json.loads(lsoa_poly.to_json())["features"],
    }

    center_lat = ward_poly.geometry.centroid.y.iloc[0]
    center_lon = ward_poly.geometry.centroid.x.iloc[0]

    # build figure – two choropleth traces so we can colour them separately
    fig = go.Figure()

    # ward boundary (semi-transparent red)
    ward_trace = px.choropleth_map(
        ward_poly,
        geojson=ward_geo,
        locations="WD24CD",
        color_discrete_sequence=["rgba(255,0,0,0.15)"],
    ).data[0]
    ward_trace.marker.line.width = 3
    ward_trace.marker.line.color = "red"
    fig.add_trace(ward_trace)

    # its LSOAs (light-blue fill with blue outline)
    lsoa_trace = px.choropleth_map(
        lsoa_poly,
        geojson=lsoa_geo,
        locations="LSOA21CD",
        color_discrete_sequence=["rgba(0,0,255,0.25)"],
    ).data[0]
    lsoa_trace.marker.line.width = 1
    lsoa_trace.marker.line.color = "blue"
    fig.add_trace(lsoa_trace)

    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_zoom=14,
        mapbox_center=dict(lat=center_lat, lon=center_lon),
        height=height_px,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
    )
    return fig


# ──────────────────────────── DASH APP ────────────────────────────── #
app    = dash.Dash(__name__)
server = app.server  # for gunicorn / render.com deploys, etc.

app.layout = html.Div(
    [
        html.H1(
            "London Burglary Predictor Dashboard",
            style={"textAlign": "center", "margin": "10px 0", "fontSize": "28px"},
        ),
        # ── controls row ───────────────────────────────────────────── #
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Borough:", style={"color": "red", "fontWeight": "bold"}),
                        dcc.Dropdown(
                            id="borough-dropdown",
                            options=[],  # filled by callback
                            placeholder="Select Borough",
                            style={"border": "2px solid red"},
                        ),
                    ],
                    style={"width": "30%", "display": "inline-block", "margin": "0 1.5%"},
                ),
                html.Div(
                    [
                        html.Label("Ward:", style={"color": "red", "fontWeight": "bold"}),
                        dcc.Dropdown(
                            id="ward-dropdown",
                            options=[],
                            placeholder="Select Ward",
                            disabled=True,
                            style={"border": "2px solid red"},
                        ),
                    ],
                    style={"width": "30%", "display": "inline-block", "margin": "0 1.5%"},
                ),
                html.Div(
                    [
                        html.Label("LSOA:", style={"color": "red", "fontWeight": "bold"}),
                        dcc.Dropdown(
                            id="lsoa-dropdown",
                            options=[],
                            placeholder="Select LSOA",
                            disabled=True,
                            style={"border": "2px solid red"},
                        ),
                    ],
                    style={"width": "30%", "display": "inline-block", "margin": "0 1.5%"},
                ),
            ],
            style={"margin": "20px 0", "textAlign": "center"},
        ),
        # ── main row (map + charts) ────────────────────────────────── #
        html.Div(
            [
                # map column
                html.Div(
                    [
                        html.P(
                            "Fixed map based on drop-down menu selection",
                            style={"color": "red", "margin": "5px", "fontSize": "12px"},
                        ),
                        html.P(
                            "Shows fixed ward with the LSOA borders",
                            style={"color": "red", "margin": "5px", "fontSize": "12px"},
                        ),
                        dcc.Graph(
                            id="map",
                            figure=create_london_map(),
                            style={"border": "3px solid black"},
                        ),
                    ],
                    style={"width": "48%", "display": "inline-block", "verticalAlign": "top"},
                ),
                # charts column
                html.Div(
                    [
                        # burglary predictions
                        html.Div(
                            [
                                html.P(
                                    "burglary count per month",
                                    style={"color": "red", "margin": "5px", "fontSize": "12px"},
                                ),
                                dcc.Graph(
                                    id="burglary-count-chart",
                                    style={"height": "180px", "border": "3px solid black"},
                                ),
                            ],
                            style={"marginBottom": "20px"},
                        ),
                        # officers per hour
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.P(
                                            "officers per hour",
                                            style={
                                                "color": "red",
                                                "margin": "5px",
                                                "fontSize": "12px",
                                                "display": "inline-block",
                                            },
                                        ),
                                        html.Div(
                                            [
                                                dcc.Dropdown(
                                                    id="month-dropdown",
                                                    options=[],
                                                    placeholder="Select Month",
                                                    disabled=True,
                                                    style={
                                                        "width": "120px",
                                                        "fontSize": "10px",
                                                        "border": "1px solid red",
                                                    },
                                                )
                                            ],
                                            style={
                                                "display": "inline-block",
                                                "marginLeft": "10px",
                                                "verticalAlign": "top",
                                            },
                                        ),
                                    ]
                                ),
                                html.P(
                                    "barchart",
                                    style={"color": "red", "margin": "5px", "fontSize": "12px"},
                                ),
                                dcc.Graph(
                                    id="officers-chart",
                                    style={"height": "150px", "border": "3px solid black"},
                                ),
                            ]
                        ),
                    ],
                    style={
                        "width": "48%",
                        "display": "inline-block",
                        "verticalAlign": "top",
                        "marginLeft": "4%",
                    },
                ),
            ]
        ),
    ],
    style={"padding": "20px"},
)

# ────────────────────────── CALLBACKS ─────────────────────────────── #
@callback(Output("borough-dropdown", "options"), Input("borough-dropdown", "id"))
def populate_borough_dropdown(_):
    opts = [
        {"label": lad["name"], "value": lad_code}
        for lad_code, lad in london_data.items()
    ]
    return sorted(opts, key=lambda d: d["label"])


@callback(
    Output("map", "figure"),
    Input("ward-dropdown", "value"),
)
def update_map(selected_ward):
    return create_ward_map(selected_ward)


@callback(
    [
        Output("ward-dropdown", "options"),
        Output("ward-dropdown", "disabled"),
        Output("ward-dropdown", "value"),
    ],
    Input("borough-dropdown", "value"),
)
def update_ward_dropdown(selected_borough):
    if not selected_borough:
        return [], True, None

    wards = london_data[selected_borough]["wards"]
    opts  = [{"label": w["name"], "value": code} for code, w in wards.items()]
    return sorted(opts, key=lambda d: d["label"]), False, None


@callback(
    [
        Output("lsoa-dropdown", "options"),
        Output("lsoa-dropdown", "disabled"),
        Output("lsoa-dropdown", "value"),
    ],
    [Input("ward-dropdown", "value"), Input("borough-dropdown", "value")],
)
def update_lsoa_dropdown(selected_ward, selected_borough):
    if not selected_ward or not selected_borough:
        return [], True, None

    lsoas = london_data[selected_borough]["wards"][selected_ward]["lsoas"]
    opts  = [{"label": l["name"], "value": code} for code, l in lsoas.items()]
    return sorted(opts, key=lambda d: d["label"]), False, None


@callback(
    [
        Output("month-dropdown", "options"),
        Output("month-dropdown", "disabled"),
        Output("month-dropdown", "value"),
    ],
    [
        Input("lsoa-dropdown", "value"),
        Input("ward-dropdown", "value"),
        Input("borough-dropdown", "value"),
    ],
)
def update_month_dropdown(selected_lsoa, selected_ward, selected_borough):
    if not (selected_lsoa and selected_ward and selected_borough):
        return [], True, None

    hourly = (
        london_data[selected_borough]["wards"][selected_ward]["lsoas"][selected_lsoa]
        .get("officer_assignments", {})
        .get("hourly", {})
    )
    if not hourly:
        return [], True, None

    months = sorted(hourly.keys())
    opts   = [{"label": m, "value": m} for m in months]
    return opts, False, months[-1]


@callback(
    Output("burglary-count-chart", "figure"),
    [
        Input("lsoa-dropdown", "value"),
        Input("ward-dropdown", "value"),
        Input("borough-dropdown", "value"),
    ],
)
def update_burglary_chart(selected_lsoa, selected_ward, selected_borough):
    if not (selected_lsoa and selected_ward and selected_borough):
        return _empty_chart("Select Borough, Ward, and LSOA to view data", 14)

    preds = (
        london_data[selected_borough]["wards"][selected_ward]["lsoas"][selected_lsoa]
        .get("predictions", {})
    )
    if not preds:
        return _empty_chart("No prediction data available", 14)

    dates, values = list(preds.keys()), list(preds.values())
    fig = go.Figure(
        go.Scatter(
            x=dates,
            y=values,
            mode="lines+markers",
            line=dict(color="black", width=3),
            marker=dict(size=6),
        )
    )
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Predicted Burglaries",
        plot_bgcolor="white",
        margin=dict(l=40, r=20, t=20, b=40),
        showlegend=False,
    )
    return fig


@callback(
    Output("officers-chart", "figure"),
    [
        Input("month-dropdown", "value"),
        Input("lsoa-dropdown", "value"),
        Input("ward-dropdown", "value"),
        Input("borough-dropdown", "value"),
    ],
)
def update_officers_chart(selected_month, selected_lsoa, selected_ward, selected_borough):
    if not (selected_month and selected_lsoa and selected_ward and selected_borough):
        return _empty_chart("Select Borough, Ward, LSOA, and Month to view data", 12)

    hourly = (
        london_data[selected_borough]["wards"][selected_ward]["lsoas"][selected_lsoa]
        .get("officer_assignments", {})
        .get("hourly", {})
    )
    if selected_month not in hourly:
        return _empty_chart("No officer assignment data for selected month", 12)

    y = hourly[selected_month]
    fig = go.Figure(
        go.Bar(
            x=list(range(24)),
            y=y,
            marker_color="red",
            marker_line_color="darkred",
            marker_line_width=1,
        )
    )
    fig.update_layout(
        title=f"Officers per Hour ({selected_month})",
        xaxis_title="Hour of Day",
        yaxis_title="Number of Officers",
        plot_bgcolor="white",
        margin=dict(l=40, r=20, t=40, b=40),
        showlegend=False,
        title_font_size=12,
        xaxis=dict(tickmode="linear", tick0=0, dtick=2),
    )
    return fig


# ──────────────────────── HELPER FUNCTIONS ───────────────────────── #
def _empty_chart(msg: str, font_size: int) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=msg,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        xanchor="center",
        yanchor="middle",
        showarrow=False,
        font=dict(size=font_size),
    )
    fig.update_layout(
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=20, b=20),
    )
    return fig


# ────────────────────────── MAIN ──────────────────────────────────── #
if __name__ == "__main__":
    # If you use a private Mapbox token, uncomment the line below.
    # px.set_mapbox_access_token("YOUR_MAPBOX_TOKEN_HERE")
    app.run_server(debug=True)
