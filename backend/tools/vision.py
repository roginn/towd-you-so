import sys

from tools._registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "vision",
        "description": "Get a general-purpose description of an image.",
        "parameters": {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL of the image to describe",
                }
            },
            "required": ["image_url"],
        },
    },
}

register(DEFINITION, sys.modules[__name__])


async def run(**kwargs) -> dict:
    """Stub: general-purpose image description."""
    return {"description": "A parking sign on a metal pole next to a street."}
