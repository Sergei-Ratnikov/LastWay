# systems/save_system.py
import json
import os
import sys

# Добавляем корневую папку проекта в пути поиска Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger import log


class SaveSystem:
    """
    Система сохранений игры.

    Работает напрямую с движком (game_engine):
      - берёт данные для сохранения из engine.game_state и engine.current_map
      - при загрузке создаёт новую карту и присваивает её движку
    """

    def __init__(self, game_engine):
        """
        Аргументы:
            game_engine: Ссылка на GameEngine (источник game_state и current_map).
        """
        self.engine = game_engine
        self.last_save_name = None  # Имя последнего сохранения

        # Папка saves/ рядом с main.py
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.saves_dir = os.path.join(base_dir, "saves")
        os.makedirs(self.saves_dir, exist_ok=True)

    # -------------------------------------------------------------------------
    # ВСПОМОГАТЕЛЬНЫЕ
    # -------------------------------------------------------------------------
    def get_save_filename(self, name):
        return os.path.join(self.saves_dir, f"{name}.json")

    # -------------------------------------------------------------------------
    # СБОР ДАННЫХ
    # -------------------------------------------------------------------------
    def collect_data(self):
        """Собирает все данные игры (игрок + локация) в один словарь."""
        game_state = self.engine.game_state
        current_map = self.engine.current_map

        log.info("СБОР ДАННЫХ: начинаю сбор")

        # Данные игрока
        player_data = {
            "x": game_state.player["x"],
            "y": game_state.player["y"],
            "class": game_state.player["class"],
            "inventory": game_state.inventory.get_items(),
            "humanity": game_state.humanity,
            "days_left": game_state.days_left,
        }
        log.info(f"СБОР: игрок на ({player_data['x']},{player_data['y']}), инвентарь: {player_data['inventory']}")

        # Данные локации
        location_data = {
            "location_id": current_map.location_id,
            "doors": dict(game_state.door_states),
            "npcs": [],
            "containers": [],
            "drops": [],
        }
        log.info(f"СБОР: двери: {location_data['doors']}")

        # NPC
        for npc in current_map.npcs:
            location_data["npcs"].append({
                "id": npc["id"],
                "x": npc["x"],
                "y": npc["y"],
                "patrol_index": npc.get("patrol_index", 0),
                "path": npc.get("path", []),
            })
            log.info(f"СБОР: NPC {npc['id']} на ({npc['x']},{npc['y']}), patrol_index={npc.get('patrol_index', 0)}")

        # Контейнеры
        for container in current_map.containers:
            location_data["containers"].append({
                "id": container.id,
                "is_open": container.is_open,
                "items": container.items.copy(),
            })
            log.info(f"СБОР: контейнер {container.id}, открыт={container.is_open}, предметы={container.items}")

        # Дропы
        for drop in current_map.drops:
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

    # -------------------------------------------------------------------------
    # СОХРАНЕНИЕ
    # -------------------------------------------------------------------------
    def save(self, name):
        """Сохраняет игру в файл <name>.json."""
        log.info(f"СОХРАНЕНИЕ: начинаю '{name}'")
        data = self.collect_data()
        filename = self.get_save_filename(name)

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            log.info(f"СОХРАНЕНИЕ: успешно записано в {filename}")
            self.last_save_name = name
            return True
        except Exception as e:
            log.info(f"СОХРАНЕНИЕ: ОШИБКА {e}")
            return False

    # -------------------------------------------------------------------------
    # ЗАГРУЗКА
    # -------------------------------------------------------------------------
    def load(self, name):
        """
        Загружает игру из файла <name>.json.

        ВАЖНО: метод не просто читает данные, но и создаёт новую карту,
        восстанавливает на ней NPC/двери/контейнеры/дропы и присваивает её движку.
        """
        log.info(f"ЗАГРУЗКА: начинаю '{name}'")
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

        game_state = self.engine.game_state
        location_data = data["location"]

        # --- 1. СОЗДАЁМ НОВУЮ КАРТУ ИЗ СОХРАНЕНИЯ ---
        # Импорт внутри метода — чтобы избежать циклических зависимостей
        from world.map import Map
        new_map = Map(location_data["location_id"], game_state, self.engine.location_manager)
        log.info(f"ЗАГРУЗКА: создана карта {location_data['location_id']}")

        # --- 2. ВОССТАНАВЛИВАЕМ ИГРОКА ---
        player_data = data["player"]
        game_state.player["x"] = player_data["x"]
        game_state.player["y"] = player_data["y"]
        game_state.player["class"] = player_data["class"]
        game_state.humanity = player_data["humanity"]
        game_state.days_left = player_data["days_left"]
        game_state.inventory.items = player_data["inventory"].copy()
        log.info(f"ЗАГРУЗКА: игрок на ({player_data['x']},{player_data['y']}), инвентарь={player_data['inventory']}")

        # --- 3. ВОССТАНАВЛИВАЕМ ДВЕРИ ---
        game_state.door_states = dict(location_data["doors"])
        for coord, tile_type in location_data["doors"].items():
            if "," in coord:
                x_str, y_str = coord.split(",")
                x, y = int(x_str), int(y_str)
                if 0 <= x < new_map.width and 0 <= y < new_map.height:
                    new_map.tiles[y][x] = tile_type
        log.info(f"ЗАГРУЗКА: двери восстановлены: {location_data['doors']}")

        # --- 4. ВОССТАНАВЛИВАЕМ NPC ---
        for npc_save in location_data["npcs"]:
            for npc in new_map.npcs:
                if npc["id"] == npc_save["id"]:
                    npc["x"] = npc_save["x"]
                    npc["y"] = npc_save["y"]
                    npc["patrol_index"] = npc_save["patrol_index"]
                    # Преобразуем списки координат обратно в кортежи
                    npc["path"] = [tuple(p) for p in npc_save["path"]]
                    npc["wait_until"] = 0
                    log.info(f"ЗАГРУЗКА: NPC {npc['id']} восстановлен на ({npc['x']},{npc['y']}), patrol_index={npc['patrol_index']}")
                    break

        # --- 5. ВОССТАНАВЛИВАЕМ КОНТЕЙНЕРЫ ---
        for cont_save in location_data["containers"]:
            for container in new_map.containers:
                if container.id == cont_save["id"]:
                    container.is_open = cont_save["is_open"]
                    container.items = cont_save["items"].copy()
                    log.info(f"ЗАГРУЗКА: контейнер {container.id} восстановлен, открыт={container.is_open}, предметы={container.items}")
                    break

        # --- 6. ВОССТАНАВЛИВАЕМ ДРОПЫ ---
        new_map.drops.clear()
        from entities.drop import ItemDrop
        for drop_save in location_data["drops"]:
            new_drop = ItemDrop(
                drop_id=drop_save["id"],
                x=drop_save["x"],
                y=drop_save["y"],
                items=drop_save["items"].copy()
            )
            new_map.drops.append(new_drop)
            log.info(f"ЗАГРУЗКА: дроп {new_drop.id} восстановлен на ({new_drop.x},{new_drop.y}), предметы={new_drop.items}")

        # --- 7. ПРИСВАИВАЕМ КАРТУ ДВИЖКУ ---
        self.engine.current_map = new_map

        # --- 8. ПЕРЕСОЗДАЁМ DIALOG_SYSTEM ПОД НОВУЮ ЛОКАЦИЮ ---
        # (иначе диалоги будут искаться в папке старой локации)
        dialogs_path = os.path.join(
            self.engine.location_manager.get_location_path(location_data["location_id"]),
            "dialogs"
        )
        from systems.dialog_system import DialogSystem
        self.engine.dialog_system = DialogSystem(game_state, dialogs_path)
        log.info(f"ЗАГРУЗКА: dialog_system пересоздан под {location_data['location_id']}")

        # --- 9. СБРАСЫВАЕМ ОЧЕРЕДЬ ДВИЖЕНИЯ ---
        self.engine.move_queue = []
        self.engine.player_target = None

        # --- 10. СБРАСЫВАЕМ in-session состояния локаций (чтобы не тащить старые) ---
        self.engine.location_manager.location_states = {}

        log.info(f"ЗАГРУЗКА: успешно завершено")
        return True

    def load_last(self):
        """Загружает последнее сохранение (по имени из last_save_name)."""
        if not self.last_save_name:
            log.info("ЗАГРУЗКА: нет last_save_name (ничего не сохранялось)")
            return False
        return self.load(self.last_save_name)