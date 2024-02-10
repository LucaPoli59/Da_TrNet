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
from plotly.subplots import make_subplots

CWD = os.getcwd()
DATA_PATH = os.path.join(CWD, 'data')
GTFS_PATH_IT = os.path.join(DATA_PATH, 'gtfs_it')
GTFS_PATH_UK = os.path.join(DATA_PATH, 'gtfs_uk')
GTFS_PATH_OTHER = os.path.join(DATA_PATH, 'gtfs_other')
RESULTS_PATH = os.path.join(DATA_PATH, 'output')
ATTACKS_PATH = os.path.join(RESULTS_PATH, 'attacks')

########################################################################################
################### General Functions ##################################################
########################################################################################

def load_graph(src=GTFS_PATH_OTHER, feed_id=1139, feed_name="DB", start_time=7, end_time=20):
    feed_path = os.path.join(src, f'{feed_id}.zip')
    feed = ptr.get_representative_feed(feed_path)
    graph = ptr.load_feed_as_graph(feed, start_time=start_time * 3600, end_time=end_time * 3600, name=feed_name)
    return graph


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


########################################################################################
################### Plotting Functions #################################################
########################################################################################

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


########################################################################################
################### Graph Evaluation ###################################################
########################################################################################

def load_node_df(graph):
    node_df = pd.DataFrame.from_dict(dict(graph.nodes(data=True)), orient='index')['boarding_cost'].to_frame()
    node_df.index.name = 'node_id'
    return node_df


def nodes_centrality_evaluation(graph, node_df):
    """
    Function to evaluate the centrality of nodes in a graph
    """
    # Degree
    node_df['degree'] = pd.DataFrame(nx.degree(graph), columns=['node', 'degree']).set_index('node')['degree']

    # Centrality
    centrality_columns = ['centrality_degree', 'centrality_betweenness', 'centrality_closeness',
                          'centrality_eigenvector', "centrality_clustering", "centrality_pagerank"]

    weight = "length"

    node_df['centrality_degree'] = node_df['degree'] / node_df['degree'].max()
    node_df['centrality_betweenness'] = nx.betweenness_centrality(graph, weight=weight)
    node_df['centrality_closeness'] = nx.closeness_centrality(graph, distance=weight)
    node_df['centrality_eigenvector'] = nx.eigenvector_centrality_numpy(graph, weight=weight)
    node_df['centrality_clustering'] = nx.clustering(nx.DiGraph(graph), weight=weight)
    node_df['centrality_pagerank'] = nx.pagerank(graph, weight=weight)

    # Centrality scaling
    for centrality in centrality_columns:
        node_df[centrality + "_scaled"] = node_df[centrality] / node_df[centrality].max()

    centrality_columns_scaled = [centrality + "_scaled" for centrality in centrality_columns]

    # Centrality correlation
    centrality_corr = node_df[centrality_columns].corr()
    centrality_corr_mean = centrality_corr.map(lambda x: np.NAN if x == 1 else x).mean(skipna=True)

    node_df['centrality'] = np.average(node_df[centrality_columns_scaled].values, axis=1,
                                       weights=abs(1 - centrality_corr_mean))

    return node_df


def evaluate_graph(graph, node_df=None):
    """
    Function to evaluate a graph and return summary statistics, and node dataframe characteristics

    summarize the computations done in graph_evaluation.ipynb
    """

    # Extraction of nodes
    if node_df is None:
        node_df = load_node_df(graph)

    # Evaluation of centrality
    node_df = nodes_centrality_evaluation(graph, node_df)

    # Graph global measures
    graph_global_measures = pd.Series({
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "density": nx.density(graph),
        "strong_GC": len(sorted((nx.strongly_connected_components(graph)), key=len, reverse=True)[0]) / len(
            graph.nodes),
        "weak_GC": len(sorted((nx.weakly_connected_components(graph)), key=len, reverse=True)[0]) / len(graph.nodes),
        "avg_degree": node_df['degree'].mean(),
        "global_c_mean": node_df['centrality'].mean(),
        "global_cd_mean": node_df['centrality_degree'].mean(),
        "global_cb_mean": node_df['centrality_betweenness'].mean(),
        "global_cc_mean": node_df['centrality_closeness'].mean(),
        "global_ce_mean": node_df['centrality_eigenvector'].mean(),
        "global_ccc_mean": node_df['centrality_clustering'].mean(),
        "global_cp_mean": node_df['centrality_pagerank'].mean()
    }, name="global_measures")

    return graph_global_measures, node_df


########################################################################################
################### Graph Attack #######################################################
########################################################################################

def attack_graph(graph_in, target=None, n_steps=10):
    graph = graph_in.copy()
    graph_stats, node_df = evaluate_graph(graph)
    total_nodes = graph_stats['nodes']
    amount = int(total_nodes / (n_steps - 1))

    results = {'100%': graph_stats.values}
    for i in range(n_steps - 2):
        if target is None:
            nodes_to_drop = node_df.sample(amount).index  # random nodes
        else:
            nodes_to_drop = node_df.sort_values(target, ascending=False).head(
                amount).index  # nodes with the highest target value
        for node_to_drop in nodes_to_drop:
            graph.remove_node(node_to_drop)

        graph_stats, node_df = evaluate_graph(graph)
        curr_nodes = graph_stats['nodes']
        row_name = str(100 - int((total_nodes - curr_nodes) / total_nodes * 100)).zfill(3) + '%'
        results[row_name] = graph_stats.values

    results = pd.DataFrame(results).transpose().rename(
        columns={i: col for i, col in enumerate(graph_stats.index)}).fillna(0)
    return results


def plot_attack_result(results, title, cols_to_plot=None):
    if cols_to_plot is None:
        cols_to_plot = ['edges', 'density', 'strong_GC', 'weak_GC', 'global_c_mean', 'avg_degree']
    elif (len(cols_to_plot) % 2) != 0:
        raise ValueError('cols_to_plot must have an even number of elements')

    full_fig = make_subplots(rows=int(len(cols_to_plot)/2), cols=2, subplot_titles=cols_to_plot, shared_xaxes=True)
    for i, col in enumerate(cols_to_plot):
        full_fig.add_trace(go.Scatter(x=results.index, y=results[col], mode='markers+lines', name=col, hoverinfo="y"), row=i//2 + 1, col=i%2 + 1)

    full_fig.update_layout(title=title, showlegend=False, title_xanchor="center",
                           title_yanchor="top", title_y=0.9, title_x=0.5)

    results_scaled = results[cols_to_plot] / results[cols_to_plot].max()
    scaled_fig = px.line(results_scaled, x=results_scaled.index, y=results_scaled.columns, title=title
                         ).update_layout(title_xanchor="center", title_yanchor="top", title_y=0.9, title_x=0.5)

    return full_fig, scaled_fig
