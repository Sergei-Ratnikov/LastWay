# systems/save_system.py
import json
import os

class SaveSystem:
    """Система сохранений. Пока только заготовка."""

    def __init__(self, game_state, current_map):
        self.game_state = game_state
        self.current_map = current_map
        self.saves_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saves")
        os.makedirs(self.saves_dir, exist_ok=True)

    def get_save_filename(self, name):
        """Формирует имя файла сохранения."""
        return os.path.join(self.saves_dir, f"{name}.json")

    def save(self, name):
        """Сохраняет игру. Пока заглушка."""
        print(f"СОХРАНЕНИЕ: {name} (заглушка)")
        return True

    def load(self, name):
        """Загружает игру. Пока заглушка."""
        print(f"ЗАГРУЗКА: {name} (заглушка)")
        return True