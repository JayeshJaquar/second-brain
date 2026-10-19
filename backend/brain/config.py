import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("SECOND_BRAIN_DATA", str(Path.home() / "Library/Application Support/SecondBrain")))
MODELS = ROOT / ".models"
TEXT_MODEL = "qwen2.5:7b-instruct"
VISION_MODEL = "qwen2.5vl:3b"
PORT = int(os.environ.get("SECOND_BRAIN_PORT", "8765"))
