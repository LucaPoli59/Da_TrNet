import os

os.popen("pip install -r requirements.txt")

from commons import *
from urllib.request import urlretrieve

for path in [DATA_PATH, GTFS_PATH_IT, GTFS_PATH_UK, GTFS_PATH_OTHER, APP_PATH, RESULTS_PATH, ATTACKS_PATH, USERS_PATH]:
    if not os.path.exists(path):
        os.makedirs(path)


df = pd.read_csv(os.path.join(DATA_PATH, "sources.csv")).set_index("mdb_source_id")

ids_to_download = [1139]
for id_to_download in ids_to_download:
    path = os.path.join(GTFS_PATH_OTHER, f'{id_to_download}.zip')
    if not os.path.exists(path):
        try:
            url = df.loc[id_to_download, "urls.direct_download"]
            urlretrieve(url, path)
        except:
            print(f"Error downloading {id_to_download}, {df.loc[id_to_download, 'provider']}")

graph = load_graph_from_feed()
nodes_df, edges_df = graph_to_gdfs(graph)

id_name_mapping = nodes_df['name'].to_dict()

edges_df['name'] = edges_df.index.to_frame()[['source', 'target']].apply(
    lambda x: str(id_name_mapping[x[0]]).replace(" ", "_") + EDGE_NAME_MID_TOKEN + str(id_name_mapping[x[1]]).replace(
        " ", "_"), axis=1, raw=True)
edges_df['key'] = 0
attribute_to_add = edges_df.set_index('key', append=True)['name'].to_dict()

nx.set_edge_attributes(graph, attribute_to_add, 'name')

graph_stats, new_nodes_df = evaluate_graph(graph, nodes_df)
graph_stats.index.name = "metric"
graph_stats.to_csv(os.path.join(RESULTS_PATH, "graph_stats.csv"))

full_graph = graph.copy()
cols = [col for col in new_nodes_df.columns if col not in nodes_df.columns]

for col in cols:
    nx.set_node_attributes(full_graph, new_nodes_df[col].to_dict(), col)

save_graph(graph, os.path.join(RESULTS_PATH, "graph"))
save_graph(full_graph, os.path.join(RESULTS_PATH, "full_graph"))
