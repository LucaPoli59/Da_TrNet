import os

import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.express as px
from dash import html, dash_table, dcc, callback, Input, Output, State, dash, callback_context
from dash_ag_grid import AgGrid

from commons import *

n_steps = ATTACKS_STEPS
nodes_lowerbound = ATTACKS_NODE_LOWERBOUND
total_nodes = load_graph_from_file(os.path.join(RESULTS_PATH, "full_graph")).number_of_nodes()
attacks_types = ["random", "centrality", "centrality_degree", "centrality_betweenness", "centrality_closeness",
                 "centrality_eigenvector", "centrality_clustering", "centrality_pagerank"]
attacks_results = {attack: pd.read_csv(os.path.join(ATTACKS_PATH, f"{attack}_{n_steps}.csv"), index_col=0)
                   for attack in attacks_types}

sum_cols = attacks_results[attacks_types[0]].columns[3:-1]
sum_cols_labels = prettify_graph_stats_columns(attacks_results[attacks_types[0]].copy()).columns[3:-1]
sum_cols_opt = {col: {"value": col, "label": label.replace("Centrality", "Cent.").replace("Mean", "M.").replace(
    "Giant Component", "G.C.")} for col, label in zip(sum_cols, sum_cols_labels)}

layout = dbc.Container(className="fluid", children=[
    html.Center(html.H1("Attacks Analysis", className="display-3 my-4")),
    html.Center(html.H3("Analisi per ogni tipo di attacco")),
    dmc.SegmentedControl(value=attacks_types[0], id="attack_selector", orientation="horizontal", color="red",
                         fullWidth=True, data=[{"value": attack, "label": attack.replace("_", " ").title()}
                                               for attack in attacks_types], className="mt-3"),
    html.Div(className="my-3", children=[dcc.Graph(id="single_results_subplots")]),
    html.Div(className="my-3", children=[dcc.Graph(id="single_results_summary")]),

    html.Br(),
    html.Center(html.H3("Analisi riassuntiva")),
    dmc.SegmentedControl(value=list(sum_cols_opt.values())[0]['value'], id="summary_col_selector", fullWidth=True,
                         orientation="horizontal", color="red", data=list(sum_cols_opt.values()), className="mt-5"),
    html.Center(html.Div(className="d-inline-flex my-3 gap-3 align-items-center", children=[
        html.Label("Threshold:"),
        dbc.Input(id="threshold_input_pct", type="number", min=1, max=100,
                  placeholder="Percent", step=0.01),
        dbc.Tooltip("Inserire la percentuale del valore massimo del parametro selezionato",
                    target="threshold_input_pct", placement="top", style={"font-size": "0.6rem"}),
        dbc.Input(id="threshold_input_abs", type="number", min=0, max=1, placeholder="Abs",
                  step=0.00001, html_size=30),
        dbc.Tooltip("Inserire il valore assoluto del parametro selezionato",
                    target="threshold_input_abs", placement="top", style={"font-size": "0.6rem"}),
        dbc.Button("Aggiorna", id="summary_threshold_button", color="primary")
    ])),
    html.Div(className="my-3", children=[dcc.Graph(id="summary_barplot")]),
    html.Div(className="my-3", children=[dcc.Graph(id="summary_lineplot")]),

])


@callback(Output("single_results_subplots", "figure"), Output("single_results_summary", "figure"),
          Input("attack_selector", "value"))
def update_attack_results_graphs(attack_type):
    fig_subplots, fig_summary = plot_attack_result(attacks_results[attack_type], prettify=True,
                                                   title=f'{attack_type.title()} Attack results')
    return fig_subplots, fig_summary


def _threashold_pct_to_abs(threshold, summary_col):
    return round(threshold / 100 * attacks_results[attacks_types[0]][summary_col].values[0], 5)


def _threashold_abs_to_pct(threshold, summary_col):
    return round(threshold / attacks_results[attacks_types[0]][summary_col].values[0] * 100, 2)


@callback(Output("summary_barplot", "figure", allow_duplicate=True),
          Output("summary_lineplot", "figure", allow_duplicate=True),
          Output("threshold_input_pct", "value", allow_duplicate=True),
          Output("threshold_input_abs", "value", allow_duplicate=True),
          Input("summary_col_selector", "value"), prevent_initial_call='initial_duplicate')
def update_summary_graphs(summary_col):
    def_threshold = 5
    threshold_abs = _threashold_pct_to_abs(def_threshold, summary_col)

    title_bar = f'Dead Timestep per ogni tipo di attacco con {sum_cols_opt[summary_col]["label"]}'
    title_line = f'Variazione del parametro {sum_cols_opt[summary_col]["label"]} per ogni tipo di attacco'

    _, _, fig_bar, fig_line = attacks_results_summary(list(attacks_results.values()), summary_col=summary_col,
                                                      total_nodes=total_nodes, attack_nodes_lowerbound=nodes_lowerbound,
                                                      n_steps=n_steps, title=(title_bar, title_line),
                                                      threshold=threshold_abs)
    return fig_bar, fig_line, def_threshold, threshold_abs


@callback(Output("threshold_input_pct", "value", allow_duplicate=True),
          Output("threshold_input_abs", "value", allow_duplicate=True),
          Input("threshold_input_pct", "value"), Input("threshold_input_abs", "value"),
          State("summary_col_selector", "value"), prevent_initial_call=True)
def update_threshold_input_pct_abs(threshold_pct, threshold_abs, summary_col):
    if callback_context.triggered_id == "threshold_input_pct":
        if threshold_pct is None:
            return threshold_pct, dash.no_update
        return threshold_pct, _threashold_pct_to_abs(threshold_pct, summary_col)

    if threshold_abs is None:
        return dash.no_update, dash.no_update
    return _threashold_abs_to_pct(threshold_abs, summary_col), threshold_abs


@callback(Output("summary_barplot", "figure", allow_duplicate=True),
          Output("summary_lineplot", "figure", allow_duplicate=True),
          Output("threshold_input_pct", "value", allow_duplicate=True),
          Output("threshold_input_abs", "value", allow_duplicate=True),
          Input("summary_threshold_button", "n_clicks"), State("threshold_input_pct", "value"),
          State("threshold_input_abs", "value"), State("summary_col_selector", "value"), prevent_initial_call=True)
def update_summary_graphs_with_threshold(_, threshold_pct, threshold_abs, summary_col):
    if threshold_abs is None:
        if threshold_pct is None:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        threshold_abs = _threashold_pct_to_abs(threshold_pct, summary_col)

    if threshold_pct is None:
        threshold_pct = _threashold_abs_to_pct(threshold_abs, summary_col)

    title = f'Dead Timestep per ogni tipo di attacco con {sum_cols_opt[summary_col]["label"]}'

    _, _, fig_bar, fig_line = attacks_results_summary(list(attacks_results.values()), summary_col=summary_col,
                                                      total_nodes=total_nodes, attack_nodes_lowerbound=nodes_lowerbound,
                                                      n_steps=n_steps, title=title, threshold=threshold_abs)
    return fig_bar, fig_line, threshold_pct, threshold_abs
