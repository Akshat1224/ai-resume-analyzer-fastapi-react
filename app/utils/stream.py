import asyncio


async def fake_progress_stream():

    steps = [
        "Uploading Resume...",
        "Extracting Text...",
        "Analyzing Resume...",
        "Generating ATS Score...",
        "Preparing Suggestions...",
        "Completed"
    ]

    for step in steps:
        yield {
            "event": "message",
            "data": step
        }

        await asyncio.sleep(1)