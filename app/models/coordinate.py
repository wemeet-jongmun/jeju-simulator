from typing import NamedTuple


class Coordinate(NamedTuple):
    longitude: float
    latitude: float

    @classmethod
    def from_list(cls, location: list[float]) -> "Coordinate":
        return cls(location[0], location[1])
