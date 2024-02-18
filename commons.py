import pandas as pd
import numpy as np
import os
import partridge as ptg
import peartree as ptr
import plotly.express as px
import networkx as nx
import datetime as dt
import osmnx as ox
from fiona.crs import CRS
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from io import StringIO

PROJECT_NAME = "data_analytics2"
PROJECT_PATH = os.getcwd()
while os.path.basename(os.getcwd()) != PROJECT_NAME:
    os.chdir("..")
    PROJECT_PATH = os.getcwd()

DATA_PATH = os.path.join(PROJECT_PATH, 'data')
GTFS_PATH_IT = os.path.join(DATA_PATH, 'gtfs_it')
GTFS_PATH_UK = os.path.join(DATA_PATH, 'gtfs_uk')
GTFS_PATH_OTHER = os.path.join(DATA_PATH, 'gtfs_other')

APP_PATH = os.path.join(PROJECT_PATH, "app")
RESULTS_PATH = os.path.join(APP_PATH, 'data')
ATTACKS_PATH = os.path.join(RESULTS_PATH, 'attacks')
USERS_PATH = os.path.join(RESULTS_PATH, 'users')

EDGE_NAME_MID_TOKEN = "<-TO->"
DEFAULT_MAPBOX_STYLE = dict(nodes=dict(size=4, color="#ec4540"), edges=dict(width=1, color="#697bf4"),
                            margin={'l': 0, 't': 0, 'b': 0, 'r': 0},
                            mapbox={'style': "open-street-map", 'zoom': 4,
                                    'center': {'lat': 49.025284, 'lon': 12.0}})

ATTACKS_NODE_LOWERBOUND = 0.1
ATTACKS_STEPS = 30


########################################################################################
################### General Functions ##################################################
########################################################################################

def load_graph_from_feed(src=GTFS_PATH_OTHER, feed_id=1139, feed_name="DB", start_time=7, end_time=20):
    feed_path = os.path.join(src, f'{feed_id}.zip')
    feed = ptr.get_representative_feed(feed_path)
    graph = ptr.load_feed_as_graph(feed, start_time=start_time * 3600, end_time=end_time * 3600, name=feed_name)
    return graph


def graph_to_gdfs(g):
    """Converts a graph to nodes and edges GeoDataFrames.
    Note: is not resilient to empty graphs, which can be returned by OSMnx for example.
    """
    nodes, edges = ox.graph_to_gdfs(g)
    nodes = nodes.rename(columns={"x": "lon", "y": "lat"}).drop(columns=["modes"])
    nodes.index.name = "node_id"

    edges = edges.drop(columns=["mode"]).reset_index(level=-1, drop=True)
    edges.index.names = ["source", "target"]
    return nodes, edges


def graph_to_data(g):
    """Converts a graph to nodes and edges DataFrames"""
    edges_df = nx.to_pandas_edgelist(g).set_index(['source', 'target'])
    node_df = pd.DataFrame.from_dict(dict(g.nodes(data=True)), orient='index')['boarding_cost'].to_frame()
    node_df.index.name = 'node_id'

    return node_df, edges_df


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


def custom_stringizer(value):
    """Custom stringizer for the CRS class used for graph writing"""
    if isinstance(value, CRS):
        return "<CRS>_" + value.to_string()
    elif isinstance(value, str):
        return value
    else:
        raise ValueError("not a CRS or string")


def custom_destringizer(value):
    """Custom destringizer for the CRS class used for graph reading"""
    if isinstance(value, str):
        if value.startswith("<CRS>_"):
            return CRS.from_string(value=value.replace("<CRS>_", ""))
        return value
    else:
        raise ValueError("not a string")


def save_graph(graph, path, **kwargs):
    """Saves a graph to a file"""
    nx.write_gml(graph, path + ".gml", stringizer=custom_stringizer, **kwargs)


def load_graph_from_file(path, **kwargs):
    """Loads a graph from a file"""
    return nx.read_gml(path + ".gml", destringizer=custom_destringizer, **kwargs)


def json_dumps_dfs_to_store(node_df, edge_df):
    return json.dumps(dict(node_df=node_df.to_json(orient="split", date_format="iso", index=True),
                           edge_df=edge_df.to_json(orient="split", date_format="iso", index=True)))


def json_loads_df_from_store(store, key):
    return pd.read_json(StringIO(json.loads(store)[key]), orient="split")


def json_dumps_graph_to_store(graph_in):
    graph = graph_in.copy()
    graph_dict = nx.node_link_data(graph)
    graph_dict['graph']['crs'] = custom_stringizer(graph_dict['graph']['crs'])
    return json.dumps(dict(graph=graph_dict))


def json_loads_graph_from_store(store, key="graph"):
    graph_dict = json.loads(store)[key]
    graph_dict['graph']['crs'] = custom_destringizer(graph_dict['graph']['crs'])
    return nx.node_link_graph(graph_dict)


########################################################################################
################### Plotting Functions #################################################
########################################################################################


def node_gdf_to_coords(node_gdf):
    node_dict = node_gdf.reset_index()[['lon', 'lat', 'node_id']].to_dict(orient="list")
    return node_dict['lon'], node_dict['lat'], node_dict['node_id']


def preprocess_edge_gdf(edge_gdf):
    edge_gdf['name'] = "From " + edge_gdf['name'].str.replace(EDGE_NAME_MID_TOKEN, " To ")
    edge_gdf.index = edge_gdf.index.map(
        lambda index: index[0].replace("DB_", "") + "-TO-" + index[1].replace("DB_", ""))  # Unify the index
    edge_gdf.index.name = "edge_id"
    return edge_gdf


def linestring_to_linespace_coords(linestring, dim):
    lat, long = linestring.xy
    return [np.linspace(lat[0], lat[1], dim + 2)[1:-1], np.linspace(long[0], long[1], dim + 2)[1:-1]]


def edge_gdf_to_coords(edge_gdf, linespace_dim=None):
    if linespace_dim is None or linespace_dim == 2:
        linespace_dim = 2
        edge_gdf[['lon', 'lat']] = edge_gdf['geometry'].to_frame().apply(lambda row: row.iloc[0].xy, axis=1,
                                                                         result_type="expand")  # Split the geometry into lat and long
    else:
        if linespace_dim < 1:
            raise ValueError("linespace_dim must be greater than 1")

        edge_gdf[['lon', 'lat']] = edge_gdf['geometry'].to_frame().apply(
            lambda row: linestring_to_linespace_coords(row.iloc[0], linespace_dim), axis=1,
            result_type="expand")  # Split the geometry into lat and long (with linespace_dim)

    longs = pad_array(np.concatenate(edge_gdf['lon'].values), step=linespace_dim)
    lats = pad_array(np.concatenate(edge_gdf['lat'].values), step=linespace_dim)
    ids = pad_array(np.repeat(edge_gdf.index.values, linespace_dim), step=linespace_dim)

    return longs, lats, ids


def plot_graph_map(g, num_edge_markers=30, nodes_style=None, edges_style=None, fig_style=None,
                   nodes_marker_increment=3):
    if fig_style is None:
        fig_style = {}
    if nodes_style is None:
        nodes_style = DEFAULT_MAPBOX_STYLE["nodes"]
    if edges_style is None:
        edges_style = DEFAULT_MAPBOX_STYLE["edges"]
    if "margin" not in fig_style.keys():
        fig_style["margin"] = DEFAULT_MAPBOX_STYLE["margin"]
    if "mapbox" not in fig_style.keys():
        fig_style["mapbox"] = DEFAULT_MAPBOX_STYLE["mapbox"]

    nodes, edges = graph_to_gdfs(g)

    threshold_25, threshold_75 = nodes['degree'].quantile(0.25), nodes['degree'].quantile(0.75)
    leaf_nodes = nodes[nodes['degree'] < threshold_25]
    mid_nodes = nodes[(nodes['degree'] >= threshold_25) & (nodes['degree'] <= threshold_75)]
    hub_nodes = nodes[nodes['degree'] > threshold_75]

    edges = preprocess_edge_gdf(edges)
    edges_longs, edges_lats, edges_ids = edge_gdf_to_coords(edges)
    edges_markers_longs, edges_markers_lats, edges_markers_ids = edge_gdf_to_coords(edges, num_edge_markers)

    fig = go.Figure()

    fig.add_trace(go.Scattermapbox(  # add edges
        mode="lines",
        lon=edges_longs,
        lat=edges_lats,
        hoverinfo="skip",
        line=edges_style,
    ))

    fig.add_trace(go.Scattermapbox(  # add edges markers (to be able to hover on edges)
        mode="markers",
        lon=edges_markers_longs,
        lat=edges_markers_lats,
        ids=edges_markers_ids,
        hoverinfo="none",
        marker=dict(color="rgba(0, 0, 0, 0.0)"),
    ))

    for i, node_gdf in enumerate([leaf_nodes, mid_nodes, hub_nodes]):
        longs, lats, ids = node_gdf_to_coords(node_gdf)
        marker_dict = nodes_style.copy()
        marker_dict['size'] = marker_dict['size'] + (i * nodes_marker_increment)
        fig.add_trace(go.Scattermapbox(  # add nodes
            mode="markers",
            lon=longs,
            lat=lats,
            ids=ids,
            hoverinfo="none",
            marker=marker_dict
        ))

    fig.update_layout(showlegend=False).update_layout(fig_style)

    node_df = nodes.drop(columns=["geometry", "lon", "lat"]).round(5)
    edge_df = edges.drop(columns=["geometry", "lon", "lat"])
    return node_df, edge_df, fig


########################################################################################
################### Graph Evaluation ###################################################
########################################################################################


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


def evaluate_graph(graph, node_df_in=None):
    """
    Function to evaluate a graph and return summary statistics, and node dataframe characteristics

    summarize the computations done in graph_evaluation.ipynb
    """

    # Extraction of nodes
    if node_df_in is None:
        node_df, _ = graph_to_data(graph)
    else:
        node_df = node_df_in.copy()

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

def attack_graph(graph_in, target=None, n_steps=ATTACKS_STEPS, min_threshold=ATTACKS_NODE_LOWERBOUND):
    graph = graph_in.copy()
    graph_stats, node_df = evaluate_graph(graph)
    total_nodes = graph_stats['nodes']
    amount = int((total_nodes - total_nodes * min_threshold) / n_steps)

    results = {'100%': graph_stats.values}
    for i in range(n_steps - 1):
        if target is None or target == "random":
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


def plot_attack_result(results, title, cols_to_plot=None, prettify=True):
    if cols_to_plot is None:
        cols_to_plot = ['edges', 'density', 'strong_GC', 'weak_GC', 'global_c_mean', 'avg_degree'] if prettify \
        else ["Edges", "Density", "Strong Giant Component", "Weak Giant Component", "Centrality Mean [Scaled]",
              "Avg Degree"]
    elif (len(cols_to_plot) % 2) != 0:
        raise ValueError('cols_to_plot must have an even number of elements')

    if prettify:
        results = prettify_graph_stats_columns(results[cols_to_plot].copy())
    else:
        results = results[cols_to_plot].copy()

    full_fig = make_subplots(rows=int(len(results.columns)/2), cols=2, subplot_titles=results.columns,
                             shared_xaxes=True, x_title="Nodes remaining%", y_title="Value")
    for i, col in enumerate(results.columns):
        full_fig.add_trace(go.Scatter(x=results.index, y=results[col], mode='markers+lines', name=col,
                                      hoverinfo="y"),
                           row=i // 2 + 1, col=i % 2 + 1)

    full_fig.update_layout(title=title + " specifico", showlegend=False, title_xanchor="center", title_yanchor="top",
                           title_y=0.9, title_x=0.5)

    results_scaled = results / results.max()

    scaled_fig = px.line(results_scaled, x=results_scaled.index, y=results_scaled.columns, title=title + " riassuntivo",
                         labels={'value': 'Value', 'index': 'Percentage of nodes remaining'},
                         ).update_layout(title_xanchor="center", title_yanchor="top", title_y=0.9, title_x=0.5)

    return full_fig, scaled_fig


def attacks_results_summary(results_list, summary_col='weak_GC', threshold=0.05, names_list=None, save=False,
                            n_steps=10, attack_nodes_lowerbound=ATTACKS_NODE_LOWERBOUND,
                            total_nodes=None, title=None, custom_labels=None):
    if names_list is None:
        names_list = ['random', 'centrality', 'degree', 'betweenness', 'closeness', 'eigenvector', 'clustering',
                      'pagerank']

    if custom_labels is None:
        custom_labels = {}

    if title is None:
        summary_plot_title = f'{summary_col.title()} Component for different attacks'
        bar_plot_title = f'Dead Graph Timestep for different attacks based on {summary_col.upper()}'
    elif isinstance(title, tuple):
        bar_plot_title, summary_plot_title = title
    else:
        summary_plot_title = title
        bar_plot_title = title

    dead_points = pd.Series(name='dead_point')
    summary_df = pd.DataFrame(index=results_list[0].index)
    iterator = zip(names_list, results_list)

    if total_nodes is None:
        amount = 1
    else:
        amount = int((total_nodes - total_nodes * attack_nodes_lowerbound) / n_steps)

    for name, results in iterator:
        dead_point = np.sum(results[summary_col] >= threshold)
        dead_points[name] = dead_point
        summary_df[name] = results[summary_col]

    dead_points = dead_points.to_frame()
    dead_points.index.name = 'attack'
    dead_points['nodes'] = dead_points['dead_point'] * amount

    if save:
        summary_df.to_csv(os.path.join(ATTACKS_PATH, f'summary_df_{n_steps}.csv'))
        dead_points.to_csv(os.path.join(ATTACKS_PATH, f'summary_dps_{n_steps}.csv'))

    bar_plot = px.bar(dead_points, x=dead_points.index, y='dead_point', hover_data='nodes',
                      title=bar_plot_title,
                      labels={'nodes': 'Nodes Removed', 'attack': 'Attack type', 'dead_point': 'Dead Timestep'
                              } | custom_labels
                      ).update_layout(title_xanchor="center", title_yanchor="top", title_y=0.9, title_x=0.5,
                                      yaxis_range=[0, n_steps])

    summary_plot = px.line(summary_df, title=summary_plot_title,
                           labels={'value': summary_col, 'index': 'Timestep'} | custom_labels
                           ).update_layout(title_xanchor="center", title_yanchor="top", title_y=0.9, title_x=0.5,
                                           yaxis_range=[0, 1])

    return dead_points, summary_df, bar_plot, summary_plot


########################################################################################
################### Prettify functions #################################################
########################################################################################


def prettify_node_df(node_df, inplace=False):
    if not inplace:
        node_df = node_df.copy()

    node_df.columns = node_df.columns.str.replace("_", " ").str.replace("centrality", "Cent"
                                                                        ).str.replace("scaled", "R").str.title()
    node_df.columns.name = "Property type"
    node_cols = node_df.columns.to_list()
    node_cols = node_cols[:3] + [node_cols[-1]] + node_cols[3:-1]
    node_df = node_df[node_cols]
    node_df.iloc[:, 3:] = node_df.iloc[:, 3:].round(5)
    return node_df


def prettify_edge_df(edge_df, inplace=False):
    if not inplace:
        edge_df = edge_df.copy()
    edge_df = edge_df[["name", "length"]]
    edge_df["name"] = edge_df["name"].str.replace("_", " ")
    edge_df.columns = edge_df.columns.str.replace("_", " ").str.title()
    edge_df.columns.name = "Property type"
    return edge_df


def prettify_graph_stats_columns(graph_stats, axis=1):
    if axis == 0:
        graph_stats = graph_stats.Transpose()

    rename_dict = {
        "global_c_mean": "centrality mean [scaled]",
        "global_cd_mean": "centrality degree mean",
        "global_cb_mean": "centrality betweenness mean",
        "global_cc_mean": "centrality closeness mean",
        "global_ce_mean": "centrality eigenvector mean",
        "global_ccc_mean": "clustering coefficient mean",
        "global_cp_mean": "pagerank mean"
    }

    graph_stats.columns = graph_stats.rename(columns=rename_dict) \
        .columns.str.replace("_", " ").str.replace("GC", "giant component").str.title()

    if axis == 0:
        graph_stats = graph_stats.Transpose()

    return graph_stats


def prettify_graph_stats(graph_stats, first_line_name="State 0"):
    graph_stats = graph_stats.rename(columns={"global_measures": first_line_name}).transpose().round(7)

    graph_stats = prettify_graph_stats_columns(graph_stats)
    graph_stats.index.name = "State"
    return graph_stats.reset_index()


