"""Simplest possible terminal visualizer using print() and ANSI colors."""

import os
import time
from src.models import MapData, Zone, ZoneType


# ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"


class Visualizer:
    """Displays the simulation as a colored text grid in the terminal.

    Each turn clears the screen, draws the zone grid with drones,
    prints the movement output, and waits 0.6 seconds before the
    next turn. Simple and portable — no external libraries needed.
    """

    CELL_W = 8  # width of each zone cell in characters

    def __init__(self, map_data: MapData,
                 schedule: dict[int, list[tuple[int, str]]],
                 output_lines: list[str],
                 positions_per_turn: list[dict[int, str]]) -> None:
        """Store all data needed to animate the simulation.

        Args:
            map_data: Parsed map with zones and connections.
            schedule: Pre-computed turn-by-turn actions per drone.
            output_lines: Formatted "D1-zone D2-zone ..." per turn.
            positions_per_turn: {drone_id: zone_name} for each turn.
        """
        self.map_data = map_data
        self.schedule = schedule
        self.output_lines = output_lines
        self.positions_per_turn = positions_per_turn

        # Find the grid boundaries from zone coordinates
        zones_list = list(map_data.zones.values())
        self.min_x = min(z.x for z in zones_list)
        self.max_x = max(z.x for z in zones_list)
        self.min_y = min(z.y for z in zones_list)
        self.max_y = max(z.y for z in zones_list)
        self.width = self.max_x - self.min_x + 1
        self.height = self.max_y - self.min_y + 1

        # Build a 2D grid: grid[row][col] = Zone or None
        self.grid: list[list[Zone | None]] = [
            [None for _ in range(self.width)] for _ in range(self.height)
        ]
        for zone in zones_list:
            row = zone.y - self.min_y
            col = zone.x - self.min_x
            self.grid[row][col] = zone

        # Pre-compute which drones are in transit on each turn
        # transit_lookup[(drone_id, turn)] = (from_zone, to_zone)
        self.transit: dict[tuple[int, int], tuple[str, str]] = {}
        for drone_id, actions in schedule.items():
            for turn, action in actions:
                if "-" in action:
                    parts = action.split("-")
                    if len(parts) == 2:
                        self.transit[(drone_id, turn)] = (parts[0], parts[1])

        max_t = list(schedule.values())
        self.max_turn = max(a[-1][0] for a in max_t) if max_t else 0

    def zone_color(self, zone: Zone) -> str:
        """Return the ANSI color code based on metadata or type."""
        if zone.color:
            c = zone.color.lower()
            if c == "green":
                return GREEN
            if c == "red":
                return RED
            if c == "blue":
                return BLUE
            if c == "yellow":
                return YELLOW

        if (zone.name == self.map_data.start_hub.name
                or zone.name == self.map_data.end_hub.name):
            return GREEN
        if zone.zone_type == ZoneType.RESTRICTED:
            return RED
        return BLUE

    def render(self, turn: int,
               positions: dict[int, str]) -> None:
        """Clear the screen and draw one frame of the simulation.

        Args:
            turn: Current turn number (0 = initial state).
            positions: {drone_id: zone_name} for drones at zones this turn.
        """
        os.system("clear")
        print(f"{BOLD}=== Turn {turn} / {self.max_turn} ==={RESET}\n")

        # Group drones by zone (multiple drones can share one zone)
        zone_drones: dict[str, list[int]] = {}
        for did, zname in positions.items():
            if (did, turn) in self.transit:
                continue  # skip drones in transit (shown separately)
            if zname not in zone_drones:
                zone_drones[zname] = []
            zone_drones[zname].append(did)

        # Draw the grid row by row
        for row_idx in range(self.height):
            parts: list[str] = []
            for col_idx in range(self.width):
                zone = self.grid[row_idx][col_idx]
                if zone is None:
                    parts.append(" " * self.CELL_W)
                    continue

                drones = zone_drones.get(zone.name, [])
                color = self.zone_color(zone)

                if drones:
                    # Show drone IDs in the cell
                    label = self._drone_label(drones)
                else:
                    label = zone.name[:6]

                padded = f"{label:^{self.CELL_W - 1}} "
                parts.append(f"{color}{padded}{RESET}")

            print("".join(parts))

        print()

        # Show transit drones (moving on connections) as extra lines
        transit_lines: list[str] = []
        for (did, t), (fz, tz) in self.transit.items():
            if t == turn:
                transit_lines.append(f"D{did} {fz}→{tz}")
        if transit_lines:
            print("  " + "  ".join(transit_lines))

        # Show the movement output for this turn
        if turn > 0 and turn - 1 < len(self.output_lines):
            print(f"\n{BOLD}>>>{RESET} {self.output_lines[turn - 1]}")

    @staticmethod
    def _drone_label(drones: list[int]) -> str:
        """Format drone IDs for display inside a zone cell.

        Args:
            drones: List of drone IDs at this zone.

        Returns:
            Short string like "D1" or "1,2,3+".
        """
        if not drones:
            return ""
        if len(drones) == 1:
            return f"D{drones[0]}"
        ids = ",".join(str(d) for d in drones[:3])
        if len(drones) > 3:
            ids += "+"
        return ids

    def run(self) -> None:
        """Animate the full simulation turn by turn.

        Shows the initial state, waits 1 second, then animates each
        turn with a 0.6 second delay between frames.
        """
        # Show initial state (turn 0)
        init_pos = (self.positions_per_turn[0]
                    if self.positions_per_turn else {})
        self.render(0, init_pos)
        print(f"  {BOLD}Initial state — {len(init_pos)} drones"
              f" at start{RESET}")
        time.sleep(1.0)

        # Animate each turn
        for turn in range(1, self.max_turn + 1):
            time.sleep(0.6)
            pos = (self.positions_per_turn[turn]
                   if turn < len(self.positions_per_turn) else {})
            self.render(turn, pos)

        # Final summary
        print(f"\n{BOLD}Simulation complete in {self.max_turn} turns{RESET}")
        time.sleep(0.5)
