*This project has been created as part of the 42 curriculum by aamhijane.*

## Description

Fly-in is a drone routing simulation. A fleet of drones must travel from a start zone
to an end zone through a network of interconnected zones. Each zone type has a
different movement cost (normal = 1 turn, restricted = 2 turns, priority = 1 turn,
blocked = inaccessible). Zones and connections have limited capacity — only a certain
number of drones may occupy them simultaneously.

The goal is to route **all** drones from start to goal in the **fewest possible simulation
turns**, respecting all capacity constraints and zone movement rules.

The project is implemented in Python 3.10+ using only the standard library. It uses
Dijkstra's algorithm for pathfinding, a turn-based reservation system for conflict
resolution, and a terminal-based visualiser with ANSI colour codes.

## Instructions

### Prerequisites

- Python 3.10 or later
- `flake8` and `mypy` for linting (optional, for development)

### Installation

```bash
# Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Or use the Makefile
make install
```

### Running the simulation

```bash
python3 main.py maps/easy/01_linear_path.txt
```

Controls: `Ctrl+C` to stop the animation. The simulation auto-advances
with a 0.6-second delay between turns.

### Testing

```bash
python3 test_simulation.py
```

### Linting

```bash
make lint          # flake8 + mypy (standard flags)
make lint-strict   # flake8 + mypy --strict
```

## Algorithm

### Pathfinding: Dijkstra with congestion penalty

Each zone type has a numeric cost (`NORMAL = 1`, `RESTRICTED = 2`,
`PRIORITY = 1`, `BLOCKED = 999999`). Dijkstra's algorithm finds the
cheapest path from start to goal for each drone.

To distribute drones across multiple paths (instead of all taking the
same shortest route), a **congestion penalty** is applied: each time a
zone is used by a drone, its effective cost increases by 0.2 for the
next drone. This naturally pushes later drones toward alternative
routes when the topology allows it. The start and end hubs are never
penalised since all drones must share them.

- Complexity: O(E log V) per drone (E = connections, V = zones).
- Paths are **cached** after computation — each drone's path is
  computed once and reused during simulation.

### Scheduling: Reservation table

The scheduler processes drones in order of **shortest path first**
(drones with fewer zones to cross reserve their slots first, then
slower drones wait). A reservation table tracks per-turn occupancy
for every zone and connection:

- `occ_zone[zone_name][turn]` — how many drones occupy a zone on a
  given turn.
- `occ_conn[(a, b)][turn]` — how many drones traverse a connection.

When a drone wants to move to the next zone on its path, it checks
the reservation table. If either the connection or the destination
zone is full at that turn, the drone **waits** in its current zone
and tries again next turn.

**Zone type movement rules:**
- **Normal / Priority**: check capacity at turn T, move in 1 turn
  (occupy connection + destination at turn T).
- **Restricted**: check connection capacity at turn T AND destination
  capacity at turn T+1 before moving. Takes 2 turns (one on the
  connection, one arriving). Cannot wait on the connection.

### Visualiser

The visualiser uses only `print()`, `os.system("clear")`, and
`time.sleep()` — no external libraries are needed.

- Zones are laid out in a grid matching their (x, y) coordinates.
- **Green** = start/goal, **Red** = restricted, **Blue** = normal.
- Drone IDs (e.g., `D1`, `1,2,3+`) appear inside zone cells.
- Transit drones are listed as `D1 start→waypoint` below the grid.
- Movement output follows the subject format: `D1-zoneA D2-zoneB`.

## Resources

### References

- Dijkstra, E. W. (1959). *A note on two problems in connexion with
  graphs.* Numerische Mathematik, 1, 269–271.
- Python `heapq` documentation — priority queue implementation:
  https://docs.python.org/3/library/heapq.html
- PEP 257 — Docstring conventions:
  https://peps.python.org/pep-0257/
- PEP 484 — Type hints:
  https://peps.python.org/pep-0484/

### AI usage

This project was developed with assistance from an AI coding assistant.
AI was used for:

- **Code generation**: initial implementation of the parser, simulation
  engine, and visualiser. All AI-generated code was reviewed, tested,
  and modified before inclusion.
- **Debugging**: identifying the `arrive_turn` bug in the scheduler
  (infinite loop when waiting at normal zones) and the multi-drone
  rendering issue in the visualiser.
- **Refactoring**: simplifying the simulation from three classes
  (`ReservationTable`, `DroneScheduler`, `SimulationEngine`) into
  a single `Simulation` class.
- **Documentation**: drafting the README structure and docstring
  templates.

Every part of the code has been understood and validated through
testing and peer discussion. No AI-generated code was used without
full comprehension.

## Performance

| Map | Drones | Our turns | Target |
|---|---|---|---|
| 01_linear_path | 2 | 4 | ≤ 6 |
| 02_simple_fork | 3 | 5 | ≤ 6 |
| 03_basic_capacity | 4 | 6 | ≤ 8 |
| 01_dead_end_trap | 5 | 8 | ≤ 15 |
| 02_circular_loop | 6 | 11 | ≤ 20 |
| 03_priority_puzzle | 4 | 7 | ≤ 12 |
| 01_maze_nightmare | 8 | 14 | ≤ 45 |
| 02_capacity_hell | 12 | 18 | ≤ 60 |
| 03_ultimate_challenge | 15 | 26 | ≤ 35 |
| challenger (bonus) | 25 | 43 | 45 (record) |

All mandatory maps meet or beat the reference targets.
