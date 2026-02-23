import sys

from tools._registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "geo_midpoint",
        "description": "Calculate the geographic midpoint between two lat/lon coordinates.",
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


async def run(*, lat1: float, lon1: float, lat2: float, lon2: float, **kwargs) -> dict:
    return {
        "lat": (lat1 + lat2) / 2,
        "lon": (lon1 + lon2) / 2,
    }
