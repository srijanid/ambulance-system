"""
Unit Tests — A* Pathfinding Algorithm
"""

import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.algorithms.astar import (
    astar,
    dijkstra,
    build_grid_graph,
    apply_traffic_weights,
    compare_algorithms,
    haversine,
    manhattan_heuristic,
)


def test_simple_path():
    """A* finds path in a tiny graph."""
    graph = {
        (0,0): {(0,1): {'weight': 1}, (1,0): {'weight': 1}},
        (0,1): {(0,0): {'weight': 1}, (1,1): {'weight': 1}},
        (1,0): {(0,0): {'weight': 1}, (1,1): {'weight': 1}},
        (1,1): {(0,1): {'weight': 1}, (1,0): {'weight': 1}},
    }
    result = astar(graph, (0,0), (1,1), heuristic_fn=manhattan_heuristic)
    assert result.cost == 2.0
    assert result.path[0] == (0,0)
    assert result.path[-1] == (1,1)
    assert len(result.path) == 3


def test_astar_equals_dijkstra_cost():
    """A* and Dijkstra must return identical costs."""
    graph = build_grid_graph(8, 8, seed=1)
    nodes = list(graph.keys())
    for start, goal in [(nodes[0], nodes[-1]), (nodes[3], nodes[10])]:
        a = astar(graph, start, goal, heuristic_fn=manhattan_heuristic)
        d = dijkstra(graph, start, goal)
        assert abs(a.cost - d.cost) < 1e-9, f"Cost mismatch: {a.cost} vs {d.cost}"


def test_astar_explores_fewer_nodes():
    """A* with admissible heuristic explores ≤ nodes vs Dijkstra."""
    graph = build_grid_graph(10, 10, seed=42)
    nodes = list(graph.keys())
    start, goal = nodes[0], nodes[-1]
    a = astar(graph, start, goal, heuristic_fn=manhattan_heuristic)
    d = dijkstra(graph, start, goal)
    assert a.nodes_explored <= d.nodes_explored


def test_unreachable_node():
    """Returns infinite cost when goal unreachable."""
    graph = {
        (0,0): {(0,1): {'weight': 1}},
        (0,1): {(0,0): {'weight': 1}},
        (1,0): {},  # isolated
    }
    result = astar(graph, (0,0), (1,0), heuristic_fn=manhattan_heuristic)
    assert result.cost == math.inf
    assert result.path == []


def test_same_node():
    """Path from a node to itself has cost 0."""
    graph = build_grid_graph(5, 5, seed=7)
    node = list(graph.keys())[0]
    result = astar(graph, node, node, heuristic_fn=manhattan_heuristic)
    assert result.cost == 0.0


def test_traffic_weights_increase_cost():
    """Traffic-weighted graph should produce higher path costs."""
    graph = build_grid_graph(6, 6, seed=9)
    nodes = list(graph.keys())
    start, goal = nodes[0], nodes[-1]

    # High congestion on all nodes
    traffic_map = {n: 3.0 for n in nodes}
    traffic_graph = apply_traffic_weights(graph, traffic_map)

    static = astar(graph, start, goal, heuristic_fn=manhattan_heuristic)
    congested = astar(traffic_graph, start, goal, heuristic_fn=manhattan_heuristic)

    if static.cost < math.inf:
        assert congested.cost >= static.cost


def test_haversine():
    """Haversine returns 0 for same coords and ~111km for 1° lat diff."""
    assert haversine(0, 0, 0, 0) == 0.0
    dist = haversine(0, 0, 1, 0)
    assert 110_000 < dist < 112_000  # ~111 km


def test_grid_graph_structure():
    """Grid graph has correct node count and bidirectional edges."""
    g = build_grid_graph(4, 4, connection_prob=1.0, seed=0)
    assert len(g) == 16
    for u, neighbours in g.items():
        for v, attrs in neighbours.items():
            assert v in g
            assert u in g[v]  # bidirectional
            assert 'weight' in attrs


def test_compare_algorithms_keys():
    """compare_algorithms returns expected keys."""
    graph = build_grid_graph(5, 5, seed=3)
    nodes = list(graph.keys())
    result = compare_algorithms(graph, nodes[0], nodes[-1], heuristic_fn=manhattan_heuristic)
    assert 'astar' in result
    assert 'dijkstra' in result
    assert 'speedup' in result


if __name__ == '__main__':
    tests = [v for k, v in globals().items() if k.startswith('test_')]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f'  ✓  {t.__name__}')
            passed += 1
        except Exception as e:
            print(f'  ✗  {t.__name__}: {e}')
            failed += 1
    print(f'\n{passed} passed, {failed} failed')
