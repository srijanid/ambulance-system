"""
Smart Ambulance Dispatch System
================================
Handles emergency prioritization, ambulance allocation, ETA calculation,
and hospital assignment using A* routing.
"""

import heapq
import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.algorithms.astar import astar, apply_traffic_weights, manhattan_heuristic


# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "critical"   # Cardiac arrest, major trauma — immediate
    HIGH = "high"           # Stroke, severe injury — < 8 min
    MEDIUM = "medium"       # Fractures, moderate pain — < 15 min
    LOW = "low"             # Minor injury — < 30 min

SEVERITY_PRIORITY = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}

SEVERITY_COLORS = {
    Severity.CRITICAL: "#dc2626",
    Severity.HIGH: "#ea580c",
    Severity.MEDIUM: "#ca8a04",
    Severity.LOW: "#16a34a",
}

AVG_SPEED_MS = 11.1  # ~40 km/h urban average (metres/second)


class AmbulanceStatus(str, Enum):
    AVAILABLE = "available"
    DISPATCHED = "dispatched"
    ON_SCENE = "on_scene"
    TRANSPORTING = "transporting"
    AT_HOSPITAL = "at_hospital"
    RETURNING = "returning"
    MAINTENANCE = "maintenance"


class EmergencyStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Ambulance:
    id: str
    base_node: Any
    current_node: Any
    status: AmbulanceStatus = AmbulanceStatus.AVAILABLE
    assigned_emergency_id: Optional[str] = None
    total_responses: int = 0
    total_distance: float = 0.0
    created_at: float = field(default_factory=time.time)

    def is_available(self) -> bool:
        return self.status == AmbulanceStatus.AVAILABLE

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "base_node": list(self.base_node) if isinstance(self.base_node, tuple) else self.base_node,
            "current_node": list(self.current_node) if isinstance(self.current_node, tuple) else self.current_node,
            "status": self.status.value,
            "assigned_emergency_id": self.assigned_emergency_id,
            "total_responses": self.total_responses,
            "total_distance": round(self.total_distance, 2),
        }


@dataclass
class Hospital:
    id: str
    name: str
    node: Any
    capacity: int = 50
    current_patients: int = 0
    specialties: List[str] = field(default_factory=list)

    def is_available(self) -> bool:
        return self.current_patients < self.capacity

    def occupancy_pct(self) -> float:
        return self.current_patients / self.capacity * 100

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "node": list(self.node) if isinstance(self.node, tuple) else self.node,
            "capacity": self.capacity,
            "current_patients": self.current_patients,
            "occupancy_pct": round(self.occupancy_pct(), 1),
            "is_available": self.is_available(),
        }


@dataclass
class Emergency:
    id: str
    node: Any
    severity: Severity
    description: str
    status: EmergencyStatus = EmergencyStatus.PENDING
    assigned_ambulance_id: Optional[str] = None
    assigned_hospital_id: Optional[str] = None
    route: List[Any] = field(default_factory=list)
    eta_seconds: float = 0.0
    response_time_seconds: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    dispatched_at: Optional[float] = None
    resolved_at: Optional[float] = None

    def priority(self) -> int:
        return SEVERITY_PRIORITY[self.severity]

    def age_seconds(self) -> float:
        return time.time() - self.created_at

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "node": list(self.node) if isinstance(self.node, tuple) else self.node,
            "severity": self.severity.value,
            "description": self.description,
            "status": self.status.value,
            "assigned_ambulance_id": self.assigned_ambulance_id,
            "assigned_hospital_id": self.assigned_hospital_id,
            "route": [list(n) if isinstance(n, tuple) else n for n in self.route],
            "eta_seconds": round(self.eta_seconds, 1),
            "response_time_seconds": round(self.response_time_seconds, 1) if self.response_time_seconds else None,
            "age_seconds": round(self.age_seconds(), 1),
            "color": SEVERITY_COLORS[self.severity],
        }


# ---------------------------------------------------------------------------
# Priority Queue wrapper for emergencies
# ---------------------------------------------------------------------------

class EmergencyQueue:
    """Min-heap priority queue — lower priority number = higher urgency."""

    def __init__(self):
        self._heap: List[Tuple[int, float, Emergency]] = []
        self._entry_finder: Dict[str, Emergency] = {}
        self._counter = 0

    def push(self, emergency: Emergency):
        priority = (emergency.priority(), emergency.created_at, self._counter)
        self._counter += 1
        heapq.heappush(self._heap, (*priority, emergency))
        self._entry_finder[emergency.id] = emergency

    def pop(self) -> Optional[Emergency]:
        while self._heap:
            p, ts, cnt, emergency = heapq.heappop(self._heap)
            if emergency.id in self._entry_finder:
                del self._entry_finder[emergency.id]
                return emergency
        return None

    def remove(self, emergency_id: str):
        self._entry_finder.pop(emergency_id, None)

    def __len__(self):
        return len(self._entry_finder)

    def peek_all(self) -> List[Emergency]:
        return sorted(self._entry_finder.values(), key=lambda e: (e.priority(), e.created_at))


# ---------------------------------------------------------------------------
# Dispatch Engine
# ---------------------------------------------------------------------------

class DispatchEngine:
    """
    Core dispatch logic:
    1. Maintain fleet of ambulances
    2. Accept incoming emergencies
    3. Assign nearest available ambulance using A*
    4. Select best hospital
    5. Track response metrics
    """

    def __init__(
        self,
        graph: Dict,
        ambulances: List[Ambulance],
        hospitals: List[Hospital],
        use_traffic: bool = True,
    ):
        self.graph = graph
        self.ambulances = {a.id: a for a in ambulances}
        self.hospitals = {h.id: h for h in hospitals}
        self.use_traffic = use_traffic
        self.emergency_queue = EmergencyQueue()
        self.active_emergencies: Dict[str, Emergency] = {}
        self.resolved_emergencies: List[Emergency] = []
        self.traffic_map: Dict[Any, float] = {}
        self._metrics: List[Dict] = []

    def update_traffic(self, traffic_map: Dict[Any, float]):
        self.traffic_map = traffic_map

    def _routing_graph(self) -> Dict:
        if self.use_traffic and self.traffic_map:
            return apply_traffic_weights(self.graph, self.traffic_map)
        return self.graph

    # ------------------------------------------------------------------
    def submit_emergency(
        self,
        node: Any,
        severity: Severity,
        description: str = "",
    ) -> Emergency:
        """Register a new emergency and trigger dispatch."""
        emergency = Emergency(
            id=str(uuid.uuid4())[:8],
            node=node,
            severity=severity,
            description=description or f"{severity.value.title()} emergency",
        )
        self.emergency_queue.push(emergency)
        self.active_emergencies[emergency.id] = emergency
        self._dispatch_next()
        return emergency

    # ------------------------------------------------------------------
    def _dispatch_next(self):
        """Process highest-priority pending emergencies."""
        pending = [
            e for e in self.emergency_queue.peek_all()
            if e.status == EmergencyStatus.PENDING
        ]
        for emergency in pending:
            ambulance = self._find_best_ambulance(emergency)
            if ambulance is None:
                break  # no available ambulances
            self._assign(emergency, ambulance)

    def _find_best_ambulance(self, emergency: Emergency) -> Optional[Ambulance]:
        """Find nearest available ambulance via A*."""
        rg = self._routing_graph()
        best_ambulance: Optional[Ambulance] = None
        best_cost = math.inf

        for amb in self.ambulances.values():
            if not amb.is_available():
                continue
            result = astar(
                rg,
                amb.current_node,
                emergency.node,
                heuristic_fn=manhattan_heuristic,
            )
            if result.cost < best_cost:
                best_cost = result.cost
                best_ambulance = amb

        return best_ambulance

    def _find_best_hospital(self, emergency: Emergency) -> Optional[Hospital]:
        """Find nearest available hospital."""
        rg = self._routing_graph()
        best_hospital: Optional[Hospital] = None
        best_cost = math.inf

        for hosp in self.hospitals.values():
            if not hosp.is_available():
                continue
            result = astar(
                rg,
                emergency.node,
                hosp.node,
                heuristic_fn=manhattan_heuristic,
            )
            if result.cost < best_cost:
                best_cost = result.cost
                best_hospital = hosp

        return best_hospital

    def _assign(self, emergency: Emergency, ambulance: Ambulance):
        """Assign ambulance to emergency and compute route."""
        rg = self._routing_graph()
        route_result = astar(
            rg,
            ambulance.current_node,
            emergency.node,
            heuristic_fn=manhattan_heuristic,
        )
        hospital = self._find_best_hospital(emergency)

        # Update emergency
        emergency.status = EmergencyStatus.ASSIGNED
        emergency.assigned_ambulance_id = ambulance.id
        emergency.assigned_hospital_id = hospital.id if hospital else None
        emergency.route = route_result.path
        emergency.eta_seconds = route_result.cost * AVG_SPEED_MS  # cost in metres
        emergency.dispatched_at = time.time()

        # Update ambulance
        ambulance.status = AmbulanceStatus.DISPATCHED
        ambulance.assigned_emergency_id = emergency.id
        ambulance.total_responses += 1
        ambulance.total_distance += route_result.cost

        self.emergency_queue.remove(emergency.id)

        self._metrics.append({
            "emergency_id": emergency.id,
            "severity": emergency.severity.value,
            "ambulance_id": ambulance.id,
            "route_cost": route_result.cost,
            "eta_seconds": emergency.eta_seconds,
            "nodes_explored": route_result.nodes_explored,
            "computation_ms": route_result.computation_time_ms,
            "wait_seconds": emergency.age_seconds(),
        })

    # ------------------------------------------------------------------
    def resolve_emergency(self, emergency_id: str) -> Optional[Emergency]:
        emergency = self.active_emergencies.pop(emergency_id, None)
        if not emergency:
            return None
        emergency.status = EmergencyStatus.RESOLVED
        emergency.resolved_at = time.time()
        if emergency.dispatched_at:
            emergency.response_time_seconds = emergency.resolved_at - emergency.created_at

        # Free ambulance
        if emergency.assigned_ambulance_id:
            amb = self.ambulances.get(emergency.assigned_ambulance_id)
            if amb:
                amb.status = AmbulanceStatus.AVAILABLE
                amb.assigned_emergency_id = None
                amb.current_node = emergency.node  # moved to scene

        # Update hospital
        if emergency.assigned_hospital_id:
            hosp = self.hospitals.get(emergency.assigned_hospital_id)
            if hosp:
                hosp.current_patients += 1

        self.resolved_emergencies.append(emergency)
        self._dispatch_next()  # process queue
        return emergency

    # ------------------------------------------------------------------
    def get_state(self) -> Dict:
        return {
            "ambulances": [a.to_dict() for a in self.ambulances.values()],
            "hospitals": [h.to_dict() for h in self.hospitals.values()],
            "active_emergencies": [e.to_dict() for e in self.active_emergencies.values()],
            "queue_length": len(self.emergency_queue),
            "resolved_count": len(self.resolved_emergencies),
            "metrics": self._get_performance_metrics(),
        }

    def _get_performance_metrics(self) -> Dict:
        if not self._metrics:
            return {}
        times = [m["response_time_seconds"] for m in self._metrics if "response_time_seconds" in m and m["response_time_seconds"]]
        eta_vals = [m["eta_seconds"] for m in self._metrics]
        costs = [m["route_cost"] for m in self._metrics]
        return {
            "total_dispatches": len(self._metrics),
            "avg_eta_seconds": round(sum(eta_vals) / len(eta_vals), 1) if eta_vals else 0,
            "avg_route_cost": round(sum(costs) / len(costs), 2) if costs else 0,
            "avg_computation_ms": round(
                sum(m["computation_ms"] for m in self._metrics) / len(self._metrics), 2
            ),
        }
