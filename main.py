from urllib.request import urlretrieve

from commons import *

for path in [DATA_PATH, INPUT_PATH, OUTPUT_PATH, GTFS_PATH_IT, GTFS_PATH_UK, GTFS_PATH_OTHER, ATTACKS_PATH, USERS_PATH]:
    if not os.path.exists(path):
        os.makedirs(path)


df = pd.read_csv(os.path.join(INPUT_PATH, "sources.csv")).set_index("mdb_source_id")

ids_to_download = [1139]
for id_to_download in ids_to_download:
    path = os.path.join(GTFS_PATH_OTHER, f'{id_to_download}.zip')
    if not os.path.exists(path):
        try:
            url = df.loc[id_to_download, "urls.direct_download"]
            urlretrieve(url, path)
        except:
            print(f"Error downloading {id_to_download}, {df.loc[id_to_download, 'provider']}")


# graph evaluation

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
graph_stats.to_csv(os.path.join(OUTPUT_PATH, "graph_stats.csv"))

full_graph = graph.copy()
cols = [col for col in new_nodes_df.columns if col not in nodes_df.columns]

for col in cols:
    nx.set_node_attributes(full_graph, new_nodes_df[col].to_dict(), col)

save_graph(graph, os.path.join(OUTPUT_PATH, "graph"))
save_graph(full_graph, os.path.join(OUTPUT_PATH, "full_graph"))





# graph attacks

graph_full = load_graph_from_feed()
_, node_df = evaluate_graph(graph_full)

targets = ['random', 'centrality', 'centrality_degree', 'centrality_betweenness', 'centrality_closeness', 'centrality_eigenvector', 'centrality_clustering', 'centrality_pagerank']
results = []

for target in targets:
    result = attack_graph(graph_in=graph_full, target=target)
    results.append(result)
    result.to_csv(os.path.join(ATTACKS_PATH, f'{target}_{ATTACKS_STEPS}.csv'))

