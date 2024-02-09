import pandas as pd
import numpy as np
import os
import partridge as ptg
import peartree as ptr
import plotly.express as px
import networkx as nx
import datetime as dt
import networkx as nx
import osmnx as ox
import plotly.graph_objects as go


def pad_array(array, pad_val=None, step=1, n_pads=1):
    """Pads an array with a value (repeated for n_pads) every n steps"""
    dim_multiplayer = (step + n_pads) / step
    if not round(len(array) * dim_multiplayer, 3).is_integer():
        raise ValueError(
            f"The step and n_nones combination is not valid : {len(array) * dim_multiplayer} / step must be an integer.")
    output = np.array([pad_val] * int(len(array) * dim_multiplayer))
    for i in range(step):
        output[i::step + n_pads] = array[i::step]
    return output


def graph_to_dfs(g):
    nodes, edges = ox.graph_to_gdfs(g)
    nodes = nodes.rename(columns={"x": "lon", "y": "lat"})
    nodes.index.name = "name"

    edges = edges.rename(columns={"u": "from", "v": "to"})
    return nodes, edges


def linestring_to_coords(linestring, dim):
    lat, long = linestring.xy
    return [np.linspace(lat[0], lat[1], dim + 2)[1:-1], np.linspace(long[0], long[1], dim + 2)[1:-1]]


def plot_graph_map(g, marker_style=None, num_edge_markers=0, **fig_style_kwargs):
    if marker_style is None:
        marker_style = dict(size=10, color="red")
    if "margin" not in fig_style_kwargs.keys():
        fig_style_kwargs["margin"] = {'l': 0, 't': 0, 'b': 0, 'r': 0}
    if "mapbox" not in fig_style_kwargs.keys():
        fig_style_kwargs["mapbox"] = {'style': "open-street-map", 'zoom': 2}

    nodes, edges = graph_to_dfs(g)
    nodes_dict = nodes[["lon", "lat"]].reset_index().to_dict(orient="list")
    nodes_names, nodes_lats, nodes_longs = nodes_dict["name"], nodes_dict["lat"], nodes_dict["lon"]

    edges.index = edges.index.droplevel(2).map(
        lambda index: index[0].replace("DB_", "") + "-TO-" + index[1].replace("DB_", "")).values
    edges.index.name = "name"
    edges_coords = edges['geometry'].to_frame().apply(lambda row: row.iloc[0].xy, axis=1,
                                                      result_type="expand").reset_index().rename(
        columns={0: "lon", 1: "lat"})
    edges_longs, edges_lats = pad_array(np.concatenate(edges_coords['lon'].values), step=2), pad_array(
        np.concatenate(edges_coords['lat'].values), step=2)

    fig = go.Figure()

    fig.add_trace(go.Scattermapbox(  # add edges
        mode="lines",
        lon=edges_longs,
        lat=edges_lats,
    ))

    if num_edge_markers != 0:
        edges_markers = edges['geometry'].to_frame().apply(
            lambda row: linestring_to_coords(row.iloc[0], num_edge_markers), axis=1, result_type="expand"
            ).reset_index().rename(columns={0: "lon", 1: "lat"})
        edges_longs_marker = pad_array(np.concatenate(edges_markers['lon'].values), step=num_edge_markers)
        edges_lats_marker = pad_array(np.concatenate(edges_markers['lat'].values), step=num_edge_markers)
        edges_text_marker = pad_array(edges.index.values.repeat(num_edge_markers), step=num_edge_markers)

        fig.add_trace(go.Scattermapbox(
            mode="markers",
            lon=edges_longs_marker,
            lat=edges_lats_marker,
            hoverinfo="text",
            text=edges_text_marker,
            marker=dict(color="rgba(0, 0, 0, 0.0)"),
            name="edges_markers")
        )

    fig.add_trace(go.Scattermapbox(
        mode="markers",
        lon=nodes_longs,
        lat=nodes_lats,
        hoverinfo="text",
        text=nodes_names,
        marker=marker_style)
    )

    fig.update_layout(showlegend=False)
    fig.update_layout(fig_style_kwargs)
    return fig


def evaluate_graph(graph):
    """
    Function to evaluate a graph and return summary statistics, and node dataframe characteristics

    summarize the computations done in graph_evaluation.ipynb
    """
    # Extraction of nodes
    node_df = pd.DataFrame.from_dict(dict(graph.nodes(data=True)), orient='index')['boarding_cost'].to_frame()
    node_df.index.name = 'node_id'

    # Degree
    node_df['degree'] = pd.DataFrame(nx.degree(graph), columns=['node', 'degree']).set_index('node')['degree']

    # Centrality
    centrality_columns = ['centrality_degree', 'centrality_betweenness', 'centrality_closeness', 'centrality_eigenvector']
    weight = "length"

    node_df['centrality_degree'] = node_df['degree'] / node_df['degree'].max()
    node_df['centrality_betweenness'] = nx.betweenness_centrality(graph, weight=weight)
    node_df['centrality_closeness'] = nx.closeness_centrality(graph, distance=weight)
    node_df['centrality_eigenvector'] = nx.eigenvector_centrality_numpy(graph, weight=weight)

    # Centrality scaling
    for centrality in centrality_columns:
        node_df[centrality] = (node_df[centrality] - node_df[centrality].min()) / (node_df[centrality].max() - node_df[centrality].min())

    # Centrality correlation
    centrality_corr = node_df[centrality_columns].corr()
    centrality_corr_mean = centrality_corr.map(lambda x: np.NAN if x == 1 else x).mean(skipna=True)

    node_df['centrality'] = np.average(node_df[centrality_columns].values, axis=1, weights=abs(1- centrality_corr_mean))

    # Graph global measures
    graph_global_measures = pd.Series({
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "density": nx.density(graph),
        "strong_GC": len(sorted((nx.strongly_connected_components(graph)), key=len, reverse=True)[0]) / len(graph.edges),
        "weak_GC": len(sorted((nx.weakly_connected_components(graph)), key=len, reverse=True)[0]) / len(graph.edges),
        "centrality_mean": node_df['centrality'].mean()
    }, name="global_measures")

    return graph_global_measures, node_df


CWD = os.getcwd()
DATA_PATH = os.path.join(CWD, 'data')
GTFS_PATH = os.path.join(DATA_PATH, 'gtfs')
GTFS_PATH_UK = os.path.join(DATA_PATH, 'gtfs_uk')
GTFS_PATH_OTHER = os.path.join(DATA_PATH, 'gtfs_other')
