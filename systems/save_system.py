# systems/save_system.py
# =============================================================================
# СИСТЕМА СОХРАНЕНИЙ ИГРЫ
# Работает напрямую с движком (game_engine):
#    - берёт данные для сохранения из engine.game_state и engine.current_map
#    - при загрузке создаёт новую карту и присваивает её движку
# =============================================================================

import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import log


class SaveSystem:
    """
    Система сохранений игры.
    Работает напрямую с движком (game_engine).
    """
    
    def __init__(self, game_engine):
        self.engine = game_engine
        self.last_save_name = None
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.saves_dir = os.path.join(base_dir, "saves")
        os.makedirs(self.saves_dir, exist_ok=True)
    
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
        
        # Данные игрока — через to_dict() объекта Player
        player_data = game_state.player.to_dict()
        # Добавляем инвентарь, человечность и дни (они пока не в Player)
        player_data["inventory"] = game_state.inventory.get_items()
        player_data["humanity"] = game_state.humanity
        player_data["days_left"] = game_state.days_left
        log.info(f"СБОР: игрок на ({player_data['x']},{player_data['y']}), инвентарь: {player_data['inventory']}")
        
        # Данные локации
        location_data = {
            "location_id": current_map.location_id,
            "doors": dict(game_state.door_states),
            "npcs": [],
            "animals": [],
            "containers": [],
            "drops": [],
        }
        log.info(f"СБОР: двери: {location_data['doors']}")
        
        # NPC
        for npc in current_map.npcs:
            location_data["npcs"].append({
                "id": npc.id,
                "x": npc.x,
                "y": npc.y,
                "patrol_index": npc.patrol_index,
                "path": npc.path,
            })
            log.info(f"СБОР: NPC {npc.id} на ({npc.x},{npc.y}), patrol_index={npc.patrol_index}")
        
        # Животные
        for animal in current_map.animals:
            location_data["animals"].append({
                "id": animal.id,
                "x": animal.x,
                "y": animal.y,
                "species": animal.species,
                "behavior_type": animal.behavior_type,
                "hunger": animal.hunger,
                "energy": animal.energy,
                "boredom": animal.boredom,
                "wanderlust": animal.wanderlust,
                "fear": animal.fear,
                "aggression": animal.aggression,
                "points_of_interest": animal.points_of_interest,
                "action": animal.action,
                "target": animal.target,
                "action_timer": animal.action_timer,
                "path": animal.path,
            })
            log.info(f"СБОР: животное {animal.id} ({animal.species}) на ({animal.x},{animal.y})")
        
        # Контейнеры
        for container in current_map.containers:
            location_data["containers"].append({
                "id": container.id,
                "x": container.x,
                "y": container.y,
                "width": container.width,
                "height": container.height,
                "is_open": container.is_open,
                "items": container.items.copy(),
                "access_side": container.access_side,
            })
        
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
        
        # --- 1. СОЗДАЁМ НОВУЮ КАРТУ ---
        from world.map import Map
        new_map = Map(location_data["location_id"], game_state, self.engine.location_manager)
        log.info(f"ЗАГРУЗКА: создана карта {location_data['location_id']}")
        
        # --- 2. ВОССТАНАВЛИВАЕМ ИГРОКА через from_dict() ---
        from entities.player import Player
        game_state.player = Player.from_dict(data["player"])
        game_state.humanity = data["player"].get("humanity", 50)
        game_state.days_left = data["player"].get("days_left", 14)
        game_state.inventory.items = data["player"].get("inventory", []).copy()
        # Синхронизируем лимит веса инвентаря с классом игрока
        game_state.inventory.max_weight = game_state.player.max_weight
        log.info(f"ЗАГРУЗКА: игрок на ({game_state.player.x},{game_state.player.y}), "
                 f"класс={game_state.player.player_class}, инвентарь={game_state.inventory.items}")
        
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
                if npc.id == npc_save["id"]:
                    npc.x = npc_save["x"]
                    npc.y = npc_save["y"]
                    npc.patrol_index = npc_save["patrol_index"]
                    npc.path = [tuple(p) for p in npc_save["path"]]
                    npc.wait_until = 0
                    log.info(f"ЗАГРУЗКА: NPC {npc.id} восстановлен на ({npc.x},{npc.y})")
                    break
        
        # --- 5. ВОССТАНАВЛИВАЕМ ЖИВОТНЫХ ---
        new_map.animals.clear()
        from entities.animal import Animal
        for animal_save in location_data.get("animals", []):
            animal = Animal(
                animal_id=animal_save["id"],
                name="Животное",
                x=animal_save["x"],
                y=animal_save["y"],
                species=animal_save.get("species", "cat"),
                behavior_type=animal_save.get("behavior_type", "emergent_needs")
            )
            animal.hunger = animal_save.get("hunger", 50)
            animal.energy = animal_save.get("energy", 80)
            animal.boredom = animal_save.get("boredom", 30)
            animal.wanderlust = animal_save.get("wanderlust", 0)
            animal.fear = animal_save.get("fear", 0)
            animal.aggression = animal_save.get("aggression", 0)
            animal.points_of_interest = animal_save.get("points_of_interest", {})
            for key in animal.points_of_interest:
                val = animal.points_of_interest[key]
                if isinstance(val, list):
                    animal.points_of_interest[key] = tuple(val)
            animal.action = animal_save.get("action", "idle")
            animal.target = animal_save.get("target")
            if isinstance(animal.target, list):
                animal.target = tuple(animal.target)
            animal.action_timer = animal_save.get("action_timer", 0)
            animal.path = [tuple(p) for p in animal_save.get("path", [])]
            new_map.animals.append(animal)
            log.info(f"ЗАГРУЗКА: животное {animal.id} ({animal.species}) восстановлено на ({animal.x},{animal.y})")
        
        # --- 6. ВОССТАНАВЛИВАЕМ КОНТЕЙНЕРЫ ---
        for cont_save in location_data["containers"]:
            for container in new_map.containers:
                if container.id == cont_save["id"]:
                    container.is_open = cont_save["is_open"]
                    container.items = cont_save["items"].copy()
                    container.access_side = cont_save.get("access_side", "all")
                    container.width = cont_save.get("width", 1)
                    container.height = cont_save.get("height", 1)
                    log.info(f"ЗАГРУЗКА: контейнер {container.id} восстановлен")
                    break
        
        # --- 7. ВОССТАНАВЛИВАЕМ ДРОПЫ ---
        new_map.drops.clear()
        from objects.drop import ItemDrop
        for drop_save in location_data["drops"]:
            new_drop = ItemDrop(
                drop_id=drop_save["id"],
                x=drop_save["x"],
                y=drop_save["y"],
                items=drop_save["items"].copy()
            )
            new_map.drops.append(new_drop)
            log.info(f"ЗАГРУЗКА: дроп {new_drop.id} восстановлен на ({new_drop.x},{new_drop.y})")
        
        # --- 8. ПРИСВАИВАЕМ КАРТУ ДВИЖКУ ---
        self.engine.current_map = new_map
        
        # --- 9. ПЕРЕСОЗДАЁМ DIALOG_SYSTEM ---
        dialogs_path = os.path.join(
            self.engine.location_manager.get_location_path(location_data["location_id"]),
            "dialogs"
        )
        from systems.dialog_system import DialogSystem
        self.engine.dialog_system = DialogSystem(game_state, dialogs_path)
        log.info(f"ЗАГРУЗКА: dialog_system пересоздан под {location_data['location_id']}")
        
        # --- 10. СБРАСЫВАЕМ СОСТОЯНИЯ ---
        self.engine.move_queue = []
        self.engine.player_target = []
        self.engine.location_manager.location_states = {}
        
        log.info(f"ЗАГРУЗКА: успешно завершено")
        return True
    
    def load_last(self):
        if not self.last_save_name:
            log.info("ЗАГРУЗКА: нет last_save_name")
            return False
        return self.load(self.last_save_name)
    
    def list_saves(self):
        if not os.path.isdir(self.saves_dir):
            return []
        files = [f for f in os.listdir(self.saves_dir) if f.endswith(".json")]
        return sorted([f[:-5] for f in files])
    
    def next_save_name(self):
        base = self.engine.game_state.player.player_class or "Идальго"
        loc = self.engine.current_map.location_id
        existing = self.list_saves()
        n = 1
        while True:
            candidate = f"{base}_{n:03d}_{loc}"
            if candidate not in existing:
                return candidate
            n += 1