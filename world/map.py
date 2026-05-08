# world/map.py
import json
import pygame
import os
import random
from settings import *

class Map:

    def __init__(self, map_id, game_state):
        self.map_id = map_id
        self.game_state = game_state
        self.width = 0
        self.height = 0
        self.tiles = []
        self.base_tiles = []
        self.npcs = []
        self.containers = []
        self.hidden_containers = []
        self.exits = []
        self.player_start = (0, 0)
        self.load()

    def load(self):
        filename = f"{self.map_id}.json"
        path = os.path.join(MAPS_DIR, filename)
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки карты {filename}:", e)
            raise Exception(f"Не удалось загрузить карту {filename}")

        self.width = data.get("width", 18)
        self.height = data.get("height", 14)
        self.base_tiles = data.get("tiles", [[1 for x in range(self.width)] for y in range(self.height)])
        self.tiles = [row[:] for row in self.base_tiles]
        self.containers = data.get("containers", [])
        self.hidden_containers = data.get("hidden_containers", [])
        self.exits = data.get("exits", [])
        self.player_start = data.get("player_start", [1, 1])

        # Загрузка NPC из отдельных файлов
        self.npcs = []
        for npc_data in data.get("npcs", []):
            npc_id = npc_data.get("npc_id")
            if not npc_id:
                print("Пропущен NPC: отсутствует npc_id")
                continue
                
            npc_filename = f"{npc_id}_npc.json"
            npc_path = os.path.join(NPCS_DIR, npc_filename)
            
            try:
                with open(npc_path, "r", encoding="utf-8") as f:
                    npc_info = json.load(f)
            except Exception as e:
                print(f"Ошибка загрузки NPC {npc_id} из {npc_path}:", e)
                # Добавляем NPC-заглушку
                self.npcs.append({
                    "id": npc_id,
                    "x": npc_data.get("x", 0),
                    "y": npc_data.get("y", 0),
                    "name": "Ошибка загрузки",
                    "dialog_id": npc_id,
                    "movement": "stationary",
                    "move_delay_ms": 1000,
                    "patrol_points": [],
                    "patrol_index": 0,
                    "last_move_time": 0,
                    "stuck_counter": 0
                })
                continue

            self.npcs.append({
                "id": npc_id,
                "x": npc_data.get("x", 0),
                "y": npc_data.get("y", 0),
                "name": npc_info.get("name", "Незнакомец"),
                "dialog_id": npc_info.get("dialog_id", npc_id),
                "movement": npc_info.get("movement", "stationary"),
                "move_delay_ms": npc_info.get("move_delay_ms", 1000),
                "patrol_points": npc_info.get("patrol_points", []),
                "patrol_index": 0,
                "last_move_time": 0,
                "stuck_counter": 0
            })

        # Восстанавливаем состояния дверей из game_state
        for coord, tile_type in self.game_state.door_states.items():
            if "," in coord:
                x_str, y_str = coord.split(",")
                x, y = int(x_str), int(y_str)
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.tiles[y][x] = tile_type

    def is_walkable(self, x, y):
        """Проходимость для игрока: пол (1), открытая дверь (2), и нет NPC"""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        
        # Нельзя проходить сквозь NPC
        if self.get_npc_at(x, y) is not None:
            return False
        
        tile = self.tiles[y][x]
        return tile == 1 or tile == 2

    def is_walkable_for_npc(self, x, y, current_npc):
        """Проходимость для NPC: пол (1), открытая дверь (2), нет игрока, нет других NPC"""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False

        tile = self.tiles[y][x]
        if tile not in (1, 2):
            return False

        # Нельзя проходить сквозь игрока
        if self.game_state.player["x"] == x and self.game_state.player["y"] == y:
            return False

        # Нельзя проходить сквозь других NPC
        for npc in self.npcs:
            if npc != current_npc and npc["x"] == x and npc["y"] == y:
                return False

        return True

    def is_door(self, x, y):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        tile = self.tiles[y][x]
        return tile in (5, 6, 7, 8, 9, 2)

    def open_door(self, x, y):
        if self.get_tile_type(x, y) in (5, 6, 7, 8, 9):
            self.tiles[y][x] = 2
            self.game_state.set_door_state(x, y, 2)
            return True
        return False

    def close_door(self, x, y):
        if self.get_tile_type(x, y) == 2:
            self.tiles[y][x] = 5
            self.game_state.set_door_state(x, y, 5)
            return True
        return False

    def get_tile_type(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

    def set_tile(self, x, y, tile_type):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = tile_type

    def get_npc_at(self, x, y):
        for npc in self.npcs:
            if npc["x"] == x and npc["y"] == y:
                return npc
        return None

    def update_npcs(self, current_time, player_x, player_y):
        """Обновление движения всех NPC"""
        for npc in self.npcs:
            if npc["movement"] == "stationary":
                continue

            if current_time - npc["last_move_time"] < npc["move_delay_ms"]:
                continue

            new_x, new_y = npc["x"], npc["y"]

            # --- Патруль по точкам ---
            if npc["movement"] == "patrol" and len(npc["patrol_points"]) > 0:
                target = npc["patrol_points"][npc["patrol_index"]]
                dx = 0
                dy = 0
                if npc["x"] < target[0]:
                    dx = 1
                elif npc["x"] > target[0]:
                    dx = -1
                elif npc["y"] < target[1]:
                    dy = 1
                elif npc["y"] > target[1]:
                    dy = -1

                new_x = npc["x"] + dx
                new_y = npc["y"] + dy

                # Если достигли цели — переключаем индекс
                if new_x == target[0] and new_y == target[1]:
                    npc["patrol_index"] = (npc["patrol_index"] + 1) % len(npc["patrol_points"])

            # --- Случайное движение ---
            elif npc["movement"] == "random":
                dirs = [(1,0), (-1,0), (0,1), (0,-1)]
                dx, dy = random.choice(dirs)
                new_x = npc["x"] + dx
                new_y = npc["y"] + dy

            # Проверка коллизий
            if self.is_walkable_for_npc(new_x, new_y, npc):
                npc["x"] = new_x
                npc["y"] = new_y
                npc["last_move_time"] = current_time

    def render(self, screen, camera_x, camera_y):
        # Отрисовка тайлов
        for y in range(self.height):
            for x in range(self.width):
                tile = self.tiles[y][x]
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

                if tile == 0:
                    color = DARK_GREY
                elif tile == 1:
                    color = LIGHT_GREY
                elif tile == 2:
                    color = BROWN
                elif tile == 5:
                    color = (100, 50, 0)
                elif tile == 6:
                    color = (120, 60, 0)
                elif tile == 7:
                    color = (80, 80, 120)
                elif tile == 8:
                    color = (90, 45, 20)
                elif tile == 9:
                    color = (70, 40, 10)
                else:
                    color = BLACK

                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, BLACK, rect, 1)

        # Отрисовка NPC
        for npc in self.npcs:
            rect = pygame.Rect(npc["x"] * TILE_SIZE, npc["y"] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, NPC_COLOR, rect)
            pygame.draw.rect(screen, BLACK, rect, 2)
            font = pygame.font.Font(None, 16)
            name_text = font.render(npc["name"], True, WHITE)
            screen.blit(name_text, (npc["x"] * TILE_SIZE, npc["y"] * TILE_SIZE - 15))


    def update_npcs(self, current_time, player_x, player_y):
        for npc in self.npcs:
            if npc["movement"] == "stationary":
                continue

            if current_time - npc["last_move_time"] < npc["move_delay_ms"]:
                continue

            new_x, new_y = npc["x"], npc["y"]

            if npc["movement"] == "patrol" and len(npc["patrol_points"]) > 0:
                target = npc["patrol_points"][npc["patrol_index"]]
                dx = 0
                dy = 0
                if npc["x"] < target[0]:
                    dx = 1
                elif npc["x"] > target[0]:
                    dx = -1
                elif npc["y"] < target[1]:
                    dy = 1
                elif npc["y"] > target[1]:
                    dy = -1

                new_x = npc["x"] + dx
                new_y = npc["y"] + dy

                if new_x == target[0] and new_y == target[1]:
                    npc["patrol_index"] = (npc["patrol_index"] + 1) % len(npc["patrol_points"])

            elif npc["movement"] == "random":
                dirs = [(1,0), (-1,0), (0,1), (0,-1)]
                for _ in range(4):
                    dx, dy = random.choice(dirs)
                    new_x = npc["x"] + dx
                    new_y = npc["y"] + dy
                    if self.is_walkable_for_npc(new_x, new_y, npc):
                        break
                else:
                    new_x, new_y = npc["x"], npc["y"]

            if self.is_walkable_for_npc(new_x, new_y, npc):
                npc["x"] = new_x
                npc["y"] = new_y
                npc["last_move_time"] = current_time
                npc["stuck_counter"] = 0
            else:
                npc["stuck_counter"] = npc.get("stuck_counter", 0) + 1
                if npc["stuck_counter"] > 3 and npc["movement"] == "random":
                    npc["last_move_time"] = current_time - npc["move_delay_ms"] + 50

    def reset_npcs_near_door(self, door_x, door_y):
        for npc in self.npcs:
            if abs(npc["x"] - door_x) <= 1 and abs(npc["y"] - door_y) <= 1:
                npc["last_move_time"] = 0