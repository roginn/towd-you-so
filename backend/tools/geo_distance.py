import math
import sys

from tools._registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "geo_distance",
        "description": "Calculate the distance between two lat/lon points using the Haversine formula.",
        "parameters": {
            "type": "object",
            "properties": {
                "lat1": {"type": "number", "description": "Latitude of point 1."},
                "lon1": {"type": "number", "description": "Longitude of point 1."},
                "lat2": {"type": "number", "description": "Latitude of point 2."},
                "lon2": {"type": "number", "description": "Longitude of point 2."},
            },
            "required": ["lat1", "lon1", "lat2", "lon2"],
        },
    },
}

register(DEFINITION, sys.modules[__name__])

EARTH_RADIUS_METERS = 6_371_000


async def run(*, lat1: float, lon1: float, lat2: float, lon2: float, **kwargs) -> dict:
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_meters = EARTH_RADIUS_METERS * c

    return {
        "distance_meters": round(distance_meters, 1),
        "distance_miles": round(distance_meters / 1609.344, 3),
    }
