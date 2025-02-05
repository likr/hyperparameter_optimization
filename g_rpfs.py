"""
SparseSgdのパラメータ最適化実験
"""
# Standard Library
import argparse
import json
import math
import os
import random
import uuid

# Third Party Library
import networkx as nx
import pandas as pd

# First Party Library
from drawing.fruchterman_reingold import fruchterman_reingold
from drawing.sgd import sgd
from quality_metrics import (
    angular_resolution,
    aspect_ratio,
    crossing_angle,
    crossing_number,
    gabriel_graph_property,
    ideal_edge_length,
    node_resolution,
    run_time,
    shape_based_metrics,
    stress,
)
from quality_metrics.run_time import RunTime
from utils.calc_quality_metrics import calc_qs
from utils.dataset import dataset_names
from utils.graph import generate_egraph_graph, graph_preprocessing

SS = "SS"
FR = "FR"
FM3 = "FM3"
KK = "KK"

QUALITY_METRICS = {
    "angular_resolution": angular_resolution,
    "aspect_ratio": aspect_ratio,
    "crossing_angle": crossing_angle,
    "crossing_number": crossing_number,
    "gabriel_graph_property": gabriel_graph_property,
    "ideal_edge_length": ideal_edge_length,
    "node_resolution": node_resolution,
    # "run_time": run_time,
    "shape_based_metrics": shape_based_metrics,
    "stress": stress,
}

ALL_QUALITY_METRICS_NAMES = sorted([name for name in QUALITY_METRICS])

RAND_MAX = 2**32


def save(
    export_path,
    pid,
    seed,
    params,
    pos,
    quality_metrics,
):
    base_df = pd.DataFrame()
    if os.path.exists(export_path):
        base_df = pd.read_pickle(export_path)

    new_df = pd.DataFrame(
        [
            {
                "pid": pid,
                "seed": seed,
                "params": params,
                "pos": pos,
                "quality_metrics": quality_metrics,
            }
        ]
    )

    df = pd.concat([base_df, new_df])
    df.to_pickle(export_path)


def parse_args():
    layout_name_abbreviations = [
        SS,
        FR,
        FM3,
        KK,
    ]

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-d", choices=dataset_names, required=True, help="dataset name"
    )
    parser.add_argument("-p", type=int, required=True, help="n params")
    parser.add_argument("-s", type=int, required=True, help="n seed")
    parser.add_argument(
        "-l",
        choices=layout_name_abbreviations,
        required=True,
        help="layout name",
    )

    args = parser.parse_args()

    return args


if __name__ == "__main__":
    EDGE_WEIGHT = 30

    args = parse_args()

    dataset_path = f"lib/egraph-rs/js/dataset/{args.d}.json"

    export_directory = f"data/rpfs/{args.l}/{args.d}"
    file_id = str(uuid.uuid4())
    export_path = f"{export_directory}/{file_id}.pkl"
    os.makedirs(export_directory, exist_ok=True)

    with open(dataset_path) as f:
        graph_data = json.load(f)
    nx_graph = graph_preprocessing(nx.node_link_graph(graph_data), EDGE_WEIGHT)
    all_pairs_shortest_path_length = dict(
        nx.all_pairs_dijkstra_path_length(nx_graph)
    )

    if args.l == SS:
        graph, indices = generate_egraph_graph(nx_graph)
        for i in range(args.p):
            pid = uuid.uuid4()
            # number_of_pivots_rate = random.uniform(0.01, 1)
            # number_of_pivots = math.ceil(
            #     number_of_pivots_rate * math.sqrt(len(nx_graph.nodes))
            # )
            # number_of_pivots = math.ceil(
            #     number_of_pivots_rate * len(nx_graph.nodes)
            # )
            params = {
                "edge_length": EDGE_WEIGHT,
                # "number_of_pivots_rate": number_of_pivots_rate,
                # "number_of_pivots": number_of_pivots,
                "number_of_pivots": random.randint(1, 100),
                "number_of_iterations": random.randint(1, 200),
                "eps": random.uniform(0.01, 1),
            }

            for s in range(args.s):
                seed = random.randint(0, RAND_MAX)
                print(i, s, seed)
                # rt = RunTime()

                # rt.start()
                pos = sgd(graph, indices, params, seed)
                # rt.end()

                quality_metrics = calc_qs(
                    nx_graph=nx_graph,
                    pos=pos,
                    all_pairs_shortest_path_length=all_pairs_shortest_path_length,
                    target_quality_metrics_names=ALL_QUALITY_METRICS_NAMES,
                    edge_weight=EDGE_WEIGHT,
                )
                # quality_metrics = {
                #     **quality_metrics,
                #     "run_time": rt.quality(),
                # }

                save(
                    export_path=export_path,
                    pid=pid,
                    seed=seed,
                    params=params,
                    pos=pos,
                    quality_metrics=quality_metrics,
                )

    elif args.l == FR:
        for p in range(args.p):
            pid = uuid.uuid4()

            # k_rate = random.uniform(0.01, 1)
            # k = math.ceil(k_rate * len(nx_graph.nodes))

            k_rate = random.uniform(0.01, 1)
            # k 1/n ~ 0.1
            n = len(nx_graph.nodes)
            start_e = 1 / n
            end_e = 0.1
            if end_e < start_e:
                print("error")
                raise ValueError()
            d = end_e - start_e
            k = k_rate * d + start_e

            params = {
                "k_rate": k_rate,
                "k": k,
                "pos": None,
                "fixed": None,
                "iterations": random.randint(10, 200),
                "threshold": random.uniform(0.00001, 0.001),
                "weight": "weight",
                "scale": 1,
                "center": None,
                "dim": 2,
                "seed": None,
            }

            for s in range(args.s):
                print(p, s)
                params = {**params, "seed": s}

                rt = RunTime()

                rt.start()
                pos = fruchterman_reingold(nx_graph=nx_graph, params=params)
                rt.end()

                quality_metrics = calc_qs(
                    nx_graph=nx_graph,
                    pos=pos,
                    all_pairs_shortest_path_length=all_pairs_shortest_path_length,
                    target_quality_metrics_names=ALL_QUALITY_METRICS_NAMES,
                    edge_weight=EDGE_WEIGHT,
                )
                quality_metrics = {
                    **quality_metrics,
                    "run_time": rt.quality(),
                }

                save(
                    export_path=export_path,
                    pid=pid,
                    n_seed=s,
                    params=params,
                    pos=pos,
                    quality_metrics=quality_metrics,
                )
