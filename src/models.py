from enum import IntEnum, Enum, auto
from typing import Optional
from dataclasses import dataclass, field


class ZoneType(IntEnum):
    NORMAL = 1
    RESTRICTED = 2
    PRIORITY = 3
    BLOCKED = 999_999


class DroneStatus(Enum):
    WAITING = auto()
    MOVING = auto()
    TRANSITING = auto()
    DELIVERED = auto()


@dataclass
class Zone:
    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    max_drones: int = 1
    color: Optional[str] = None


@dataclass
class Connection:
    zone_a: str
    zone_b: str
    max_link_capacity: int = 1


@dataclass
class MapData:
    nb_drones: int
    start_hub: Zone
    end_hub: Zone
    zones: dict[str, Zone]
    connections: list[Connection]
    adjacency: dict[str, list[str]]


@dataclass
class Drone:
    id: int
    current_zone: str
    status: DroneStatus = DroneStatus.WAITING
    transit_target: Optional[str] = None
    transit_timer: int = 0
    path: list[str] = field(default_factory=list)
