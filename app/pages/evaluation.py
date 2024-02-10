import os

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
from dash import html, dash_table, dcc, callback, Input, Output
from dash_ag_grid import AgGrid


layout = dbc.Container(className="fluid", children=[
    html.Center(html.H1("", className="display-3 my-4")),


])
