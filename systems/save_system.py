# systems/save_system.py
import json
import os
import sys

# Добавляем корневую папку проекта в пути поиска Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger import log

class SaveSystem:
    """Система сохранений."""

    def __init__(self, game_state, current_map):
        self.game_state = game_state
        self.current_map = current_map
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.saves_dir = os.path.join(base_dir, "saves")
        os.makedirs(self.saves_dir, exist_ok=True)

    def get_save_filename(self, name):
        return os.path.join(self.saves_dir, f"{name}.json")

    def collect_data(self):
        """Собирает все данные игры в один словарь."""
        log.info("СБОР ДАННЫХ: начинаю сбор")
        
        player_data = {
            "x": self.game_state.player["x"],
            "y": self.game_state.player["y"],
            "class": self.game_state.player["class"],
            "inventory": self.game_state.inventory.get_items(),
            "humanity": self.game_state.humanity,
            "days_left": self.game_state.days_left,
        }
        log.info(f"СБОР: игрок на ({player_data['x']},{player_data['y']}), инвентарь: {player_data['inventory']}")

        location_data = {
            "location_id": self.current_map.location_id,
            "doors": dict(self.game_state.door_states),
            "npcs": [],
            "containers": [],
            "drops": [],
        }
        log.info(f"СБОР: двери: {location_data['doors']}")

        for npc in self.current_map.npcs:
            location_data["npcs"].append({
                "id": npc["id"],
                "x": npc["x"],
                "y": npc["y"],
                "patrol_index": npc.get("patrol_index", 0),
                "path": npc.get("path", []),
            })
            log.info(f"СБОР: NPC {npc['id']} на ({npc['x']},{npc['y']}), patrol_index={npc.get('patrol_index',0)}, path={npc.get('path',[])}")

        for container in self.current_map.containers:
            location_data["containers"].append({
                "id": container.id,
                "is_open": container.is_open,
                "items": container.items.copy(),
            })
            log.info(f"СБОР: контейнер {container.id}, открыт={container.is_open}, предметы={container.items}")

        for drop in self.current_map.drops:
            location_data["drops"].append({
                "id": drop.id,
                "x": drop.x,
                "y": drop.y,
                "items": drop.items.copy(),
            })
            log.info(f"СБОР: дроп {drop.id} на ({drop.x},{drop.y}), предметы={drop.items}")

        return {
            "player": player_data,
            "location": location_data,
        }

    def save(self, name):
        """Сохраняет игру в файл."""
        log.info(f"СОХРАНЕНИЕ: начинаю сохранение '{name}'")
        data = self.collect_data()
        filename = self.get_save_filename(name)
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            log.info(f"СОХРАНЕНИЕ: успешно записано в {filename}")
            return True
        except Exception as e:
            log.info(f"СОХРАНЕНИЕ: ОШИБКА {e}")
            return False

    def load(self, name):
        """Загружает игру из файла."""
        log.info(f"ЗАГРУЗКА: начинаю загрузку '{name}'")
        filename = self.get_save_filename(name)
        if not os.path.exists(filename):
            log.info(f"ЗАГРУЗКА: файл не найден {filename}")
            return False

        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            log.info(f"ЗАГРУЗКА: ОШИБКА чтения {e}")
            return False

        # Игрок
        player_data = data["player"]
        self.game_state.player["x"] = player_data["x"]
        self.game_state.player["y"] = player_data["y"]
        self.game_state.player["class"] = player_data["class"]
        self.game_state.humanity = player_data["humanity"]
        self.game_state.days_left = player_data["days_left"]
        self.game_state.inventory.items = player_data["inventory"].copy()
        log.info(f"ЗАГРУЗКА: игрок на ({player_data['x']},{player_data['y']}), инвентарь={player_data['inventory']}")

        # Локация
        location_data = data["location"]
        self.game_state.door_states = dict(location_data["doors"])
        log.info(f"ЗАГРУЗКА: двери={location_data['doors']}")

        # NPC
        for npc_save in location_data["npcs"]:
            for npc in self.current_map.npcs:
                if npc["id"] == npc_save["id"]:
                    npc["x"] = npc_save["x"]
                    npc["y"] = npc_save["y"]
                    npc["patrol_index"] = npc_save["patrol_index"]
                    # ВАЖНО: преобразуем списки обратно в кортежи
                    npc["path"] = [tuple(p) for p in npc_save["path"]]
                    npc["wait_until"] = 0
                    log.info(f"ЗАГРУЗКА: NPC {npc['id']} восстановлен на ({npc['x']},{npc['y']}), patrol_index={npc['patrol_index']}, path={npc['path']}")
                    break

        # Контейнеры
        for cont_save in location_data["containers"]:
            for container in self.current_map.containers:
                if container.id == cont_save["id"]:
                    container.is_open = cont_save["is_open"]
                    container.items = cont_save["items"].copy()
                    log.info(f"ЗАГРУЗКА: контейнер {container.id} восстановлен, открыт={container.is_open}, предметы={container.items}")
                    break

        # Дропы
        self.current_map.drops.clear()
        for drop_save in location_data["drops"]:
            from entities.drop import ItemDrop
            new_drop = ItemDrop(
                drop_id=drop_save["id"],
                x=drop_save["x"],
                y=drop_save["y"],
                items=drop_save["items"].copy()
            )
            self.current_map.drops.append(new_drop)
            log.info(f"ЗАГРУЗКА: дроп {new_drop.id} восстановлен на ({new_drop.x},{new_drop.y}), предметы={new_drop.items}")

        log.info(f"ЗАГРУЗКА: успешно завершено")
        return True