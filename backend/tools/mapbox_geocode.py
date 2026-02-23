import json
import logging
import sys
import urllib.parse
import urllib.request

from config import settings
from tools._registry import register

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://api.mapbox.com/search/geocode/v6/forward"

DEFINITION = {
    "type": "function",
    "function": {
        "name": "mapbox_geocode",
        "description": (
            "Forward-geocode a location query using Mapbox. "
            "Returns latitude, longitude, full address, and name for the best match."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The location to geocode, e.g. '20th St & Illinois St, San Francisco'.",
                },
                "proximity": {
                    "type": "string",
                    "description": "Optional 'lon,lat' string to bias results toward a location.",
                },
            },
            "required": ["query"],
        },
    },
}

register(DEFINITION, sys.modules[__name__])


async def run(*, query: str, proximity: str | None = None, **kwargs) -> dict:
    token = settings.MAPBOX_ACCESS_TOKEN
    if not token:
        return {"error": "MAPBOX_ACCESS_TOKEN is not configured"}

    params = {
        "q": query,
        "access_token": token,
        "limit": 1,
        "types": "address,street",
    }
    if proximity:
        params["proximity"] = proximity

    url = f"{GEOCODE_URL}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        logger.exception("Mapbox geocode request failed")
        return {"error": str(e)}

    features = data.get("features", [])
    if not features:
        return {"error": f"No results found for '{query}'"}

    feature = features[0]
    coords = feature["geometry"]["coordinates"]
    props = feature.get("properties", {})

    return {
        "lat": coords[1],
        "lon": coords[0],
        "full_address": props.get("full_address", ""),
        "name": props.get("name", ""),
    }
