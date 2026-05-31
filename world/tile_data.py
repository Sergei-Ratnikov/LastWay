# world/tile_data.py
import json
import os
from settings import DATA_DIR

class TileData:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TileData, cls).__new__(cls)
            cls._instance._load()
        return cls._instance
    
    def _load(self):
        path = os.path.join(DATA_DIR, "tiles.json")
        with open(path, "r", encoding="utf-8") as f:
            self.tiles = json.load(f)
    
    def get(self, tile_type, default=None):
        return self.tiles.get(str(tile_type), default)
    
    def is_walkable(self, tile_type):
        prop = self.get(tile_type)
        return prop.get("walkable", False) if prop else False