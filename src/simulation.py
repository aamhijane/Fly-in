"""Schedule drones, resolve conflicts, produce turn output."""

from src.models import MapData, ZoneType


class Simulation:
    """Runs the full simulation.

    Handles three tasks:
    1. Track zone/connection occupancy (reservation table)
    2. Build a conflict-free turn schedule for each drone
    3. Produce the final output lines

    Usage:
        sim = Simulation(map_data, pathfinder.paths)
        sim.run()
        # sim.output_lines  -> list of strings like "D1-zoneA D2-zoneB"
    """

    def __init__(self, map_data: MapData,
                 paths: dict[int, list[str]]) -> None:
        """Initialise simulation with map data and pre-computed paths.

        Args:
            map_data: Parsed map with zones, connections, and capacities.
            paths: Per-drone list of zone names from start to goal.
        """
        self.map_data = map_data
        self.paths = paths
        self.schedule: dict[int, list[tuple[int, str]]] = {}
        self.output_lines: list[str] = []
        self.max_turn = 0

        # Build connection capacity lookup for fast access
        # conn_cap[(zoneA, zoneB)] = max_link_capacity (normalised key)
        self.conn_cap: dict[tuple[str, str], int] = {}
        for conn in map_data.connections:
            key = (conn.zone_a, conn.zone_b)
            if conn.zone_a > conn.zone_b:
                key = (conn.zone_b, conn.zone_a)
            self.conn_cap[key] = conn.max_link_capacity

        # Occupancy trackers: occ_zone[zone_name][turn] = count
        self.occ_zone: dict[str, dict[int, int]] = {}
        # occ_conn[(a,b)][turn] = count  (key always normalised a<b)
        self.occ_conn: dict[tuple[str, str], dict[int, int]] = {}

    def _conn_key(self, a: str, b: str) -> tuple[str, str]:
        """Return a normalised connection key (a ≤ b).

        Ensures (start,waypoint1) and (waypoint1,start)
        map to the same key.
        """
        if a < b:
            return (a, b)
        return (b, a)

    def _zone_free(self, zone: str, turn: int) -> bool:
        """Check if the zone has free capacity at a given turn."""
        used = self.occ_zone.get(zone, {}).get(turn, 0)
        return used < self.map_data.zones[zone].max_drones

    def _conn_free(self, a: str, b: str, turn: int) -> bool:
        """Check if the connection has free capacity at a given turn."""
        key = self._conn_key(a, b)
        used = self.occ_conn.get(key, {}).get(turn, 0)
        cap = self.conn_cap.get(key, 1)
        return used < cap

    def _reserve_zone(self, zone: str, turn: int) -> None:
        """Mark one drone occupying a zone at a turn."""
        if zone not in self.occ_zone:
            self.occ_zone[zone] = {}
        self.occ_zone[zone][turn] = self.occ_zone[zone].get(turn, 0) + 1

    def _reserve_conn(self, a: str, b: str, turn: int) -> None:
        """Mark one drone occupying a connection at a turn."""
        key = self._conn_key(a, b)
        if key not in self.occ_conn:
            self.occ_conn[key] = {}
        self.occ_conn[key][turn] = self.occ_conn[key].get(turn, 0) + 1

    def _release_zone(self, zone: str, turn: int) -> None:
        """Remove one drone from a zone at a turn."""
        if zone in self.occ_zone and turn in self.occ_zone[zone]:
            self.occ_zone[zone][turn] -= 1

    def run(self) -> None:
        """Build the schedule then produce output lines."""
        self._build_schedule()
        self._build_output()

    def _build_schedule(self) -> None:
        """Compute the turn-by-turn schedule for every drone.

        Drones with shorter paths are scheduled first (they reserve
        slots first, and slower drones wait for free capacity).
        """
        sorted_drones = sorted(
            self.paths.items(),
            key=lambda item: len(item[1]),
        )
        for drone_id, path in sorted_drones:
            self.schedule[drone_id] = self._simulate_drone(drone_id, path)

        if self.schedule:
            self.max_turn = max(
                actions[-1][0] for actions in self.schedule.values()
            )

    def _simulate_drone(self, drone_id: int,
                        path: list[str]) -> list[tuple[int, str]]:
        """Walk one drone through its path, waiting for free capacity.

        Args:
            drone_id: Drone identifier (for logging).
            path: List of zone names from start to goal.

        Returns:
            List of (turn, action) pairs.
        """
        zones = self.map_data.zones
        results: list[tuple[int, str]] = [(0, path[0])]
        current = path[0]
        turn = 0
        self._reserve_zone(current, turn)

        for next_zone in path[1:]:
            turn += 1
            restricted = zones[next_zone].zone_type == ZoneType.RESTRICTED
            # For restricted zones, we must check destination capacity
            # at turn+1 (we cannot wait on the connection)
            arrive_turn = turn + (1 if restricted else 0)

            # Wait until both connection and destination are free
            while True:
                conn_ok = self._conn_free(current, next_zone, turn)
                zone_ok = self._zone_free(next_zone, arrive_turn)
                if conn_ok and zone_ok:
                    break
                self._reserve_zone(current, turn)
                results.append((turn, current))
                turn += 1
                arrive_turn = turn + (1 if restricted else 0)

            # Occupy the connection and leave current zone
            self._reserve_conn(current, next_zone, turn)
            self._release_zone(current, turn)

            if restricted:
                # Transit takes one full turn on the connection
                results.append((turn, f"{current}-{next_zone}"))
                turn += 1

            # Arrive at the next zone
            self._reserve_zone(next_zone, turn)
            results.append((turn, next_zone))
            current = next_zone

        return results

    def _build_output(self) -> None:
        """Walk the schedule and produce output strings.

        Each output line lists drones that moved this turn:
        "D1-zoneA D2-zoneB"
        Drones that are waiting or delivered are omitted.
        """
        goal = self.map_data.end_hub.name
        delivered: set[int] = set()
        prev_actions: dict[int, str] = {
            did: actions[0][1] for did, actions in self.schedule.items()
        }

        for turn in range(1, self.max_turn + 1):
            moved: list[str] = []

            for drone_id in sorted(self.schedule):
                if drone_id in delivered:
                    continue

                current_action = None
                for t, action in self.schedule[drone_id]:
                    if t == turn:
                        current_action = action
                        break

                if current_action is None:
                    continue

                if current_action != prev_actions[drone_id]:
                    moved.append(f"D{drone_id}-{current_action}")
                    prev_actions[drone_id] = current_action

                if current_action == goal:
                    delivered.add(drone_id)

            if moved:
                self.output_lines.append(" ".join(moved))
