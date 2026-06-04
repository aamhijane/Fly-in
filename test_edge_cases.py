"""Comprehensive edge-case and validation tests for Fly-in."""

import os
import sys
import tempfile
from typing import Optional

from src.parser import MapParser, ParserError
from src.pathfinding import Pathfinder, PathfinderError
from src.simulation import Simulation

# ── Helpers ──────────────────────────────────────────────────

PASS = "\033[32m✓ PASS\033[0m"
FAIL = "\033[31m✗ FAIL\033[0m"

passed = 0
failed = 0


def _write_map(content: str) -> str:
    """Write map content to a temporary file and return the path."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


def expect_parser_error(label: str, content: str,
                        keyword: Optional[str] = None) -> None:
    """Expect MapParser.parse to raise ParserError."""
    global passed, failed
    path = _write_map(content)
    try:
        MapParser.parse(path)
        print(f"  {FAIL}  {label} — expected ParserError, got none")
        failed += 1
    except ParserError as e:
        if keyword and keyword.lower() not in str(e).lower():
            print(f"  {FAIL}  {label} — got ParserError but missing "
                  f"keyword '{keyword}': {e}")
            failed += 1
        else:
            print(f"  {PASS}  {label}")
            passed += 1
    except Exception as e:
        print(f"  {FAIL}  {label} — unexpected error: {type(e).__name__}: {e}")
        failed += 1
    finally:
        os.unlink(path)


def expect_pathfinder_error(label: str, content: str) -> None:
    """Expect Pathfinder.compute_paths to raise PathfinderError."""
    global passed, failed
    path = _write_map(content)
    try:
        map_data = MapParser.parse(path)
        pf = Pathfinder(map_data)
        pf.compute_paths()
        print(f"  {FAIL}  {label} — expected PathfinderError, got none")
        failed += 1
    except PathfinderError:
        print(f"  {PASS}  {label}")
        passed += 1
    except Exception as e:
        print(f"  {FAIL}  {label} — unexpected error: {type(e).__name__}: {e}")
        failed += 1
    finally:
        os.unlink(path)


def expect_success(label: str, content: str) -> Optional[Simulation]:
    """Expect a full parse → pathfind → simulate to succeed."""
    global passed, failed
    path = _write_map(content)
    try:
        map_data = MapParser.parse(path)
        pf = Pathfinder(map_data)
        pf.compute_paths()
        sim = Simulation(map_data, pf.paths)
        sim.run()
        print(f"  {PASS}  {label} — {len(sim.output_lines)} turns")
        passed += 1
        return sim
    except Exception as e:
        print(f"  {FAIL}  {label} — {type(e).__name__}: {e}")
        failed += 1
        return None
    finally:
        os.unlink(path)


def run_map_file(label: str, map_path: str,
                 max_turns: int) -> None:
    """Run a provided map file and check turn count."""
    global passed, failed
    try:
        map_data = MapParser.parse(map_path)
        pf = Pathfinder(map_data)
        pf.compute_paths()
        sim = Simulation(map_data, pf.paths)
        sim.run()
        turns = len(sim.output_lines)
        if turns <= max_turns:
            print(f"  {PASS}  {label} — {turns} turns "
                  f"(limit: {max_turns})")
            passed += 1
        else:
            print(f"  {FAIL}  {label} — {turns} turns "
                  f"exceeds limit of {max_turns}")
            failed += 1
    except Exception as e:
        print(f"  {FAIL}  {label} — {type(e).__name__}: {e}")
        failed += 1


# ── Test Groups ──────────────────────────────────────────────

def test_parser_errors() -> None:
    """Test that malformed map files produce clean errors."""
    print("\n\033[1m[1/5] Parser Error Handling\033[0m")

    # Missing nb_drones
    expect_parser_error(
        "Missing nb_drones",
        "start_hub: s 0 0\nend_hub: g 1 0\nconnection: s-g\n",
        "nb_drones",
    )

    # nb_drones is zero
    expect_parser_error(
        "nb_drones is zero",
        "nb_drones: 0\nstart_hub: s 0 0\nend_hub: g 1 0\n",
        "positive",
    )

    # nb_drones is negative
    expect_parser_error(
        "nb_drones is negative",
        "nb_drones: -3\nstart_hub: s 0 0\nend_hub: g 1 0\n",
        "positive",
    )

    # nb_drones is not a number
    expect_parser_error(
        "nb_drones is text",
        "nb_drones: abc\nstart_hub: s 0 0\nend_hub: g 1 0\n",
        "positive",
    )

    # Missing start_hub
    expect_parser_error(
        "Missing start_hub",
        "nb_drones: 1\nend_hub: g 1 0\n",
        "start_hub",
    )

    # Missing end_hub
    expect_parser_error(
        "Missing end_hub",
        "nb_drones: 1\nstart_hub: s 0 0\n",
        "end_hub",
    )

    # Duplicate zone name
    expect_parser_error(
        "Duplicate zone name",
        ("nb_drones: 1\n"
         "start_hub: dup 0 0\n"
         "end_hub: dup 1 0\n"),
        "duplicate",
    )

    # Zone name with hyphen
    expect_parser_error(
        "Zone name contains hyphen",
        ("nb_drones: 1\n"
         "start_hub: bad-name 0 0\n"
         "end_hub: g 1 0\n"),
        "invalid character",
    )

    # Duplicate connection
    expect_parser_error(
        "Duplicate connection",
        ("nb_drones: 1\n"
         "start_hub: s 0 0\n"
         "end_hub: g 1 0\n"
         "connection: s-g\n"
         "connection: g-s\n"),
        "duplicate",
    )

    # Connection references undefined zone
    expect_parser_error(
        "Undefined zone in connection",
        ("nb_drones: 1\n"
         "start_hub: s 0 0\n"
         "end_hub: g 1 0\n"
         "connection: s-phantom\n"),
        "undefined",
    )

    # Invalid zone coordinates
    expect_parser_error(
        "Invalid zone coordinates",
        ("nb_drones: 1\n"
         "start_hub: s abc def\n"
         "end_hub: g 1 0\n"),
        "coordinates",
    )

    # Invalid zone type
    expect_parser_error(
        "Invalid zone type",
        ("nb_drones: 1\n"
         "start_hub: s 0 0\n"
         "hub: mid 1 0 [zone=flying]\n"
         "end_hub: g 2 0\n"),
        "invalid zone type",
    )

    # Invalid max_drones value
    expect_parser_error(
        "Invalid max_drones value",
        ("nb_drones: 1\n"
         "start_hub: s 0 0 [max_drones=0]\n"
         "end_hub: g 1 0\n"),
        "positive",
    )

    # File does not exist
    expect_parser_error(
        "File does not exist",
        "",
    )
    # Special case: test with a non-existent path directly
    global passed, failed
    try:
        MapParser.parse("/tmp/this_file_does_not_exist_12345.txt")
        print(f"  {FAIL}  Non-existent file path — expected error")
        failed += 1
    except ParserError:
        print(f"  {PASS}  Non-existent file path")
        passed += 1
    except Exception as e:
        print(f"  {FAIL}  Non-existent file path — "
              f"{type(e).__name__}: {e}")
        failed += 1


def test_pathfinding_errors() -> None:
    """Test that unreachable goals produce clean errors."""
    print("\n\033[1m[2/5] Pathfinding Error Handling\033[0m")

    # No connections at all
    expect_pathfinder_error(
        "No connections (isolated zones)",
        ("nb_drones: 1\n"
         "start_hub: s 0 0\n"
         "end_hub: g 1 0\n"),
    )

    # All paths blocked
    expect_pathfinder_error(
        "Only path goes through blocked zone",
        ("nb_drones: 1\n"
         "start_hub: s 0 0\n"
         "hub: wall 1 0 [zone=blocked]\n"
         "end_hub: g 2 0\n"
         "connection: s-wall\n"
         "connection: wall-g\n"),
    )


def test_valid_simple_maps() -> None:
    """Test simple valid maps that should succeed."""
    print("\n\033[1m[3/5] Valid Simple Maps\033[0m")

    # Minimal map: 1 drone, direct connection
    sim = expect_success(
        "Minimal map (1 drone, direct path)",
        ("nb_drones: 1\n"
         "start_hub: s 0 0\n"
         "end_hub: g 1 0\n"
         "connection: s-g\n"),
    )
    if sim:
        assert len(sim.output_lines) == 1, "Should take 1 turn"

    # Two drones, one path, capacity 1 (must queue)
    expect_success(
        "Two drones, single lane (queuing)",
        ("nb_drones: 2\n"
         "start_hub: s 0 0\n"
         "hub: mid 1 0\n"
         "end_hub: g 2 0\n"
         "connection: s-mid\n"
         "connection: mid-g\n"),
    )

    # Map with comments and blank lines
    expect_success(
        "Map with comments and blank lines",
        ("# This is a comment\n"
         "\n"
         "nb_drones: 1\n"
         "\n"
         "# Define zones\n"
         "start_hub: s 0 0\n"
         "end_hub: g 1 0\n"
         "\n"
         "# Connections\n"
         "connection: s-g\n"),
    )

    # Restricted zone (2-turn transit)
    expect_success(
        "Restricted zone (2-turn crossing)",
        ("nb_drones: 1\n"
         "start_hub: s 0 0\n"
         "hub: slow 1 0 [zone=restricted]\n"
         "end_hub: g 2 0\n"
         "connection: s-slow\n"
         "connection: slow-g\n"),
    )

    # Priority zone (should be preferred)
    expect_success(
        "Priority zone routing",
        ("nb_drones: 1\n"
         "start_hub: s 0 0\n"
         "hub: fast 1 0 [zone=priority]\n"
         "hub: norm 1 1\n"
         "end_hub: g 2 0\n"
         "connection: s-fast\n"
         "connection: s-norm\n"
         "connection: fast-g\n"
         "connection: norm-g\n"),
    )

    # Multiple drones, forking paths
    expect_success(
        "Three drones, two paths (congestion spreading)",
        ("nb_drones: 3\n"
         "start_hub: s 0 0 [max_drones=3]\n"
         "hub: pathA 1 0\n"
         "hub: pathB 1 1\n"
         "end_hub: g 2 0 [max_drones=3]\n"
         "connection: s-pathA\n"
         "connection: s-pathB\n"
         "connection: pathA-g\n"
         "connection: pathB-g\n"),
    )

    # High capacity zone
    expect_success(
        "High capacity zone (5 drones, capacity 5)",
        ("nb_drones: 5\n"
         "start_hub: s 0 0 [max_drones=5]\n"
         "hub: wide 1 0 [max_drones=5]\n"
         "end_hub: g 2 0 [max_drones=5]\n"
         "connection: s-wide [max_link_capacity=5]\n"
         "connection: wide-g [max_link_capacity=5]\n"),
    )


def test_simulation_rules() -> None:
    """Test that simulation respects capacity and zone rules."""
    print("\n\033[1m[4/5] Simulation Rule Validation\033[0m")

    global passed, failed

    # Test: No drone exceeds zone capacity at any turn
    content = (
        "nb_drones: 4\n"
        "start_hub: s 0 0 [max_drones=4]\n"
        "hub: bottle 1 0\n"
        "end_hub: g 2 0 [max_drones=4]\n"
        "connection: s-bottle\n"
        "connection: bottle-g\n"
    )
    path = _write_map(content)
    try:
        map_data = MapParser.parse(path)
        pf = Pathfinder(map_data)
        pf.compute_paths()
        sim = Simulation(map_data, pf.paths)
        sim.run()

        # Check zone capacity is never exceeded
        violation = False
        for zone_name, turns in sim.occ_zone.items():
            zone = map_data.zones[zone_name]
            # Skip start/end hubs (infinite capacity)
            if (zone_name == map_data.start_hub.name
                    or zone_name == map_data.end_hub.name):
                continue
            for turn, count in turns.items():
                if count > zone.max_drones:
                    print(f"  {FAIL}  Zone capacity — "
                          f"'{zone_name}' has {count} drones "
                          f"at turn {turn} "
                          f"(max: {zone.max_drones})")
                    violation = True
                    failed += 1
                    break
            if violation:
                break
        if not violation:
            print(f"  {PASS}  Zone capacity never exceeded")
            passed += 1

        # Check all drones reach the goal
        goal = map_data.end_hub.name
        all_delivered = True
        for drone_id, actions in sim.schedule.items():
            last_action = actions[-1][1]
            if last_action != goal:
                print(f"  {FAIL}  Drone {drone_id} did not "
                      f"reach goal (ended at '{last_action}')")
                all_delivered = False
                failed += 1
                break
        if all_delivered:
            print(f"  {PASS}  All drones reach the goal")
            passed += 1

    except Exception as e:
        print(f"  {FAIL}  Simulation rules — "
              f"{type(e).__name__}: {e}")
        failed += 1
    finally:
        os.unlink(path)


def test_provided_maps() -> None:
    """Test all provided map files meet their turn limits."""
    print("\n\033[1m[5/5] Provided Map Files\033[0m")

    targets = [
        ("Easy 01: linear_path", "maps/easy/01_linear_path.txt", 6),
        ("Easy 02: simple_fork", "maps/easy/02_simple_fork.txt", 6),
        ("Easy 03: basic_capacity",
         "maps/easy/03_basic_capacity.txt", 8),
        ("Medium 01: dead_end_trap",
         "maps/medium/01_dead_end_trap.txt", 15),
        ("Medium 02: circular_loop",
         "maps/medium/02_circular_loop.txt", 20),
        ("Medium 03: priority_puzzle",
         "maps/medium/03_priority_puzzle.txt", 12),
        ("Hard 01: maze_nightmare",
         "maps/hard/01_maze_nightmare.txt", 45),
        ("Hard 02: capacity_hell",
         "maps/hard/02_capacity_hell.txt", 60),
        ("Hard 03: ultimate_challenge",
         "maps/hard/03_ultimate_challenge.txt", 35),
    ]

    for label, map_path, max_turns in targets:
        if os.path.exists(map_path):
            run_map_file(label, map_path, max_turns)
        else:
            print(f"  {FAIL}  {label} — file not found: {map_path}")


# ── Main ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n\033[1m" + "=" * 60)
    print("  Fly-in — Edge Case & Validation Tests")
    print("=" * 60 + "\033[0m")

    test_parser_errors()
    test_pathfinding_errors()
    test_valid_simple_maps()
    test_simulation_rules()
    test_provided_maps()

    print(f"\n\033[1m{'=' * 60}")
    total = passed + failed
    print(f"  Results: {passed}/{total} passed, "
          f"{failed} failed")
    print(f"{'=' * 60}\033[0m\n")

    sys.exit(1 if failed else 0)
