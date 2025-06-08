import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd


#df = pd.read_csv("")
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H2("London Crime Prediction Tool"),
   
])


   
# extra callbacks for the map…

if __name__ == "__main__":
    app.run_server(debug=True)