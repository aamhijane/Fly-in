"""Dijkstra-based pathfinding with congestion-aware path distribution."""

import heapq
from src.models import MapData, ZoneType


class Pathfinder:
    """Finds cheapest paths from start to goal for all drones.

    Uses Dijkstra's algorithm with a congestion penalty: each time a
    zone is used by a drone, its effective cost increases slightly for
    subsequent drones. This distributes drones across multiple paths
    when the network topology allows it.
    """

    CONGESTION_PENALTY = 0.02

    def __init__(self, map_data: MapData):
        """Initialise with parsed map data.

        Args:
            map_data: Parsed map with zones, connections, adjacency.
        """
        self.map_data = map_data
        self.paths: dict[int, list[str]] = {}
        self._usage: dict[str, int] = {}

    def compute_paths(self) -> None:
        """Run Dijkstra once per drone, applying congestion penalties.

        After each drone's path is computed, every zone on that path
        gets its usage count incremented. The next drone will see a
        slightly higher cost for those zones, encouraging alternative
        routes.
        """
        start = self.map_data.start_hub.name
        goal = self.map_data.end_hub.name
        self._usage = {}

        for i in range(self.map_data.nb_drones):
            drone_id = i + 1
            path = self._dijkstra(start, goal)
            self.paths[drone_id] = path
            for zone in path:
                self._usage[zone] = self._usage.get(zone, 0) + 1

    def _dijkstra(self, start: str, goal: str) -> list[str]:
        """Return cheapest path from start to goal as list of zone names.

        Zone costs are: zone_type.value + congestion_penalty * usage_count.
        Start and end hubs are never penalised (all drones share them).

        Args:
            start: Starting zone name.
            goal: Destination zone name.

        Returns:
            List of zone names from start to goal, or empty list if
            no path exists.
        """
        if start == goal:
            return []

        parent: dict[str, str] = {}
        dist: dict[str, float] = {}
        pq: list[tuple[float, str]] = []

        start_cost = self.map_data.zones[start].zone_type.value
        dist[start] = start_cost
        heapq.heappush(pq, (start_cost, start))

        while pq:
            current_cost, zone_name = heapq.heappop(pq)

            if zone_name == goal:
                path: list[str] = []
                while zone_name:
                    path.append(zone_name)
                    zone_name = parent.get(zone_name, "")
                path.reverse()
                return path

            if current_cost != dist.get(zone_name, -1.0):
                continue

            current_zone = self.map_data.zones[zone_name]
            if current_zone.zone_type == ZoneType.BLOCKED:
                continue

            for n in self.map_data.adjacency[zone_name]:
                neighbor_zone = self.map_data.zones[n]
                if neighbor_zone.zone_type == ZoneType.BLOCKED:
                    continue

                base = neighbor_zone.zone_type.value
                penalty = (self._usage.get(n, 0) * self.CONGESTION_PENALTY
                           if n != start and n != goal else 0.0)
                new_cost = current_cost + base + penalty

                if n not in dist or new_cost < dist[n]:
                    dist[n] = new_cost
                    parent[n] = zone_name
                    heapq.heappush(pq, (new_cost, n))

        return []
