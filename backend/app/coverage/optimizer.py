"""
Coverage Optimization Module
=============================
Analyses ambulance coverage gaps, computes Voronoi territories,
and recommends optimal placement using K-Means + coverage scoring.
"""

import math
import random
from typing import Any, Dict, List, Optional, Tuple

from app.algorithms.astar import astar, manhattan_heuristic


# ---------------------------------------------------------------------------
# Coverage Analysis
# ---------------------------------------------------------------------------

def coverage_analysis(
    graph: Dict,
    facility_nodes: List[Any],
    all_nodes: List[Any],
    radius: float,
    weight_key: str = "weight",
) -> Dict:
    """
    Compute which nodes are covered (reachable within `radius` cost).
    Returns coverage percentage and per-node coverage flags.
    """
    covered = set()
    node_min_dist: Dict[Any, float] = {}

    for facility in facility_nodes:
        for node in all_nodes:
            result = astar(graph, facility, node, heuristic_fn=manhattan_heuristic)
            dist = result.cost
            if dist <= radius:
                covered.add(node)
            prev = node_min_dist.get(node, math.inf)
            node_min_dist[node] = min(prev, dist)

    coverage_pct = len(covered) / len(all_nodes) * 100 if all_nodes else 0

    return {
        "coverage_pct": round(coverage_pct, 2),
        "covered_nodes": len(covered),
        "total_nodes": len(all_nodes),
        "uncovered_nodes": len(all_nodes) - len(covered),
        "node_distances": {
            str(k): round(v, 2) if v != math.inf else -1
            for k, v in node_min_dist.items()
        },
        "coverage_score": round(coverage_pct, 2),
    }


# ---------------------------------------------------------------------------
# K-Means placement optimiser
# ---------------------------------------------------------------------------

def kmeans_placement(
    nodes: List[Tuple[int, int]],
    k: int,
    iterations: int = 50,
    seed: int = 42,
) -> List[Tuple[int, int]]:
    """
    K-Means clustering to find optimal ambulance base locations.
    Works on 2-D tuple nodes (row, col).
    Returns k centroid nodes (snapped to nearest actual node).
    """
    rng = random.Random(seed)
    # Initialise centroids randomly (K-Means++ style)
    centroids = [rng.choice(nodes)]
    for _ in range(k - 1):
        dists = [min(
            math.dist(n, c) for c in centroids
        ) for n in nodes]
        total = sum(dists)
        probs = [d / total for d in dists]
        # Weighted random selection
        r = rng.random()
        cumulative = 0
        for node, prob in zip(nodes, probs):
            cumulative += prob
            if r <= cumulative:
                centroids.append(node)
                break
        else:
            centroids.append(rng.choice(nodes))

    for _ in range(iterations):
        # Assignment
        clusters: Dict[int, List] = {i: [] for i in range(k)}
        for node in nodes:
            nearest = min(range(k), key=lambda i: math.dist(node, centroids[i]))
            clusters[nearest].append(node)

        # Update centroids
        new_centroids = []
        for i in range(k):
            if clusters[i]:
                mean_r = sum(n[0] for n in clusters[i]) / len(clusters[i])
                mean_c = sum(n[1] for n in clusters[i]) / len(clusters[i])
                # Snap to nearest actual node
                nearest_node = min(
                    clusters[i],
                    key=lambda n: math.dist(n, (mean_r, mean_c))
                )
                new_centroids.append(nearest_node)
            else:
                new_centroids.append(centroids[i])
        centroids = new_centroids

    return centroids


# ---------------------------------------------------------------------------
# Voronoi territories
# ---------------------------------------------------------------------------

def voronoi_territories(
    nodes: List[Any],
    facility_nodes: List[Any],
    graph: Dict,
) -> Dict[str, List[Any]]:
    """
    Assign each node to its nearest facility (Voronoi region).
    Uses A* distances.  Returns {facility_id: [nodes]}.
    """
    territories: Dict[int, List] = {i: [] for i in range(len(facility_nodes))}

    for node in nodes:
        best_facility = 0
        best_cost = math.inf
        for i, facility in enumerate(facility_nodes):
            result = astar(graph, facility, node, heuristic_fn=manhattan_heuristic)
            if result.cost < best_cost:
                best_cost = result.cost
                best_facility = i
        territories[best_facility].append(node)

    return {
        str(i): [list(n) if isinstance(n, tuple) else n for n in nodes]
        for i, nodes in territories.items()
    }


# ---------------------------------------------------------------------------
# Heatmap generation
# ---------------------------------------------------------------------------

def generate_demand_heatmap(
    nodes: List[Tuple[int, int]],
    facility_nodes: List[Tuple[int, int]],
    graph: Dict,
    demand: Optional[Dict[Any, float]] = None,
    seed: int = 42,
) -> List[Dict]:
    """
    Generate heatmap data — each cell has a risk/demand score.
    Higher score = more underserved or higher demand.
    """
    rng = random.Random(seed)
    if demand is None:
        demand = {n: rng.uniform(0.1, 1.0) for n in nodes}

    heatmap = []
    for node in nodes:
        # Nearest facility distance
        min_dist = math.inf
        for f in facility_nodes:
            result = astar(graph, f, node, heuristic_fn=manhattan_heuristic)
            min_dist = min(min_dist, result.cost)

        d = demand.get(node, 0.5)
        # Risk = demand * distance (higher = more underserved)
        risk = d * (1 + min_dist / 10.0)
        heatmap.append({
            "node": list(node) if isinstance(node, tuple) else node,
            "row": node[0] if isinstance(node, tuple) else 0,
            "col": node[1] if isinstance(node, tuple) else 0,
            "demand": round(d, 3),
            "min_dist_to_facility": round(min_dist, 2) if min_dist != math.inf else -1,
            "risk_score": round(risk, 3),
        })

    # Normalise risk scores 0-1
    max_risk = max((h["risk_score"] for h in heatmap), default=1.0)
    if max_risk > 0:
        for h in heatmap:
            h["risk_score_normalised"] = round(h["risk_score"] / max_risk, 3)

    return heatmap


# ---------------------------------------------------------------------------
# Comparative placement evaluation
# ---------------------------------------------------------------------------

def compare_placements(
    graph: Dict,
    nodes: List[Any],
    optimised_facilities: List[Any],
    random_facilities: List[Any],
    coverage_radius: float,
) -> Dict:
    """Return side-by-side metrics for optimised vs random placement."""
    opt = coverage_analysis(graph, optimised_facilities, nodes, coverage_radius)
    rnd = coverage_analysis(graph, random_facilities, nodes, coverage_radius)

    return {
        "optimised": opt,
        "random": rnd,
        "improvement_pct": round(opt["coverage_pct"] - rnd["coverage_pct"], 2),
        "optimised_facilities": [
            list(f) if isinstance(f, tuple) else f for f in optimised_facilities
        ],
        "random_facilities": [
            list(f) if isinstance(f, tuple) else f for f in random_facilities
        ],
    }
