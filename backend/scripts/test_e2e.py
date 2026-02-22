"""End-to-end test: create session, upload image, send message, get OCR result."""

import asyncio
import json
import sys
from glob import glob
from pathlib import Path

import httpx

BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"

# Pick a test image
uploads_dir = Path(__file__).parent.parent / "uploads"
images = sorted(glob(str(uploads_dir / "*.jpeg"))) + sorted(glob(str(uploads_dir / "*.jpg")))
if not images:
    print("ERROR: No images in uploads/")
    sys.exit(1)
image_path = images[0]
print(f"Using image: {image_path}")


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=10) as client:
        # 1. Create session
        resp = await client.post("/api/sessions")
        resp.raise_for_status()
        session_id = resp.json()["session_id"]
        print(f"Session: {session_id}")

        # 2. Upload image
        with open(image_path, "rb") as f:
            resp = await client.post(
                "/api/upload",
                files={"file": (Path(image_path).name, f, "image/jpeg")},
            )
        resp.raise_for_status()
        upload = resp.json()
        file_id = upload["file_id"]
        print(f"Uploaded: file_id={file_id}, url={upload['url']}")

    # 3. Connect websocket, send message, collect responses
    import websockets

    uri = f"{WS_BASE}/ws/{session_id}"
    print(f"Connecting to {uri} ...")

    async with websockets.connect(uri) as ws:
        msg = {"content": "Can I park here right now?", "file_id": file_id}
        print(f"Sending: {json.dumps(msg)}")
        await ws.send(json.dumps(msg))

        # Collect responses until turn_complete or timeout
        full_content = ""
        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=120)
                data = json.loads(raw)
                msg_type = data.get("type")

                if msg_type == "entry":
                    entry = data["entry"]
                    kind = entry.get("kind")
                    status = entry.get("status")
                    print(f"  [{kind}] status={status}")
                    if kind == "tool_call":
                        print(f"    tool: {entry['data'].get('tool_name')} args: {json.dumps(entry['data'].get('arguments', {}))}")
                    elif kind == "tool_result":
                        result_data = entry.get("data", {}).get("result", {})
                        print(f"    result: {json.dumps(result_data)[:500]}")
                    elif kind == "assistant_message":
                        content = entry.get("data", {}).get("content", "")
                        if content:
                            full_content = content
                            print(f"    content: {content[:300]}")
                elif msg_type == "content_delta":
                    text = data.get("text", "")
                    sys.stdout.write(text)
                    sys.stdout.flush()
                    full_content += text
                elif msg_type == "reasoning_delta":
                    pass  # skip reasoning tokens
                elif msg_type == "turn_complete":
                    print("\n--- TURN COMPLETE ---")
                    break
                elif msg_type == "status":
                    print(f"  [status] entry_id={data.get('entry_id', '?')[:8]}... -> {data.get('status')}")
                else:
                    print(f"  [{msg_type}] {json.dumps(data)[:200]}")
        except asyncio.TimeoutError:
            print("\n--- TIMEOUT (120s) ---")

    print(f"\n=== FINAL ANSWER ===\n{full_content}")


asyncio.run(main())
