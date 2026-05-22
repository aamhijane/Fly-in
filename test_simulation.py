"""Test script for the drone routing simulation."""

from src.parser import MapParser
from src.pathfinding import Pathfinder
from src.simulation import Simulation


def run_test(map_path: str) -> None:
    """Parse, pathfind, schedule, simulate, and print results."""
    print(f"\n{'=' * 60}")
    print(f"Map: {map_path}")
    print(f"{'=' * 60}")

    map_data = MapParser.parse(map_path)
    print(f"Drones: {map_data.nb_drones}")
    print(f"Zones: {len(map_data.zones)}, "
          f"Connections: {len(map_data.connections)}")

    pathfinder = Pathfinder(map_data)
    pathfinder.compute_paths()

    sim = Simulation(map_data, pathfinder.paths)
    sim.run()
    output = sim.output_lines

    for line in output:
        print(f"  {line}")

    print(f"\n  Total turns: {len(output)}")


if __name__ == "__main__":
    maps = [
        "maps/easy/01_linear_path.txt",
        "maps/easy/02_simple_fork.txt",
        "maps/easy/03_basic_capacity.txt",
        "maps/medium/01_dead_end_trap.txt",
        "maps/medium/02_circular_loop.txt",
        "maps/medium/03_priority_puzzle.txt",
        "maps/hard/01_maze_nightmare.txt",
        "maps/hard/02_capacity_hell.txt",
        "maps/hard/03_ultimate_challenge.txt",
    ]

    for m in maps:
        run_test(m)
