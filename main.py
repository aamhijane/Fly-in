"""Entry point for the drone routing simulation."""

import sys
from src.parser import MapParser, ParserError
from src.pathfinding import Pathfinder, PathfinderError
from src.simulation import Simulation
from src.visual import Visualizer


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 main.py <map_file>")
        sys.exit(1)

    map_path = sys.argv[1]

    try:
        map_data = MapParser.parse(map_path)
    except ParserError as e:
        print(e)
        sys.exit(1)

    pathfinder = Pathfinder(map_data)
    try:
        pathfinder.compute_paths()
    except PathfinderError as e:
        print(f"Error: {e}")
        sys.exit(1)

    sim = Simulation(map_data, pathfinder.paths)
    sim.run()

    max_turn = max(
        actions[-1][0] for actions in sim.schedule.values()
    )
    positions_per_turn: list[dict[int, str]] = [
        {} for _ in range(max_turn + 1)
    ]

    for drone_id, actions in sim.schedule.items():
        for turn, action in actions:
            if "-" not in action:
                positions_per_turn[turn][drone_id] = action

    for turn in range(1, max_turn + 1):
        for did, zone in positions_per_turn[turn - 1].items():
            if did not in positions_per_turn[turn]:
                positions_per_turn[turn][did] = zone

    visualizer = Visualizer(
        map_data, sim.schedule,
        sim.output_lines, positions_per_turn,
    )
    try:
        visualizer.run()
    except KeyboardInterrupt:
        print("==================================")
        print("========= Program closed =========")
        print("==================================")
        sys.exit(0)


if __name__ == "__main__":
    main()
