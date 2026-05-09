"""
OSM Loader for Smart Ambulance System
======================================
Loads road network and converts it for A* routing.
"""

import os
import osmnx as ox
import networkx as nx
from typing import Any, Dict, Tuple


# ---------------------------------------------------------------------
# 1. Load OSM Graph (FAST + STABLE)
# ---------------------------------------------------------------------

def load_osm_graph(graphml_path: str):
    print("Loading GraphML...")

    G = ox.load_graphml(graphml_path)

    G = ox.project_graph(G)

    print(f"Nodes: {len(G.nodes)} | Edges: {len(G.edges)}")

    return G


# ---------------------------------------------------------------------
# 2. Convert to A* adjacency list
# ---------------------------------------------------------------------

def convert_osm_to_astar_graph(G):
    graph = {}

    for u, v, data in G.edges(data=True):
        cost = float(data.get("length", 1.0))

        if u not in graph:
            graph[u] = {}

        # keep minimum cost if multiple edges exist
        if v not in graph[u]:
            graph[u][v] = cost
        else:
            graph[u][v] = min(graph[u][v], cost)

    return graph


# ---------------------------------------------------------------------
# 3. GPS → nearest node
# ---------------------------------------------------------------------

def get_nearest_node(G: nx.MultiDiGraph, lat: float, lon: float):
    """
    Snap GPS coordinate to nearest road node.
    """
    return ox.distance.nearest_nodes(G, lon, lat)


# ---------------------------------------------------------------------
# 4. Prepare routing nodes
# ---------------------------------------------------------------------

def prepare_route_nodes(
    G: nx.MultiDiGraph,
    ambulance_lat: float,
    ambulance_lon: float,
    patient_lat: float,
    patient_lon: float
) -> Tuple[Any, Any]:

    start = get_nearest_node(G, ambulance_lat, ambulance_lon)
    goal = get_nearest_node(G, patient_lat, patient_lon)

    return start, goal


# ---------------------------------------------------------------------
# 5. Heuristic 
# ---------------------------------------------------------------------

def osm_heuristic(node1: Any, node2: Any, G: nx.MultiDiGraph) -> float:
    """
    Euclidean distance heuristic for A*
    """

    x1, y1 = G.nodes[node1]["x"], G.nodes[node1]["y"]
    x2, y2 = G.nodes[node2]["x"], G.nodes[node2]["y"]

    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5