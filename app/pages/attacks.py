import os

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
from dash import html, dash_table, dcc, callback, Input, Output
from dash_ag_grid import AgGrid

from commons import *

n_steps = 20
attacks_types = ["random", "centrality", "centrality_degree", "centrality_betweenness", "centrality_closeness",
                 "centrality_eigenvector", "centrality_pagerank"]
attacks_results = {attack: pd.read_csv(os.path.join(ATTACKS_PATH, f"{attack}_{n_steps}.csv"), index_col=0)
                   for attack in attacks_types}

summary_col_options = attacks_results[attacks_types[0]].columns[3:-1]

print(summary_col_options, "\n\n")


layout = dbc.Container(className="fluid", children=[
    html.Center(html.H1("Attacks Analysis", className="display-3 my-4")),
    html.Center(html.H3("Analisi per ogni attacco")),
    dbc.Select(attacks_types, value=attacks_types[0], id="attack_selector",
               className="date-group-items justify-content-center mt-4"),
    html.Div(className="my-3", children=[dcc.Graph(id="single_results_subplots")]),
    html.Div(className="my-3", children=[dcc.Graph(id="single_results_summary")]),

    html.Br(),
    html.Center(html.H3("Analisi riassuntiva")),
    dbc.Select(summary_col_options, value=summary_col_options[0], id="summary_col_selector",
               className="date-group-items justify-content-center mt-4"),
    html.Div(className="my-3", children=[dcc.Graph(id="summary_barplot")]),
    html.Div(className="my-3", children=[dcc.Graph(id="summary_lineplot")]),

])


@callback([Output("single_results_subplots", "figure"), Output("single_results_summary", "figure")],
              [Input("attack_selector", "value")])
def update_attack_results_graphs(attack_type):
    fig_subplots, fig_summary = plot_attack_result(attacks_results[attack_type],
                                                   f'{attack_type.upper()} Attack results')
    return fig_subplots, fig_summary


@callback([Output("summary_barplot", "figure"), Output("summary_lineplot", "figure")],
                [Input("summary_col_selector", "value")])
def update_summary_graphs(summary_col):
    _, _, fig_bar, fig_line = attacks_results_summary(list(attacks_results.values()), summary_col=summary_col)
    return fig_bar, fig_line


