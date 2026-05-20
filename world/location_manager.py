# world/location_manager.py
import json
import os
from settings import DATA_DIR


class LocationManager:
    """Управляет загрузкой локаций и их состояниями.
        
        Модуль отвечает за:
            Загрузку registry.json
            Построение пути к папке локации
            Загрузку location.json
            Управление состояниями локаций
    """

    def __init__(self):
        self.registry = self._load_registry()
        self.location_states = {}  # {location_id: state_data}

    def _load_registry(self):
        """Загружает список всех локаций из registry.json."""
        path = os.path.join(DATA_DIR, "locations", "registry.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_location_path(self, location_id):
        """Возвращает путь к папке локации по её ID."""
        return os.path.join(DATA_DIR, "locations", location_id)

    def get_location_data(self, location_id):
        """Загружает location.json из папки локации."""
        loc_path = self.get_location_path(location_id)
        map_path = os.path.join(loc_path, "location.json")
        with open(map_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_start_location(self):
        """Возвращает ID стартовой локации из registry.json."""
        for loc in self.registry.get("locations", []):
            if loc.get("start"):
                return loc["id"]
        return self.registry["locations"][0]["id"]