"""
A* Pathfinding Algorithm — Production Implementation
=====================================================
Implements A*, Dijkstra, and traffic-aware routing on a grid or OSM graph.

Mathematical formulation:
  f(n) = g(n) + h(n)
  g(n) = actual cost from start to n
  h(n) = heuristic estimate from n to goal (Haversine or Manhattan)
"""

import heapq
import math
import time
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Heuristics
# ---------------------------------------------------------------------------

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Haversine formula — great-circle distance in metres.
    Admissible heuristic when edge weights are travel distances.
    """
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def manhattan_heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    """Manhattan distance for grid graphs (row, col) nodes."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def euclidean_heuristic(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


# ---------------------------------------------------------------------------
# Core A* Implementation
# ---------------------------------------------------------------------------

class PathResult:
    """Encapsulates the result of a pathfinding run."""

    def __init__(
        self,
        path: List[Any],
        cost: float,
        nodes_explored: int,
        computation_time_ms: float,
        algorithm: str,
    ):
        self.path = path
        self.cost = cost
        self.nodes_explored = nodes_explored
        self.computation_time_ms = computation_time_ms
        self.algorithm = algorithm

    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "cost": self.cost,
            "nodes_explored": self.nodes_explored,
            "computation_time_ms": round(self.computation_time_ms, 3),
            "algorithm": self.algorithm,
            "path_length": len(self.path),
        }


def astar(
    graph: Dict[Any, Dict[Any, float]],
    start: Any,
    goal: Any,
    heuristic_fn=None,
    weight_key: str = "weight",
) -> PathResult:
    """
    A* search algorithm.

    Parameters
    ----------
    graph      : adjacency dict  {node: {neighbour: {weight_key: cost, ...}, ...}}
    start      : source node
    goal       : target node
    heuristic_fn : callable(node, goal) -> float   (None → Dijkstra)
    weight_key : edge attribute to use as cost

    Returns
    -------
    PathResult with reconstructed path, total cost, and diagnostics.
    """
    if heuristic_fn is None:
        heuristic_fn = lambda a, b: 0.0  # degenerates to Dijkstra

    t0 = time.perf_counter()

    # open_set: (f_score, tie_breaker, node)
    counter = 0
    open_set: List[Tuple[float, int, Any]] = []
    heapq.heappush(open_set, (0.0, counter, start))

    came_from: Dict[Any, Any] = {}
    g_score: Dict[Any, float] = {start: 0.0}
    closed_set: set = set()
    nodes_explored = 0

    while open_set:
        f, _, current = heapq.heappop(open_set)

        if current == goal:
            # Reconstruct path
            path = []
            node = goal
            while node in came_from:
                path.append(node)
                node = came_from[node]
            path.append(start)
            path.reverse()
            elapsed = (time.perf_counter() - t0) * 1000
            return PathResult(path, g_score[goal], nodes_explored, elapsed, "astar")

        if current in closed_set:
            continue
        closed_set.add(current)
        nodes_explored += 1

        for neighbour, attrs in graph.get(current, {}).items():
            if neighbour in closed_set:
                continue
            edge_cost = attrs if isinstance(attrs, (int, float)) else attrs.get(weight_key, 1.0)
            tentative_g = g_score[current] + edge_cost

            if tentative_g < g_score.get(neighbour, math.inf):
                came_from[neighbour] = current
                g_score[neighbour] = tentative_g
                h = heuristic_fn(neighbour, goal)
                f_new = tentative_g + h
                counter += 1
                heapq.heappush(open_set, (f_new, counter, neighbour))

    elapsed = (time.perf_counter() - t0) * 1000
    return PathResult([], math.inf, nodes_explored, elapsed, "astar")


def dijkstra(
    graph: Dict[Any, Dict[Any, float]],
    start: Any,
    goal: Any,
    weight_key: str = "weight",
) -> PathResult:
    """Standard Dijkstra — used as benchmark against A*."""
    return astar(graph, start, goal, heuristic_fn=None, weight_key=weight_key)


# ---------------------------------------------------------------------------
# Grid-graph builder (used in simulation without OSM)
# ---------------------------------------------------------------------------

def build_grid_graph(
    rows: int,
    cols: int,
    connection_prob: float = 0.85,
    min_weight: float = 1.0,
    max_weight: float = 10.0,
    seed: int = 42,
) -> Dict[Tuple[int, int], Dict[Tuple[int, int], Dict[str, float]]]:
    """
    Build a random weighted grid graph.
    Nodes are (row, col) tuples.  Edges are bidirectional.
    """
    import random
    rng = random.Random(seed)
    graph: Dict = {}

    def add_edge(u, v, w):
        graph.setdefault(u, {})[v] = {"weight": w}
        graph.setdefault(v, {})[u] = {"weight": w}

    for r in range(rows):
        for c in range(cols):
            node = (r, c)
            graph.setdefault(node, {})
            # right
            if c + 1 < cols and rng.random() < connection_prob:
                w = rng.uniform(min_weight, max_weight)
                add_edge(node, (r, c + 1), w)
            # down
            if r + 1 < rows and rng.random() < connection_prob:
                w = rng.uniform(min_weight, max_weight)
                add_edge(node, (r + 1, c), w)

    return graph


# ---------------------------------------------------------------------------
# Traffic-aware weight modifier
# ---------------------------------------------------------------------------

def apply_traffic_weights(
    graph: Dict,
    traffic_map: Dict[Tuple, float],
    weight_key: str = "weight",
) -> Dict:
    """
    Returns a new graph where edge weights are multiplied by
    the average congestion factor of the two endpoint nodes.
    traffic_map: {node -> congestion_factor}  (1.0 = clear, 3.0 = heavy)
    """
    traffic_graph: Dict = {}
    for u, neighbours in graph.items():
        traffic_graph[u] = {}
        for v, attrs in neighbours.items():
            factor_u = traffic_map.get(u, 1.0)
            factor_v = traffic_map.get(v, 1.0)
            factor = (factor_u + factor_v) / 2.0
            base_w = attrs.get(weight_key, 1.0) if isinstance(attrs, dict) else attrs
            traffic_graph[u][v] = {weight_key: base_w * factor}
    return traffic_graph


# ---------------------------------------------------------------------------
# Comparison utility
# ---------------------------------------------------------------------------

def compare_algorithms(
    graph: Dict,
    start: Any,
    goal: Any,
    heuristic_fn=None,
    traffic_map: Optional[Dict] = None,
) -> Dict:
    """Run A* and Dijkstra, return side-by-side metrics."""
    # Static routing
    dijkstra_result = dijkstra(graph, start, goal)
    astar_result = astar(graph, start, goal, heuristic_fn=heuristic_fn)

    results = {
        "dijkstra": dijkstra_result.to_dict(),
        "astar": astar_result.to_dict(),
        "speedup": (
            dijkstra_result.computation_time_ms / astar_result.computation_time_ms
            if astar_result.computation_time_ms > 0 else 1.0
        ),
        "nodes_saved": dijkstra_result.nodes_explored - astar_result.nodes_explored,
    }

    if traffic_map is not None:
        tg = apply_traffic_weights(graph, traffic_map)
        traffic_result = astar(tg, start, goal, heuristic_fn=heuristic_fn)
        traffic_result.algorithm = "astar_traffic"
        results["astar_traffic"] = traffic_result.to_dict()

    return results
