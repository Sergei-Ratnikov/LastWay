# world/actor_data.py
# =============================================================================
# ЗАГРУЗЧИК ДАННЫХ О ПЕРСОНАЖАХ (NPC)
# Читает data/actors.json и предоставляет доступ к данным NPC.
# Работает как Singleton (один экземпляр на всё приложение).
# =============================================================================

import json
import os
from logger import log


class ActorData:
    """
    Singleton для загрузки и доступа к данным о персонажах.
    Читает data/actors.json один раз при первом обращении.
    """
    
    _instance = None
    _data = None
    
    def __new__(cls):
        """Singleton pattern: возвращает единственный экземпляр."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Инициализация: загружаем данные при первом создании."""
        if ActorData._data is None:
            self._load_data()
    
    def _load_data(self):
        """Загружает данные из actors.json."""
        actors_file = os.path.join("data", "actors.json")
        
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
        """
        Возвращает данные персонажа по ID.
        
        Аргументы:
            actor_id (str): ID персонажа (например, "001_001").
            
        Возвращает:
            dict: Словарь с данными персонажа или пустой словарь.
        """
        if ActorData._data is None:
            self._load_data()
        return ActorData._data.get(actor_id, {})
    
    def get_all_ids(self) -> list[str]:
        """
        Возвращает список всех ID персонажей.
        
        Возвращает:
            list[str]: Список ID.
        """
        if ActorData._data is None:
            self._load_data()
        return list(ActorData._data.keys())
    
    def reload(self):
        """Перезагружает данные из файла (для горячего обновления)."""
        ActorData._data = None
        self._load_data()