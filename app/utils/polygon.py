from shapely.geometry import Point, Polygon

from app.schemas.request import Coordinate


def assign_group_id(location: list[float], polygons: dict[str, Polygon]) -> int | None:
    coord = Coordinate.from_list(location)
    point = Point(coord.longitude, coord.latitude)
    for polygon_id, polygon in polygons.items():
        if polygon.contains(point):
            return polygon_id
    return None
