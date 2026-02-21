import uuid


async def run_agent(
    uploaded_file_id: uuid.UUID | None = None,
) -> dict:
    """Run an internal LLM loop to analyze a parking sign image."""
    # TODO: replace with real vision call
    return {
        "text": (
            "No parking 7am-9am Mon-Fri. "
            "2-hour parking 9am-6pm Mon-Sat. "
            "No restrictions Sunday."
        )
    }
