import os

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
from dash import html, dash_table, dcc, callback, Input, Output
from dash_ag_grid import AgGrid

from commons import *

graph = load_graph_from_file(os.path.join(RESULTS_PATH, "full_graph"))
node_df, edge_df = graph_to_gdfs(graph)

fig_style = {"margin": DEFAULT_MAPBOX_STYLE["margin"], "mapbox": DEFAULT_MAPBOX_STYLE["mapbox"]}

plot_map_nodes = px.scatter_mapbox(node_df, lat="lat", lon="lon", size="degree",
                                   hover_data=["name", "degree", "centrality"],
                                   zoom=DEFAULT_MAPBOX_STYLE['mapbox']['zoom'], size_max=15,
                                   ).update_layout(fig_style)

node_df_pretty = node_df.drop(columns=["geometry", "lon", "lat"]).reset_index()
node_df_table = AgGrid(rowData=node_df_pretty.to_dict('records'),  # add button to filter some columns
                       columnDefs=[{'field': col} for col in node_df_pretty.columns],
                       defaultColDef={"resizable": True, "sortable": True, "filter": True,
                                      "wrapText": True, 'autoHeight': True,
                                      "wrapHeaderText": True, "autoHeaderHeight": True},
                       columnSize='sizeToFit',
                       id="node_df_table")

layout = dbc.Container(className="fluid", children=[
    html.Center(html.H1("Visualizzazione Stazioni", className="display-3 my-4")),
    dcc.Graph(id="plot_map_nodes", figure=plot_map_nodes),

    html.Br(),
    html.Hr(),
    html.Center(html.H3("Tabella delle stazioni")),
    html.Div(className="my-3", children=[node_df_table]),

])
