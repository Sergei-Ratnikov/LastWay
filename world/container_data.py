# world/container_data.py
import json
import os
from settings import DATA_DIR
from logger import log


class ContainerData:
    """Singleton для загрузки и доступа к шаблонам контейнеров."""

    _instance = None
    _data = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ContainerData._data is None:
            self._load_data()

    def _load_data(self):
        # FIX (#9): абсолютный путь.
        path = os.path.join(DATA_DIR, "containers.json")
        if not os.path.exists(path):
            ContainerData._data = {}
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                ContainerData._data = json.load(f)
            log.info(f"CONTAINER_DATA: загружено {len(ContainerData._data)} шаблонов")
        except Exception as e:
            log.error(f"CONTAINER_DATA: {e}")
            ContainerData._data = {}

    def get(self, con_id: str) -> dict:
        if ContainerData._data is None:
            self._load_data()
        return ContainerData._data.get(con_id, {})

    def get_all_ids(self) -> list:
        if ContainerData._data is None:
            self._load_data()
        return list(ContainerData._data.keys())