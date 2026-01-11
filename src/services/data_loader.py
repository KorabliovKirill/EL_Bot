from pathlib import Path
import json
from functools import lru_cache
from src.config.settings import DATA_DIR


@lru_cache(maxsize=1)
def load_json(filename: str) -> dict:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_mentors() -> list[dict]:
    return load_json("mentors.json")["mentors"]


def get_admins() -> list[dict]:
    return load_json("admins.json")["admins"]


def get_homeworks() -> list[dict]:
    return load_json("homeworks.json")["homeworks"]