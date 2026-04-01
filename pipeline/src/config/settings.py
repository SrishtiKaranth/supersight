from os import getenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = BASE_DIR / "data" / "input"

DEVICES = [d.name for d in DATA_DIR.iterdir() if d.is_dir()]

DB_CONFIG = {
    "host":     getenv("DB_HOST", "localhost"),
    "port":     int(getenv("DB_PORT", 5434)),
    "dbname":   getenv("DB_NAME", "supersight"),
    "user":     getenv("DB_USER", "supersight_user"),
    "password": getenv("DB_PASSWORD", "supersight123"),
}
