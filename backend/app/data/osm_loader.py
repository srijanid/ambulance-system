"""
OSM Loader for Smart Ambulance System
====================================
Loads road network and converts it for A* routing.
"""

import osmnx as ox
import networkx as nx
from typing import Any, Tuple


# ---------------------------------------------------------------------
# 1. LOAD OSM GRAPH
# ---------------------------------------------------------------------

def load_osm_graph(graphml_path: str):

    print("Loading GraphML...")

    # LOAD GRAPHML
    G = ox.load_graphml(graphml_path)

    # IMPORTANT:
    # DO NOT PROJECT GRAPH
    # Leaflet requires original lat/lon coordinates

    print(f"Loaded graph: {len(G.nodes)} nodes | {len(G.edges)} edges")

    return G


# ---------------------------------------------------------------------
# 2. CONVERT TO A* GRAPH
# ---------------------------------------------------------------------

def convert_osm_to_astar_graph(G):

    graph = {}

    for u, v, data in G.edges(data=True):

        cost = float(data.get("length", 1.0))

        if u not in graph:
            graph[u] = {}

        # KEEP LOWEST EDGE COST
        if v not in graph[u]:
            graph[u][v] = cost
        else:
            graph[u][v] = min(graph[u][v], cost)

    return graph


# ---------------------------------------------------------------------
# 3. GPS → NEAREST NODE
# ---------------------------------------------------------------------

def get_nearest_node(
    G: nx.MultiDiGraph,
    lat: float,
    lon: float
):

    return ox.distance.nearest_nodes(
        G,
        X=lon,
        Y=lat
    )


# ---------------------------------------------------------------------
# 4. PREPARE ROUTE NODES
# ---------------------------------------------------------------------

def prepare_route_nodes(
    G: nx.MultiDiGraph,
    ambulance_lat: float,
    ambulance_lon: float,
    patient_lat: float,
    patient_lon: float
) -> Tuple[Any, Any]:

    start = get_nearest_node(
        G,
        ambulance_lat,
        ambulance_lon
    )

    goal = get_nearest_node(
        G,
        patient_lat,
        patient_lon
    )

    return start, goal


# ---------------------------------------------------------------------
# 5. A* HEURISTIC
# ---------------------------------------------------------------------

def osm_heuristic(
    node1: Any,
    node2: Any,
    G: nx.MultiDiGraph
) -> float:

    x1 = G.nodes[node1]["x"]
    y1 = G.nodes[node1]["y"]

    x2 = G.nodes[node2]["x"]
    y2 = G.nodes[node2]["y"]

    return (
        ((x1 - x2) ** 2) +
        ((y1 - y2) ** 2)
    ) ** 0.5