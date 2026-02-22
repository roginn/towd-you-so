"""Test script to call the Roboflow parking-sign workflow and inspect the response."""

import base64
import json
import os
import sys
from glob import glob

import httpx

# Load .env manually (no extra deps needed)
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("ROBOFLOW_API_KEY", "")
if not API_KEY:
    print("ERROR: ROBOFLOW_API_KEY not set")
    sys.exit(1)

WORKSPACE = "robolook"
WORKFLOW_ID = "parking-sign"
API_URL = f"https://detect.roboflow.com/infer/workflows/{WORKSPACE}/{WORKFLOW_ID}"

# Pick first image from uploads/
uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
images = sorted(glob(os.path.join(uploads_dir, "*.jpeg"))) + sorted(
    glob(os.path.join(uploads_dir, "*.jpg"))
)
if not images:
    print("ERROR: No images found in uploads/")
    sys.exit(1)

image_path = images[0]
print(f"Using image: {image_path}")

with open(image_path, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("ascii")

payload = {
    "api_key": API_KEY,
    "inputs": {
        "image": {
            "type": "base64",
            "value": image_b64,
        }
    },
}

print(f"Calling {API_URL} ...")
resp = httpx.post(API_URL, json=payload, timeout=60)
print(f"Status: {resp.status_code}")

data = resp.json()

# Strip base64 image values for readability
def strip_b64(obj):
    if isinstance(obj, dict):
        return {
            k: ("<base64 image>" if isinstance(v, dict) and v.get("type") == "base64" else strip_b64(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [strip_b64(i) for i in obj]
    return obj

print(f"Response:\n{json.dumps(strip_b64(data), indent=2)}")
