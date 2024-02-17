import os

import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.express as px
from dash import html, dash_table, dcc, callback, Input, Output, State, dash
from dash_ag_grid import AgGrid

from commons import *

graph = load_graph_from_file(os.path.join(RESULTS_PATH, "full_graph"))
node_df, edge_df = graph_to_gdfs(graph)

fig_style = {"margin": DEFAULT_MAPBOX_STYLE["margin"], "mapbox": DEFAULT_MAPBOX_STYLE["mapbox"]}

plot_map_nodes = px.scatter_mapbox(node_df, lat="lat", lon="lon",
                                   hover_data=["name", "degree", "centrality"],
                                   zoom=DEFAULT_MAPBOX_STYLE['mapbox']['zoom'], size_max=15,
                                   color_continuous_scale="Bluered", size="degree", color="centrality",
                                   ).update_layout(fig_style)

node_df_pretty = prettify_node_df(node_df.drop(columns=["geometry", "lon", "lat"])).drop(columns=["Boarding Cost"])

def_col_def = {"resizable": True, "sortable": True, "filter": True, "wrapText": True, 'autoHeight': True,
               "wrapHeaderText": True, "autoHeaderHeight": True}

scaled_cols = ['Name', 'Degree', 'Cent'] + ['Cent Degree R', 'Cent Betweenness R', 'Cent Closeness R',
                                            'Cent Eigenvector R', 'Cent Clustering R', 'Cent Pagerank R']

no_scaled_cols = ['Name', 'Degree', 'Cent'] + ['Cent Degree', 'Cent Betweenness', 'Cent Closeness', 'Cent Eigenvector',
                                               'Cent Clustering', 'Cent Pagerank']

node_df_table_ns = AgGrid(rowData=node_df_pretty[no_scaled_cols].reset_index(drop=True).to_dict('records'),
                          columnDefs=[{'field': col} for col in node_df_pretty[no_scaled_cols].columns],
                          id="node_df_table_ns", dashGridOptions={'alignedGrids': ['node_df_table_s']},
                          defaultColDef=def_col_def, columnSize="responsiveSizeToFit")

node_df_table_s = AgGrid(rowData=node_df_pretty[scaled_cols].reset_index(drop=True).to_dict('records'),
                         columnDefs=[{'field': col} for col in node_df_pretty[scaled_cols].columns],
                         id="node_df_table_s", dashGridOptions={'alignedGrids': ['node_df_table_ns']},
                         defaultColDef=def_col_def, columnSize="responsiveSizeToFit")

layout = dbc.Container(className="fluid", children=[
    html.Center(html.H1("Visualizzazione Stazioni", className="display-3 my-4")),
    dcc.Graph(id="plot_map_nodes", figure=plot_map_nodes),
    html.Br(),
    html.Hr(),
    html.Center(html.H3("Tabella delle stazioni")),
    html.Div(dmc.Switch(id="node_df_table_switch", label="Usa statistiche scalate", color="blue"),
             className="d-flex justify-content-end"),
    html.Div(className="my-3", children=node_df_table_ns, id="node_df_table"),

])


@callback(Output("node_df_table", "children"),
          Input("node_df_table_switch", "checked"), prevent_initial_call=True)
def node_df_table_update_hide_columns(checked):
    return node_df_table_s if checked else node_df_table_ns
