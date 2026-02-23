import math
import sys

from config import settings
from tools._registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_nearby_signs",
        "description": (
            "Search for saved parking sign locations near a given point. "
            "Returns results sorted by distance with pagination."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "Latitude of the search center.",
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude of the search center.",
                },
                "radius_meters": {
                    "type": "number",
                    "description": "Search radius in meters (default 1600, ~1 mile).",
                },
                "page": {
                    "type": "integer",
                    "description": "Page number (default 1).",
                },
                "page_size": {
                    "type": "integer",
                    "description": "Results per page (default 5).",
                },
            },
            "required": ["latitude", "longitude"],
        },
    },
}

register(DEFINITION, sys.modules[__name__])

EARTH_RADIUS_METERS = 6_371_000


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_METERS * c


async def run(
    *,
    latitude: float,
    longitude: float,
    radius_meters: float = 1600,
    page: int = 1,
    page_size: int = 5,
    **kwargs,
) -> dict:
    from db.database import get_db
    from db.repository import list_parking_sign_locations, get_uploaded_file

    async with get_db() as db:
        all_locations = await list_parking_sign_locations(db)

        results = []
        for loc in all_locations:
            dist = _haversine(latitude, longitude, loc.latitude, loc.longitude)
            if dist <= radius_meters:
                # Build image URL from uploaded file's storage key
                uploaded_file = await get_uploaded_file(db, loc.uploaded_file_id)
                image_url = ""
                if uploaded_file:
                    image_url = f"{settings.BASE_URL}/uploads/{uploaded_file.storage_key}"

                results.append({
                    "id": str(loc.id),
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "description": loc.description,
                    "sign_text": loc.sign_text,
                    "distance_meters": round(dist, 1),
                    "distance_miles": round(dist / 1609.344, 3),
                    "image_url": image_url,
                })

    results.sort(key=lambda r: r["distance_meters"])

    total_results = len(results)
    total_pages = max(1, math.ceil(total_results / page_size))
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "results": results[start:end],
        "page": page,
        "total_pages": total_pages,
        "total_results": total_results,
    }
