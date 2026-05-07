"""
Real-Time Simulation Engine
============================
Generates random emergencies, advances the simulation tick-by-tick,
and collects metrics for analysis and visualization.
"""

import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.algorithms.astar import build_grid_graph, compare_algorithms, manhattan_heuristic
from app.coverage.optimizer import (
    coverage_analysis,
    generate_demand_heatmap,
    kmeans_placement,
    compare_placements,
)
from app.dispatch.engine import (
    Ambulance,
    AmbulanceStatus,
    DispatchEngine,
    Emergency,
    Hospital,
    Severity,
)
from app.traffic.simulator import TrafficSimulator

SEVERITY_WEIGHTS = [10, 25, 40, 25]  # critical, high, medium, low

EMERGENCY_DESCRIPTIONS = {
    Severity.CRITICAL: [
        "Cardiac arrest reported",
        "Major vehicle collision with injuries",
        "Gunshot wound — critical",
        "Severe allergic reaction",
        "Drowning victim",
    ],
    Severity.HIGH: [
        "Suspected stroke",
        "Motorcycle accident",
        "Fall from height",
        "Chest pain — possible heart attack",
        "Severe burn injury",
    ],
    Severity.MEDIUM: [
        "Broken limb",
        "Moderate laceration",
        "Diabetic emergency",
        "Breathing difficulty",
        "Unconscious patient",
    ],
    Severity.LOW: [
        "Minor laceration",
        "Mild fever",
        "Sprained ankle",
        "Nausea and vomiting",
        "Non-urgent transfer",
    ],
}


# ---------------------------------------------------------------------------

class SimulationEngine:
    """
    Central simulation coordinator.
    Creates the city grid, spawns ambulances and hospitals,
    then runs tick-based simulation loop.
    """

    def __init__(
        self,
        rows: int = 16,
        cols: int = 16,
        num_ambulances: int = 5,
        num_hospitals: int = 3,
        coverage_radius: float = 8.0,
        connection_prob: float = 0.85,
        min_weight: float = 1.0,
        max_weight: float = 10.0,
        seed: int = 42,
        use_traffic: bool = True,
        peak_hour: bool = False,
    ):
        self.rows = rows
        self.cols = cols
        self.coverage_radius = coverage_radius
        self.seed = seed
        self.rng = random.Random(seed)
        self.use_traffic = use_traffic
        self.tick_count = 0
        self.start_time = time.time()

        # Build road network
        self.graph = build_grid_graph(
            rows, cols, connection_prob, min_weight, max_weight, seed
        )
        self.nodes: List[Any] = list(self.graph.keys())

        # Traffic simulator
        self.traffic_sim = TrafficSimulator(self.nodes, seed=seed, peak_hour=peak_hour)

        # Place hospitals (K-Means optimal positions)
        hospital_positions = kmeans_placement(
            [n for n in self.nodes if isinstance(n, tuple)],
            k=num_hospitals,
            seed=seed,
        )
        self.hospitals = [
            Hospital(
                id=f"H{i+1}",
                name=f"City Hospital {i+1}",
                node=pos,
                capacity=self.rng.randint(30, 80),
                specialties=self.rng.sample(
                    ["Trauma", "Cardiology", "Neurology", "Burns", "Paediatrics"], 2
                ),
            )
            for i, pos in enumerate(hospital_positions)
        ]

        # Place ambulances at hospital bases (with some spread)
        ambulance_positions = self._spread_ambulance_bases(
            hospital_positions, num_ambulances
        )
        self.ambulances = [
            Ambulance(
                id=f"AMB{i+1:02d}",
                base_node=pos,
                current_node=pos,
            )
            for i, pos in enumerate(ambulance_positions)
        ]

        # Dispatch engine
        self.dispatch = DispatchEngine(
            graph=self.graph,
            ambulances=self.ambulances,
            hospitals=self.hospitals,
            use_traffic=use_traffic,
        )

        # Coverage analysis
        facility_nodes = [h.node for h in self.hospitals]
        self.coverage_data = coverage_analysis(
            self.graph, facility_nodes, self.nodes, coverage_radius
        )
        self.heatmap = generate_demand_heatmap(
            [n for n in self.nodes if isinstance(n, tuple)],
            [n for n in facility_nodes if isinstance(n, tuple)],
            self.graph,
            seed=seed,
        )

    # ------------------------------------------------------------------
    def _spread_ambulance_bases(
        self, hospital_positions, num_ambulances: int
    ) -> List[Any]:
        """Distribute ambulances across city — some at hospitals, rest spread."""
        bases = list(hospital_positions)  # start at hospitals
        while len(bases) < num_ambulances:
            # Pick a random node not already used
            candidate = self.rng.choice(self.nodes)
            if candidate not in bases:
                bases.append(candidate)
        return bases[:num_ambulances]

    # ------------------------------------------------------------------
    def tick(self, spawn_emergency: bool = True) -> Dict:
        """Advance simulation by one time step."""
        self.tick_count += 1

        # Advance traffic
        self.traffic_sim.tick()
        traffic_factors = self.traffic_sim.get_node_factors()
        self.dispatch.update_traffic(traffic_factors)

        # Randomly spawn emergency
        new_emergency = None
        if spawn_emergency and self.rng.random() < 0.6:  # 60% chance per tick
            severity = self.rng.choices(list(Severity), weights=SEVERITY_WEIGHTS)[0]
            node = self.rng.choice(self.nodes)
            desc = self.rng.choice(EMERGENCY_DESCRIPTIONS[severity])
            new_emergency = self.dispatch.submit_emergency(node, severity, desc)

        return {
            "tick": self.tick_count,
            "new_emergency": new_emergency.to_dict() if new_emergency else None,
            "dispatch_state": self.dispatch.get_state(),
            "traffic": self.traffic_sim.get_summary(),
        }

    def run(self, n_ticks: int = 20) -> List[Dict]:
        """Run simulation for n_ticks steps, return all snapshots."""
        snapshots = []
        for _ in range(n_ticks):
            snapshot = self.tick()
            snapshots.append(snapshot)
            # Auto-resolve some dispatched emergencies
            for em in list(self.dispatch.active_emergencies.values()):
                if em.status.value == "assigned" and self.rng.random() < 0.3:
                    self.dispatch.resolve_emergency(em.id)
        return snapshots

    # ------------------------------------------------------------------
    def get_full_state(self) -> Dict:
        grid_data = []
        for node in self.nodes:
            if isinstance(node, tuple):
                r, c = node
                neighbours = list(self.graph.get(node, {}).keys())
                grid_data.append({
                    "id": f"{r},{c}",
                    "row": r,
                    "col": c,
                    "neighbours": [
                        {"row": n[0], "col": n[1], "weight": self.graph[node][n].get("weight", 1)}
                        for n in neighbours if isinstance(n, tuple)
                    ],
                })

        return {
            "config": {
                "rows": self.rows,
                "cols": self.cols,
                "seed": self.seed,
                "use_traffic": self.use_traffic,
                "coverage_radius": self.coverage_radius,
            },
            "grid": grid_data,
            "ambulances": [a.to_dict() for a in self.ambulances],
            "hospitals": [h.to_dict() for h in self.hospitals],
            "active_emergencies": [
                e.to_dict() for e in self.dispatch.active_emergencies.values()
            ],
            "coverage": self.coverage_data,
            "heatmap": self.heatmap,
            "traffic": self.traffic_sim.get_summary(),
            "metrics": self.dispatch.get_state()["metrics"],
        }

    def run_algorithm_comparison(
        self,
        n_pairs: int = 10,
    ) -> Dict:
        """Run A* vs Dijkstra comparison across random node pairs."""
        pairs = []
        for _ in range(n_pairs):
            start = self.rng.choice(self.nodes)
            goal = self.rng.choice(self.nodes)
            if start == goal:
                continue
            traffic_map = self.traffic_sim.get_node_factors()
            result = compare_algorithms(
                self.graph,
                start,
                goal,
                heuristic_fn=manhattan_heuristic,
                traffic_map=traffic_map,
            )
            result["pair"] = {
                "start": list(start) if isinstance(start, tuple) else start,
                "goal": list(goal) if isinstance(goal, tuple) else goal,
            }
            pairs.append(result)

        if not pairs:
            return {"pairs": [], "summary": {}}

        avg = lambda key, sub: sum(p[sub][key] for p in pairs if sub in p) / len(pairs)
        summary = {
            "n_pairs": len(pairs),
            "avg_astar_nodes": round(avg("nodes_explored", "astar"), 1),
            "avg_dijkstra_nodes": round(avg("nodes_explored", "dijkstra"), 1),
            "avg_astar_ms": round(avg("computation_time_ms", "astar"), 3),
            "avg_dijkstra_ms": round(avg("computation_time_ms", "dijkstra"), 3),
            "avg_speedup": round(sum(p.get("speedup", 1) for p in pairs) / len(pairs), 2),
            "avg_nodes_saved": round(sum(p.get("nodes_saved", 0) for p in pairs) / len(pairs), 1),
        }
        return {"pairs": pairs, "summary": summary}
