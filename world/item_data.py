# world/item_data.py
import json
import os
from settings import DATA_DIR

class ItemData:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ItemData, cls).__new__(cls)
            cls._instance._load()
        return cls._instance
    
    def _load(self):
        path = os.path.join(DATA_DIR, "items.json")
        with open(path, "r", encoding="utf-8") as f:
            self.items = json.load(f)
    
    def get(self, item_id, default=None):
        return self.items.get(item_id, default)
    
    def get_mass(self, item_id):
        prop = self.get(item_id)
        return prop.get("mass", 0.0) if prop else 0.0