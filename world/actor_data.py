# world/actor_data.py
import json
import os
from settings import DATA_DIR
from logger import log


class ActorData:
    """Singleton для загрузки и доступа к данным о персонажах."""

    _instance = None
    _data = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ActorData._data is None:
            self._load_data()

    def _load_data(self):
        # FIX (#9): абсолютный путь вместо относительного "data/...".
        actors_file = os.path.join(DATA_DIR, "actors.json")

        if not os.path.exists(actors_file):
            log.warning(f"ACTOR_DATA: файл {actors_file} не найден")
            ActorData._data = {}
            return

        try:
            with open(actors_file, "r", encoding="utf-8") as f:
                ActorData._data = json.load(f)
            log.info(f"ACTOR_DATA: загружено {len(ActorData._data)} персонажей")
        except Exception as e:
            log.error(f"ACTOR_DATA: ошибка загрузки {actors_file}: {e}")
            ActorData._data = {}

    def get(self, actor_id: str) -> dict:
        if ActorData._data is None:
            self._load_data()
        return ActorData._data.get(actor_id, {})

    def get_all_ids(self) -> list[str]:
        if ActorData._data is None:
            self._load_data()
        return list(ActorData._data.keys())

    def reload(self):
        ActorData._data = None
        self._load_data()