"""
is_empty_or_comment:    skip blank/comment lines
parse_nb_drones:        read drone count
split_metadata:         extract [...] from line
read_metadata:          parse key=value pairs
zone_name_is_valid:     check name has no - or space
zone_name_error:        get error message for invalid name
is_duplicate_zone:      check zone already exists
zone_type_from_string:  convert string to ZoneType
parse_zone_line:        parse a zone line into Zone object
parse_connection_line:  parse a connection line
connection_key:         normalize a-b / b-a to same key
line_type:              identify what kind of line it is
check_zones_exist:      verify both zones in connection exist
add_zone:               validate + insert zone
build_adjacency:        build neighbor map from connections
MapParser.parse:        main orchestrator (calls the above)
"""

from typing import Optional
from src.models import Zone, Connection, MapData, ZoneType


class ParserError(Exception):
    def __init__(self, line: int, message: str) -> None:
        self.line = line
        self.message = message
        super().__init__(f"Error on line {line}: {message}")


def is_empty_or_comment(line: str) -> bool:
    return line == "" or line.startswith("#")


def parse_nb_drones(line: str, line_num: int) -> int:
    parts = line.split(":", 1)
    if len(parts) != 2:
        raise ParserError(line_num, "Invalid nb_drones format")
    val = parts[1].strip()
    try:
        n = int(val)
    except ValueError:
        raise ParserError(
            line_num,
            f"nb_drones must be a positive integer, got '{val}'",
        )
    if n <= 0:
        raise ParserError(
            line_num,
            f"nb_drones must be a positive integer, got '{val}'",
        )
    return n


def split_metadata(line: str) -> tuple[Optional[str], str]:
    start = line.find("[")
    if start == -1:
        return None, line.strip()
    end = line.find("]", start)
    if end == -1:
        return None, line.strip()
    meta = line[start + 1:end]
    clean = line[:start].strip()
    return meta, clean


def read_metadata(meta_str: Optional[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    if meta_str is None:
        return result
    for pair in meta_str.split():
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        result[k] = v
    return result


def zone_name_is_valid(name: str) -> bool:
    if "-" in name:
        return False
    if " " in name:
        return False
    return True


def zone_name_error(name: str) -> str:
    if "-" in name:
        return f"Zone name '{name}' contains invalid character '-'"
    if " " in name:
        return f"Zone name '{name}' contains invalid character ' '"
    return ""


def is_duplicate_zone(name: str, zones: dict[str, Zone]) -> bool:
    return name in zones


def zone_type_from_string(s: str) -> Optional[ZoneType]:
    types = {
        "normal": ZoneType.NORMAL,
        "restricted": ZoneType.RESTRICTED,
        "priority": ZoneType.PRIORITY,
        "blocked": ZoneType.BLOCKED,
    }
    return types.get(s)


def parse_zone_line(prefix: str, line: str, meta: dict[str, str],
                    line_num: int) -> Zone:
    rest = line[len(prefix):].strip()
    parts = rest.split()
    if len(parts) < 3:
        raise ParserError(
            line_num,
            "Invalid zone format. Expected: <name> <x> <y> [metadata]",
        )
    name = parts[0]
    try:
        x = int(parts[1])
        y = int(parts[2])
    except ValueError:
        raise ParserError(
            line_num, f"Invalid coordinates for zone '{name}'"
        )

    zone_type = ZoneType.NORMAL
    max_drones = 1
    color = None

    if "zone" in meta:
        zt = meta["zone"].lower()
        t = zone_type_from_string(zt)
        if t is None:
            raise ParserError(
                line_num,
                f"Invalid zone type '{meta['zone']}'. "
                "Must be: normal, restricted, priority, blocked",
            )
        zone_type = t

    if "max_drones" in meta:
        try:
            md = int(meta["max_drones"])
        except ValueError:
            raise ParserError(
                line_num,
                "max_drones must be a positive integer, "
                f"got '{meta['max_drones']}'",
            )
        if md <= 0:
            raise ParserError(
                line_num,
                "max_drones must be a positive integer, "
                f"got '{meta['max_drones']}'",
            )
        max_drones = md

    if "color" in meta:
        color = meta["color"]

    return Zone(name, x, y, zone_type, max_drones, color)


def parse_connection_line(line: str, meta: dict[str, str],
                          line_num: int) -> Connection:
    rest = line[len("connection:"):].strip()
    if "-" not in rest:
        raise ParserError(
            line_num,
            "Invalid connection format. Expected: <zone1>-<zone2>",
        )
    a, b = rest.split("-", 1)

    cap = 1
    if "max_link_capacity" in meta:
        try:
            cap = int(meta["max_link_capacity"])
        except ValueError:
            raise ParserError(
                line_num,
                "max_link_capacity must be a positive integer, "
                f"got '{meta['max_link_capacity']}'",
            )
        if cap <= 0:
            raise ParserError(
                line_num,
                "max_link_capacity must be a positive integer, "
                f"got '{meta['max_link_capacity']}'",
            )

    return Connection(a, b, cap)


def connection_key(a: str, b: str) -> str:
    if a < b:
        return a + "-" + b
    return b + "-" + a


def line_type(clean: str) -> str:
    if clean.startswith("start_hub:"):
        return "start_hub"
    if clean.startswith("end_hub:"):
        return "end_hub"
    if clean.startswith("hub:"):
        return "hub"
    if clean.startswith("connection:"):
        return "connection"
    return "unknown"


def check_zones_exist(a: str, b: str, zones: dict[str, Zone],
                      line_num: int) -> None:
    if a not in zones:
        raise ParserError(
            line_num, f"Undefined zone '{a}' in connection"
        )
    if b not in zones:
        raise ParserError(
            line_num, f"Undefined zone '{b}' in connection"
        )


def add_zone(zones: dict[str, Zone], z: Zone, line_num: int) -> None:
    if not zone_name_is_valid(z.name):
        msg = zone_name_error(z.name)
        raise ParserError(line_num, msg)
    if is_duplicate_zone(z.name, zones):
        raise ParserError(
            line_num, f"Duplicate zone name '{z.name}'"
        )
    zones[z.name] = z


def build_adjacency(zones: dict[str, Zone],
                    connections: list[Connection]) -> dict[str, list[str]]:
    adj: dict[str, list[str]] = {name: [] for name in zones}
    for c in connections:
        adj[c.zone_a].append(c.zone_b)
        adj[c.zone_b].append(c.zone_a)
    return adj


class MapParser:

    @staticmethod
    def parse(filepath: str) -> MapData:
        with open(filepath, "r") as f:
            lines = f.readlines()

        start_hub: Optional[Zone] = None
        end_hub: Optional[Zone] = None
        zones: dict[str, Zone] = {}
        connections: list[Connection] = []
        nb_drones = 0
        nb_drones_line = 0
        first = True
        seen_conns: dict[str, int] = {}

        for i, raw in enumerate(lines, 1):
            line = raw.strip()
            if is_empty_or_comment(line):
                continue

            if first:
                first = False
                if not line.startswith("nb_drones:"):
                    raise ParserError(
                        i, "First definition must be nb_drones"
                    )
                nb_drones = parse_nb_drones(line, i)
                nb_drones_line = i
                continue

            meta_str, clean = split_metadata(line)
            meta = read_metadata(meta_str)
            kind = line_type(clean)

            if kind == "start_hub":
                z = parse_zone_line("start_hub:", clean, meta, i)
                if start_hub is not None:
                    raise ParserError(
                        i,
                        "start_hub already defined "
                        f"at line {nb_drones_line}",
                    )
                add_zone(zones, z, i)
                start_hub = z

            elif kind == "end_hub":
                z = parse_zone_line("end_hub:", clean, meta, i)
                add_zone(zones, z, i)
                end_hub = z

            elif kind == "hub":
                z = parse_zone_line("hub:", clean, meta, i)
                add_zone(zones, z, i)

            elif kind == "connection":
                conn = parse_connection_line(clean, meta, i)
                check_zones_exist(
                    conn.zone_a, conn.zone_b, zones, i
                )
                key = connection_key(conn.zone_a, conn.zone_b)
                if key in seen_conns:
                    raise ParserError(
                        i,
                        f"Duplicate connection "
                        f"'{conn.zone_a}-{conn.zone_b}' "
                        f"already at line {seen_conns[key]}",
                    )
                seen_conns[key] = i
                connections.append(conn)

            else:
                raise ParserError(
                    i, f"Unknown definition: '{line.split(':')[0]}'"
                )

        if start_hub is None:
            raise ParserError(0, "Missing required start_hub")
        if end_hub is None:
            raise ParserError(0, "Missing required end_hub")

        adj = build_adjacency(zones, connections)

        return MapData(
            nb_drones=nb_drones,
            start_hub=start_hub,
            end_hub=end_hub,
            zones=zones,
            connections=connections,
            adjacency=adj,
        )
