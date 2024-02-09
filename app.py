import dash
from dash import dcc
from dash import html


from commons import *
import os
import peartree as ptr

src = GTFS_PATH_OTHER
feed_id, feed_name = 1139, "DB" # Deytsche Bahn
feed_path = os.path.join(src, f'{feed_id}.zip')
feed = ptr.get_representative_feed(feed_path)
start_time, end_time = 7, 20
graph = ptr.load_feed_as_graph(feed, start_time=start_time*3600, end_time=end_time*3600, name=feed_name)

# Create the plot
fig = plot_graph_map(graph, num_edge_markers=30)

app = dash.Dash(__name__)

app.layout = html.Div(children=[
    html.H1(children='My Dash App'),

    dcc.Graph(
        id='example-graph',
        figure=fig
    )
])

if __name__ == '__main__':
    app.run_server(debug=True)

#%%
