"""
Traffic Simulation Engine
=========================
Generates realistic synthetic traffic conditions on a road network.

Traffic levels:
  1.0 = Free flow
  1.5 = Light traffic
  2.5 = Moderate congestion
  4.0 = Heavy congestion
  10.0 = Road blockage
"""

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TrafficLevel(str, Enum):
    CLEAR = "clear"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    BLOCKED = "blocked"


TRAFFIC_FACTORS = {
    TrafficLevel.CLEAR: 1.0,
    TrafficLevel.LIGHT: 1.5,
    TrafficLevel.MODERATE: 2.5,
    TrafficLevel.HEAVY: 4.0,
    TrafficLevel.BLOCKED: 10.0,
}

TRAFFIC_COLORS = {
    TrafficLevel.CLEAR: "#22c55e",
    TrafficLevel.LIGHT: "#84cc16",
    TrafficLevel.MODERATE: "#eab308",
    TrafficLevel.HEAVY: "#ef4444",
    TrafficLevel.BLOCKED: "#7f1d1d",
}


@dataclass
class TrafficIncident:
    node: Any
    level: TrafficLevel
    factor: float
    description: str
    created_at: float = field(default_factory=time.time)
    duration_secs: float = 300.0  # 5 minutes default

    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.duration_secs

    def to_dict(self) -> Dict:
        return {
            "node": list(self.node) if isinstance(self.node, tuple) else self.node,
            "level": self.level.value,
            "factor": self.factor,
            "description": self.description,
            "age_secs": round(time.time() - self.created_at, 1),
        }


class TrafficSimulator:
    """
    Simulates dynamic traffic conditions across a road network graph.

    Usage:
        sim = TrafficSimulator(graph_nodes, seed=42)
        sim.tick()                     # advance time step
        traffic_map = sim.get_node_factors()  # {node: congestion_factor}
    """

    def __init__(
        self,
        nodes: List[Any],
        seed: int = 42,
        peak_hour: bool = False,
    ):
        self.nodes = nodes
        self.rng = random.Random(seed)
        self.peak_hour = peak_hour
        self.incidents: List[TrafficIncident] = []
        self._base_factors: Dict[Any, float] = {}
        self._tick_count = 0
        self._initialize_base_traffic()

    # ------------------------------------------------------------------
    def _initialize_base_traffic(self):
        """Assign baseline traffic to each node (spatial clustering)."""
        # Randomly seed some "hot zones" — high traffic clusters
        n_hotspots = max(1, len(self.nodes) // 20)
        hotspots = self.rng.sample(self.nodes, min(n_hotspots, len(self.nodes)))

        for node in self.nodes:
            # Nodes near hotspots get higher base traffic
            min_dist = min(
                self._node_distance(node, h) for h in hotspots
            )
            # Decay over distance (max influence radius = 5 grid units)
            influence = max(0.0, 1.0 - min_dist / 5.0)
            peak_mult = 1.6 if self.peak_hour else 1.0
            base = 1.0 + influence * 1.5 * peak_mult + self.rng.uniform(-0.2, 0.2)
            self._base_factors[node] = max(1.0, base)

    def _node_distance(self, a, b) -> float:
        if isinstance(a, tuple) and isinstance(b, tuple):
            return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        return 0.0

    # ------------------------------------------------------------------
    def tick(self):
        """Advance simulation one time step (~30 s of simulated time)."""
        self._tick_count += 1
        # Prune expired incidents
        self.incidents = [i for i in self.incidents if not i.is_expired()]

        # Randomly spawn new incidents
        if self.rng.random() < 0.15:  # 15% chance per tick
            self._spawn_incident()

        # Slightly perturb base factors (traffic fluctuates)
        for node in self.nodes:
            delta = self.rng.uniform(-0.1, 0.1)
            self._base_factors[node] = max(1.0, self._base_factors[node] + delta)

    def _spawn_incident(self):
        node = self.rng.choice(self.nodes)
        level = self.rng.choices(
            list(TrafficLevel),
            weights=[30, 30, 20, 15, 5],
        )[0]
        incident = TrafficIncident(
            node=node,
            level=level,
            factor=TRAFFIC_FACTORS[level] + self.rng.uniform(-0.3, 0.3),
            description=self._describe_incident(level),
            duration_secs=self.rng.uniform(60, 600),
        )
        self.incidents.append(incident)

    def _describe_incident(self, level: TrafficLevel) -> str:
        descriptions = {
            TrafficLevel.CLEAR: "Road clear",
            TrafficLevel.LIGHT: "Light traffic ahead",
            TrafficLevel.MODERATE: "Moderate congestion — slow down",
            TrafficLevel.HEAVY: "Heavy traffic — significant delay",
            TrafficLevel.BLOCKED: "Road blocked — detour required",
        }
        return descriptions[level]

    # ------------------------------------------------------------------
    def get_node_factors(self) -> Dict[Any, float]:
        """Return {node: congestion_factor} combining base + incidents."""
        factors = dict(self._base_factors)
        for incident in self.incidents:
            node = incident.node
            if node in factors:
                factors[node] = max(factors[node], incident.factor)
        return factors

    def get_traffic_level(self, node: Any) -> TrafficLevel:
        factor = self.get_node_factors().get(node, 1.0)
        if factor < 1.3:
            return TrafficLevel.CLEAR
        elif factor < 2.0:
            return TrafficLevel.LIGHT
        elif factor < 3.0:
            return TrafficLevel.MODERATE
        elif factor < 6.0:
            return TrafficLevel.HEAVY
        return TrafficLevel.BLOCKED

    def get_summary(self) -> Dict:
        factors = self.get_node_factors()
        levels = [self.get_traffic_level(n) for n in self.nodes]
        level_counts = {l.value: levels.count(l) for l in TrafficLevel}
        avg_factor = sum(factors.values()) / len(factors) if factors else 1.0
        return {
            "tick": self._tick_count,
            "peak_hour": self.peak_hour,
            "avg_congestion_factor": round(avg_factor, 2),
            "level_distribution": level_counts,
            "active_incidents": len(self.incidents),
            "incidents": [i.to_dict() for i in self.incidents[:10]],
        }

    def set_peak_hour(self, is_peak: bool):
        self.peak_hour = is_peak
        # Rescale base factors
        mult = 1.6 if is_peak else (1 / 1.6)
        for node in self._base_factors:
            self._base_factors[node] = max(1.0, self._base_factors[node] * mult)
