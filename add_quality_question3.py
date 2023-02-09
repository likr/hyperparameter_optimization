# Standard Library
import argparse
import json
import os

# Third Party Library
import networkx as nx
import pandas as pd

# First Party Library
from drawing.fruchterman_reingold import fruchterman_reingold
from drawing.sgd import sgd
from quality_metrics import run_time
from utils.calc_quality_metrics import calc_qs
from utils.graph import generate_egraph_graph, graph_preprocessing

ALL_QUALITY_METRICS_NAMES = [
    "angular_resolution",
    "aspect_ratio",
    "crossing_angle",
    "crossing_number",
    "gabriel_graph_property",
    "ideal_edge_length",
    "node_resolution",
    "run_time",
    "shape_based_metrics",
    "stress",
]


EDGE_WEIGHT = 30


ds = ["les_miserables", "1138_bus", "USpowerGrid"]

layout_name_abbreviations = [
    "SS",
    "FR",
]

parser = argparse.ArgumentParser()

parser.add_argument("-q", required=True, help="question id")
parser.add_argument(
    "-l",
    choices=layout_name_abbreviations,
    required=True,
    help="layout name",
)

args = parser.parse_args()

l = args.l
question_id = args.q

ps = [
    "les_miserables-1138_bus",
    "les_miserables-USpowerGrid",
    "1138_bus-USpowerGrid",
]

df = pd.read_pickle(f"data/question3/{l}/{question_id}/data.pkl")
new_df = pd.DataFrame()
for p in ps:
    d_from, d_to = p.split("-")
    dataset_path = f"lib/egraph-rs/js/dataset/{d_to}.json"
    with open(dataset_path) as f:
        graph_data = json.load(f)
    nx_graph = graph_preprocessing(nx.node_link_graph(graph_data), EDGE_WEIGHT)
    all_pairs_shortest_path_length = dict(
        nx.all_pairs_dijkstra_path_length(nx_graph)
    )
    graph = None
    indices = None
    if l == "SS":
        graph, indices = generate_egraph_graph(nx_graph)

    for i, row in df.iterrows():
        r_dict = row.to_dict()
        if r_dict["dataset_from"] != d_from and r_dict["dataset_to"] != d_to:
            continue
        if r_dict["type"] != "multi_optimized":
            r_dict["quality_metrics"] = None
            new_df = pd.concat([new_df, pd.DataFrame([r_dict])])
            continue
        params = row["params"]
        seed = row["seed"]
        pos = None
        rt = run_time.RunTime()

        rt.start()
        if l == "FR":
            pos = fruchterman_reingold(nx_graph, params)
        elif l == "SS":
            pos = sgd(graph, indices, params, seed)
        rt.end()

        if row.pos != pos:
            print("diff", row.id)

        quality_metrics = calc_qs(
            nx_graph=nx_graph,
            pos=pos,
            all_pairs_shortest_path_length=all_pairs_shortest_path_length,
            target_quality_metrics_names=ALL_QUALITY_METRICS_NAMES,
            edge_weight=EDGE_WEIGHT,
        )
        quality_metrics = {**quality_metrics, "run_time": rt.quality()}
        print(quality_metrics)
        r_dict["quality_metrics"] = quality_metrics
        new_df = pd.concat([new_df, pd.DataFrame([r_dict])])

new_df.to_pickle(f"data/question3/{l}/{question_id}/data_with_qs.pkl")
