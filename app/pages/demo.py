import json
import os
import time

import dash
import numpy as np
import pandas as pd
import plotly.express as px
from dash import html, dash_table, dcc, callback, Input, Output, State, Patch
from dash_ag_grid import AgGrid
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from commons import *

init_graph = load_graph_from_file(os.path.join(RESULTS_PATH, "full_graph"))
init_node_df, init_edge_df, init_map_plot = plot_graph_map(init_graph)

hover_tt_style = dict(className="px-1 py-0 rounded fs-6 lh-1",
                      c_bg_nodes="#ec4540", c_b_nodes="#5b4d4c", c_t_nodes="#684443",
                      c_bg_edges="#6374f4", c_b_edges="#9ea9f8", c_t_edges="#e0e4fc")
graph_notify_delete = html.P("Elementi in rimozione, attendere...")
graph_notify_reset = html.P("Grafo in reset, attendere...")
graph_notify_save = html.P("Salvataggio grafo, attendere...")

init_graph_stats = prettify_graph_stats(pd.read_csv(os.path.join(RESULTS_PATH, "graph_stats.csv"), index_col="metric"))

init_graph_stats_table = AgGrid(rowData=init_graph_stats.to_dict('records'),
                                columnDefs=[{'field': col} for col in init_graph_stats.columns],
                                defaultColDef={"resizable": True, "sortable": True, "filter": True,
                                               "wrapText": True, 'autoHeight': True,
                                               "wrapHeaderText": True, "autoHeaderHeight": True},
                                columnSize='sizeToFit',
                                id="graph_stats_table")

print("start\n\n\n\n")

layout = dbc.Container(fluid=True, children=[
    html.Center(html.H1("Demo", className="display-3 my-4")),
    html.Div(className="my-3", style={"position": "relative"}, children=[
        html.Div(dcc.Graph(id="map_plot", figure=init_map_plot, clear_on_unhover=True,
                           responsive=True, style={'height': '70vh'})),
        dcc.Tooltip(id="map_hover_tooltip", className=hover_tt_style["className"]),

        dmc.Button(DashIconify(icon="gg:arrow-left", color="black", width=24), variant="subtle", size="md",
                   className="position-absolute top-50 end-0", id="open_bt_click_info", display="block"),
        dbc.Tooltip("Show information", target="open_bt_click_info", placement="top", style={"font-size": "0.6rem"}),
        dmc.Button(DashIconify(icon="gg:arrow-right", color="black", width=24), variant="subtle", size="md",
                   className="position-absolute top-50 start-0", id="open_bt_click_info_copy", display="block"),
        dbc.Tooltip("Show copied information", target="open_bt_click_info_copy", placement="top",
                    style={"font-size": "0.6rem"}),

        dbc.Toast(id="click_info", is_open=False, dismissable=True, headerClassName="d-flex",
                  header=html.Div(className="d-flex", children=[
                      html.Div(id="click_info_header", children="Information"),
                      html.Div(children=[
                          dmc.Button(DashIconify(icon="grommet-icons:copy", color="black"), variant="light",
                                     compact=True, id="click_info_copy_toast", size="sm"),
                          dbc.Tooltip("Copy to second table", target="click_info_copy_toast",
                                      placement="top", style={"font-size": "0.6rem"}),
                          dcc.Clipboard(target_id='click_info_content', className="ms-1",
                                        id="click_info_copy_clipboard"),
                          dbc.Tooltip("Copy to clipboard", target="click_info_copy_clipboard",
                                      placement="top", style={"font-size": "0.6rem"}),
                      ], className="d-flex ms-3"),
                  ]),
                  children=[html.Div(id="click_info_content"),
                            html.Div([html.Br(),
                                      html.Center(dbc.Button("Remove Element", id="remove_element", color="danger",
                                                             size="sm"))
                                      ])
                            ], className="position-absolute top-0 end-0 mt-5"),

        dbc.Toast(id="click_info_copy", header="Copied Information", is_open=False, dismissable=True,
                  className="position-absolute top-0 start-0 mt-5"),

        dbc.Toast(id="graph_notify", header="Notifica grafo", icon="info", is_open=False, dismissable=True,
                  duration=3000, className="position-absolute top-0 start-0 mt-3 ms-3"),
        html.Div(className="d-flex position-absolute bottom-0 start-0 mb-3 ms-3", children=[
            dbc.Button("Reset Graph", id="reset_graph_btn", color="secondary", size="sm", outline=True, disabled=True,
                       className="me-2"),
            dbc.Tooltip("Reset the graph to the initial state", target="reset_graph_btn",
                        placement="top", style={"font-size": "0.6rem"}),
            dbc.Button("Remove Elements", id="remove_elements", color="danger", size="sm", outline=True, disabled=True,
                       className="me-2"),
            dbc.Tooltip("Remove selected elements", target="remove_elements",
                        placement="top", style={"font-size": "0.6rem"}),

            dbc.Button("Save Graph", id="save_graph_popover", color="secondary", size="sm", outline=True,
                       disabled=False),
            dbc.Tooltip("Save the graph to file", target="save_graph_popover",
                        placement="top", style={"font-size": "0.6rem"}),
            dbc.Popover(target="save_graph_popover", trigger="legacy", placement="top", children=dbc.PopoverBody([
                dbc.Input(id="save_graph_input", type="text", placeholder="Insert file name", size="sm"),
                dbc.Button("Confirm", id="save_graph_btn", color="success", size="sm", className="ms-1")
            ], className="d-flex justify-content-between align-items-center")),

        ]),
    ]),

    html.Center(html.H3("Caratteristiche generali del grafo"), className="my-5"),
    html.Div(className="my-2", id='graph_stats_table_div', children=[init_graph_stats_table]),

    html.Center(html.H3("Manual Attack results"), className="my-5"),
    html.Center(dbc.Button("Load Attack Results", id="load_attack_results", color="primary")),
    dcc.Loading(html.Div(className="my-2", children=[
        dcc.Graph(id="attack_results_full"), dcc.Graph(id="attack_result_scaled")]), type="circle"),


    dcc.Store(id="clicked_elem", data=None),
    dcc.Store(id="reset_click_state", data=None),
    dcc.Store(id="dfs", data=json_dumps_dfs_to_store(init_node_df, init_edge_df)),
    dcc.Store(id="graph", data=json_dumps_graph_to_store(init_graph)),
    dcc.Store(id="general_memory", data=json.dumps(dict(del_clicks=0))),
    dcc.Store(id="map_box_relayout", data=json.dumps(dict(center=DEFAULT_MAPBOX_STYLE['mapbox']['center'],
                                                          zoom=DEFAULT_MAPBOX_STYLE['mapbox']['zoom']))),
])


@callback(Output('click_info', 'is_open'), Output('open_bt_click_info', 'display'),
          Input('open_bt_click_info', 'n_clicks'), Input('click_info', 'n_dismiss'), prevent_initial_call=True)
def show_hide_click_info(n_clicks, n_dismiss):
    if dash.callback_context.triggered_id == "open_bt_click_info":
        return True, "none"
    return False, "block"


@callback(Output('click_info_copy', 'is_open'), Output('open_bt_click_info_copy', 'display'),
          Input('open_bt_click_info_copy', 'n_clicks'), Input('click_info_copy', 'n_dismiss'),
          prevent_initial_call=True)
def show_hide_click_info_copy(n_clicks, n_dismiss):
    if dash.callback_context.triggered_id == "open_bt_click_info_copy":
        return True, "none"
    return False, "block"


@callback(Output('map_hover_tooltip', 'show'),
          Output('map_hover_tooltip', 'bbox'),
          Output('map_hover_tooltip', 'children'),
          Output('map_hover_tooltip', "background_color"),
          Output('map_hover_tooltip', "border_color"),
          Input('map_plot', 'hoverData'), State('dfs', 'data'), prevent_initial_call=True)
def display_hover_info(hover_data, dfs_data):
    if hover_data is None:
        return False, None, None, None, None
    hover_data = hover_data['points'][0]
    bbox = hover_data['bbox']
    if hover_data['curveNumber'] == 0 or hover_data['curveNumber'] > 4:
        raise ValueError("Hovering error: curveNumber not valid.")
    elif hover_data['curveNumber'] == 1:
        output = display_hover_edge_info(hover_data, json_loads_df_from_store(dfs_data, "edge_df"))
        c_bg, c_b = hover_tt_style["c_bg_edges"], hover_tt_style["c_b_edges"]
    else:
        output = display_hover_node_info(hover_data, json_loads_df_from_store(dfs_data, "node_df"))
        c_bg, c_b = hover_tt_style["c_bg_nodes"], hover_tt_style["c_b_nodes"]

    return True, bbox, output, c_bg, c_b


def display_hover_edge_info(hover_data, edge_df):
    return html.Div(className="fluid", style={"max-width": "200px", "color": hover_tt_style["c_t_edges"]}, children=[
        html.P(f"{edge_df.at[hover_data['id'], 'name'].replace('_', ' ')}",
               className="small my-1 text-wrap text-center"),
        html.Hr(className="my-1 color-black"),
        html.P(f"Lon: {hover_data['lon']}", className="small my-1"),
        html.P(f"Lat: {hover_data['lat']}", className="small my-1"),
        html.P(f"Id: {hover_data['id']}", className="small my-1"),
        html.P(f"Length: {edge_df.at[hover_data['id'], 'length']}", className="small my-1"),
    ])


def display_hover_node_info(hover_data, node_df):
    return html.Div(className="fluid", style={"max-width": "2000px", "color": hover_tt_style["c_t_nodes"]}, children=[
        html.P(f"{node_df.at[hover_data['id'], 'name']}", className="small my-1 text-wrap text-center"),
        html.Hr(className="my-1 color-black"),
        html.P(f"Lon: {hover_data['lon']}", className="small my-1"),
        html.P(f"Lat: {hover_data['lat']}", className="small my-1"),
        html.P(f"Id: {hover_data['id']}", className="small my-1"),
        html.P(f"Degree: {node_df.at[hover_data['id'], 'degree']}", className="small my-1"),
        html.P(f"Centrality: {round(node_df.at[hover_data['id'], 'centrality'], 5)}", className="small my-1"),
    ])


@callback(Output("reset_click_state", "data", allow_duplicate=True),
          Output("click_info_header", "children", allow_duplicate=True),
          Output("click_info_content", "children", allow_duplicate=True),
          Output("clicked_elem", "data", allow_duplicate=True),
          Input("reset_click_state", "data"), prevent_initial_call=True)
def reset_click_state(state):
    return json.dumps(False), "Information", "", None


@callback(Output("click_info_header", "children", allow_duplicate=True),
          Output("click_info_content", "children", allow_duplicate=True),
          Output("clicked_elem", "data", allow_duplicate=True),
          Input('map_plot', 'clickData'), State('dfs', 'data'), prevent_initial_call=True)
def display_click_info(click_data, dfs_data):
    if click_data is None:
        return None, None, None
    click_data = click_data['points'][0]

    if click_data['curveNumber'] == 0 or click_data['curveNumber'] > 4:
        raise ValueError("Click error: curveNumber not valid.")
    elif click_data['curveNumber'] == 1:
        edge_df = json_loads_df_from_store(dfs_data, "edge_df")
        edge_info = prettify_edge_df(edge_df).loc[click_data['id']]

        edge_info = edge_info.to_frame(name="Property value").reset_index()
        text, data = "Hedge Information", dbc.Table.from_dataframe(edge_info, bordered=True, hover=True,
                                                                   responsive=True, striped=True, size="sm")
        elem_type = "edge"
    else:
        node_df = json_loads_df_from_store(dfs_data, "node_df")
        node_info = prettify_node_df(node_df).drop(columns=["Boarding Cost"]).loc[click_data['id']]
        node_info = node_info.to_frame(name="Property value").reset_index()
        text, data = "Node Information", dbc.Table.from_dataframe(node_info, striped=True, size="sm",
                                                                  bordered=True, hover=True, responsive=True)
        elem_type = "node"

    return text, data, json.dumps(dict(id=click_data['id'], type=elem_type))


@callback(Output("click_info_copy", "header"), Output("click_info_copy", "children"),
          Input("click_info_copy_toast", "n_clicks"),
          State("click_info_header", "children"), State("click_info_content", "children"), prevent_initial_call=True)
def copy_click_info(n_click_copy_btn, header, content):
    if n_click_copy_btn is None:
        return dash.no_update, dash.no_update

    return "Copied " + header, content


def remove_elements_graph(graph_data, selected_ids, selected_types, relayout_data, general_memory):
    if len(selected_ids) != len(selected_types):
        raise ValueError("Selected ids and types have different length.")

    del_clicks = json.loads(general_memory)['del_clicks'] + 1
    graph = json_loads_graph_from_store(graph_data)
    relayout_center, relayout_zoom = json.loads(relayout_data)["center"], json.loads(relayout_data)["zoom"]

    for elem_id, elem_type in zip(selected_ids, selected_types):
        try:
            if elem_type == "edge":
                u, v = ["DB_" + edge_id for edge_id in elem_id.split("-TO-")]
                graph.remove_edge(u, v)
            else:
                graph.remove_node(elem_id)
        except nx.NetworkXError as e:
            continue

    node_df, edge_df, map_fig = plot_graph_map(graph)
    graph_stats, node_df = evaluate_graph(graph, node_df)
    map_fig.update_layout(mapbox_center=relayout_center, mapbox_zoom=relayout_zoom)

    graph_stats = prettify_graph_stats(graph_stats.to_frame(), first_line_name=f'State {del_clicks}')
    graph_stats_patch = Patch()
    graph_stats_patch.extend(graph_stats.to_dict('records'))

    return map_fig, graph_stats_patch, json_dumps_dfs_to_store(node_df, edge_df), json_dumps_graph_to_store(graph), \
        json.dumps(dict(del_clicks=del_clicks))


@callback(Output("map_plot", "figure", allow_duplicate=True),
          Output("graph_stats_table", "rowData", allow_duplicate=True),
          Output("reset_click_state", "data", allow_duplicate=True),
          Output('dfs', 'data', allow_duplicate=True),
          Output('graph', 'data', allow_duplicate=True),
          Output('general_memory', 'data', allow_duplicate=True),
          Input("remove_element", "n_clicks"), Input("remove_elements", "n_clicks"),
          State("clicked_elem", "data"), State("map_plot", "selectedData"), State('graph', 'data'),
          State('general_memory', 'data'), State("map_box_relayout", "data"),
          prevent_initial_call=True, background=True,
          running=[
              (Output("remove_element", "disabled"), True, False),
              (Output('reset_graph_btn', "disabled"), True, False),
              (Output("graph_notify", "is_open"), True, False),
              (Output("graph_notify", "children"), graph_notify_delete, html.P("")),
          ])
def elements_removal(_, __, clicked_elem, selected_elems, graph_data, gm, relayout_data):
    if dash.callback_context.triggered_id == "remove_element":
        if clicked_elem is None:
            return dash.no_update
        clicked_elem = json.loads(clicked_elem)
        clicked_ids, clicked_types = [clicked_elem['id']], [clicked_elem['type']]
    else:
        clicked_ids, clicked_types = [], []
        for elem in selected_elems['points']:
            if elem['id'] not in clicked_ids:
                clicked_ids.append(elem['id'])
                clicked_types.append("edge" if elem['curveNumber'] == 1 else "node")

    map_fig, gsp, dfs_data, g_data, gm = remove_elements_graph(graph_data, clicked_ids, clicked_types,
                                                               relayout_data, gm)

    return map_fig, gsp, json.dumps(True), dfs_data, g_data, gm


@callback(Output("map_plot", "figure", allow_duplicate=True),
          Output("graph_stats_table_div", "children", allow_duplicate=True),
          Output("reset_click_state", "data", allow_duplicate=True),
          Output('dfs', 'data', allow_duplicate=True),
          Output('graph', 'data', allow_duplicate=True),
          Output('general_memory', 'data', allow_duplicate=True),
          Output("reset_graph_btn", "disabled", allow_duplicate=True),
          Output("remove_elements", "disabled", allow_duplicate=True),
          Input("reset_graph_btn", "n_clicks"), State("map_box_relayout", "data"),
          prevent_initial_call=True, background=True,
          running=[
              (Output("remove_element", "disabled"), True, False),
              (Output('reset_graph_btn', "disabled"), True, False),
              (Output("graph_notify", "is_open"), True, False),
              (Output("graph_notify", "children"), graph_notify_reset, html.P("")),
          ])
def graph_reset(_, relayout_data):
    relayout_center, relayout_zoom = json.loads(relayout_data)["center"], json.loads(relayout_data)["zoom"]
    graph = init_graph.copy()
    node_df, edge_df, map_fig = init_node_df, init_edge_df, init_map_plot
    map_fig.update_layout(mapbox_center=relayout_center, mapbox_zoom=relayout_zoom)

    return map_fig, init_graph_stats_table, json.dumps(True), json_dumps_dfs_to_store(node_df, edge_df), \
        json_dumps_graph_to_store(graph), json.dumps(dict(del_clicks=0)), True, True


@callback(Output("reset_graph_btn", "disabled"),
          Input('general_memory', 'data'), prevent_initial_call=True)
def graph_reset_check(general_memory):
    del_clicks = json.loads(general_memory)['del_clicks']
    if del_clicks == 0:
        return dash.no_update

    return False


@callback(Output("map_box_relayout", "data"), Input("map_plot", "relayoutData"), prevent_initial_call=True)
def save_relayout(relayout_data):
    if relayout_data is not None and "mapbox.center" in relayout_data:
        return json.dumps(dict(center=relayout_data["mapbox.center"], zoom=relayout_data["mapbox.zoom"]))

    return dash.no_update


@callback(Output("remove_elements", "disabled", allow_duplicate=True),
          Input("map_plot", "selectedData"), prevent_initial_call=True)
def check_remove_elements(selected_data):
    if selected_data is not None:
        return False

    return True


@callback(Output("graph_notify", "is_open"), Output("graph_notify", "children"),
          State("save_graph_input", "value"), State("graph", "data"), Input("save_graph_btn", "n_clicks"),
          prevent_initial_call=True, background=True,
          running=[
              (Output("remove_element", "disabled"), True, False),
              (Output('reset_graph_btn', "disabled"), True, False),
              (Output("graph_notify", "is_open"), True, False),
              (Output("graph_notify", "children"), graph_notify_save, html.P("")),
          ])
def save_graph_to_file(file_name, graph_data, __):
    print(file_name)
    file_name = "_" + file_name.replace(" ", "_")

    graph = json_loads_graph_from_store(graph_data)
    save_graph(graph, os.path.join(USERS_PATH, f"{file_name}.gml"))
    return True, html.P("Grafo salvato con successo.")



@callback(Output("attack_results_full", "figure"), Output("attack_result_scaled", "figure"),
            State("graph_stats_table", "rowData"), Input("load_attack_results", "n_clicks"))
def load_attack_result(table_data, _):
    cols_to_plot = ["Edges", "Density", "Strong Giant Component", "Weak Giant Component",
                    "Centrality Mean [Scaled]", "Avg Degree"]
    table_data = pd.DataFrame(table_data).set_index("State")
    fig_full, fig_scaled = plot_attack_result(table_data, "Risultati attacco", cols_to_plot=cols_to_plot)

    return fig_full, fig_scaled
