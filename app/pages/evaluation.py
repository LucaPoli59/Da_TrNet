import os

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
from dash import html, dash_table, dcc, callback, Input, Output
from dash_ag_grid import AgGrid

from commons import *

graph_stats = pd.read_csv(os.path.join(RESULTS_PATH, "graph_stats.csv"), index_col="metric")
graph = load_graph_from_file(os.path.join(RESULTS_PATH, "full_graph"))
node_df, edge_df = graph_to_gdfs(graph)
centrality_columns = ['centrality_degree', 'centrality_betweenness', 'centrality_closeness', 'centrality_eigenvector',
                      "centrality_clustering", "centrality_pagerank"]

centrality_summary_fig = make_subplots(rows=int(len(centrality_columns) / 2), cols=2,
                                       subplot_titles=("Degree", "Betweenness", "Closeness", "Eigenvector",
                                                       "Clustering", "PageRank"))
for i, centrality in enumerate(centrality_columns):
    centrality_summary_fig.add_trace(go.Histogram(x=node_df[centrality], histfunc="count",
                                                  histnorm='probability density', hoverinfo='x'),
                                     row=(i // 2) + 1, col=(i % 2) + 1)

centrality_summary_fig.update_layout(title_text="Centrality Distribution", showlegend=False,
                                     title_xanchor="center", title_yanchor="top", title_y=0.9, title_x=0.5)

centrality_corr = node_df[centrality_columns].corr()
# centrality_corr.style.background_gradient(cmap='coolwarm', axis=None)

centrality_summary = centrality_corr.map(lambda x: np.NAN if x == 1 else x).mean(skipna=True).to_frame(name="corr_mean")
for stats in ['mean', 'std', '25%', '50%', '75%']:
    centrality_summary[stats] = node_df[centrality_columns].describe().loc[stats]

centrality_summary.index = centrality_summary.index.str.replace('centrality_', '')
centrality_summary = centrality_summary.round(5)


graph_stats_table = dbc.Table.from_dataframe(graph_stats.reset_index(), bordered=True, hover=True, responsive=True,
                                             striped=True, size="sm")

centrality_summary_table = dbc.Table.from_dataframe(centrality_summary.reset_index(), bordered=True, hover=True,
                                                    responsive=True, striped=True, size="sm")


layout = dbc.Container(className="fluid", children=[
    html.Center(html.H1("Graph Evaluation", className="display-3 my-4")),
    html.Center(html.H3("Caratteristiche generali del grafo")),
    html.Div(className="my-3", children=[graph_stats_table]),
    html.Center(html.H3("Distribuzione del grado dei nodi", className="mt-5")),
    html.Div(className="my-3", children=[
        dcc.Graph(figure=px.histogram(node_df, x='degree',
                                      histfunc="count", histnorm='probability density', marginal="box"))
    ]),
    html.Center(html.H3("Analisi Centrality metrics", className="mt-5")),
    html.Div(className="my-3", children=[
        dcc.Graph(figure=centrality_summary_fig)
    ]),
    html.Center(html.H5("Tabella correlazione tra le metriche di centralità", className="mt-5")),
    html.Div(className="my-3", children=[dcc.Graph(figure=px.imshow(centrality_corr))]),

    html.Center(html.H5("Tabella riassuntiva delle metriche di centralità", className="mt-5")),
    html.Div(className="my-3", children=[centrality_summary_table]),

])
