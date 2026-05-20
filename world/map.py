# world/map.py
import json
import pygame
import os
import random
from settings import *
from world.location_manager import LocationManager

class Map:

    def __init__(self, location_id, game_state, location_manager=None):
        self.location_id = location_id
        self.game_state = game_state
        self.location_manager = location_manager or LocationManager()
        self.width = 0
        self.height = 0
        self.tiles = []
        self.npcs = []
        self.exits = []
        self.player_start = (0, 0)
        self.load()

    def load(self):
        data = self.location_manager.get_location_data(self.location_id)
        
        self.width = data.get("width", 18)
        self.height = data.get("height", 14)
        self.tiles = data.get("tiles", [])
        self.npcs = data.get("npcs", [])

        # Загрузка данных NPC из отдельных файлов
        npcs_loaded = []
        for npc_ref in self.npcs:
            npc_id = npc_ref.get("npc_id") or npc_ref.get("id")
            npc_path = os.path.join(
                self.location_manager.get_location_path(self.location_id),
                "npcs",
                f"{npc_id}.json"
            )
            try:
                with open(npc_path, "r", encoding="utf-8") as f:
                    npc_data = json.load(f)
            except Exception as e:
                print(f"Ошибка загрузки NPC {npc_id}: {e}")
                continue

            # Объединяем данные из location.json (координаты) и из файла NPC (параметры)
            npcs_loaded.append({
                "id": npc_id,
                "x": npc_ref.get("x", 0),
                "y": npc_ref.get("y", 0),
                "name": npc_data.get("name", "Незнакомец"),
                "dialog_id": npc_data.get("dialog_id", npc_id),
                "movement": npc_data.get("movement", "stationary"),
                "move_delay_ms": npc_data.get("move_delay_ms", 1000),
                "patrol_points": npc_data.get("patrol_points", []),
                "patrol_index": 0,
                "last_move_time": 0,
                "stuck_counter": 0
            })

        self.npcs = npcs_loaded

        self.exits = data.get("exits", [])
        self.player_start = data.get("player_start", [1, 1])


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
        if x == self.game_state.player["x"] and y == self.game_state.player["y"]:
            print("Нельзя открыть дверь там, где стоит игрок")
            return False
        print(f"open_door({x}, {y}) -> tile = {self.get_tile_type(x, y)}")
        if self.get_tile_type(x, y) in (5, 6, 7, 8, 9):
            self.tiles[y][x] = 2
            self.game_state.set_door_state(x, y, 2)
            print(f"Дверь {x},{y} успешно открыта")
            return True
        print(f"Не удалось открыть: не дверь")
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
            # --- Линия направления для NPC
            if npc.get("movement") != "stationary" and len(npc.get("patrol_points", [])) > 0:
                patrol_points = npc["patrol_points"]
                current_index = npc.get("patrol_index", 0)
                target = patrol_points[current_index]
                
                # Определяем координаты цели (если словарь — берём pos)
                if isinstance(target, dict):
                    target_x, target_y = target.get("pos", [npc["x"], npc["y"]])
                else:
                    target_x, target_y = target[0], target[1]
                
                dx = target_x - npc["x"]
                dy = target_y - npc["y"]
                if dx != 0:
                    dx = 1 if dx > 0 else -1
                if dy != 0:
                    dy = 1 if dy > 0 else -1
                
                cx = npc["x"] * TILE_SIZE + TILE_SIZE // 2
                cy = npc["y"] * TILE_SIZE + TILE_SIZE // 2
                end_x = cx + dx * 20
                end_y = cy + dy * 20
                pygame.draw.line(screen, (255, 200, 0), (cx, cy), (end_x, end_y), 2)

    def reset_npcs_near_door(self, door_x, door_y):
        for npc in self.npcs:
            if abs(npc["x"] - door_x) <= 1 and abs(npc["y"] - door_y) <= 1:
                npc["last_move_time"] = 0

    def reset_all_npcs_timer(self):
        for npc in self.npcs:
            npc["last_move_time"] = 0

    def update_npcs(self, current_time, player_x, player_y):
        for npc in self.npcs:
            if npc["movement"] == "stationary":
                continue

            # Задержка движения
            if current_time - npc.get("last_move_time", 0) < npc.get("move_delay_ms", 1000):
                continue

            # Задержка ожидания (wait)
            if npc.get("wait_until", 0) > current_time:
                continue

            # --- ОТКРЫТЬ ДВЕРЬ ПОД СОБОЙ ---
            tile_below = self.get_tile_type(npc["x"], npc["y"])
            if tile_below in (5, 6, 7, 8, 9):
                self.open_door(npc["x"], npc["y"])
                self.reset_npcs_near_door(npc["x"], npc["y"])
                print(f"NPC {npc['name']} открыл дверь под собой {npc['x']},{npc['y']}")
                npc["last_move_time"] = current_time
                continue

            # Получаем текущую цель
            patrol_points = npc.get("patrol_points", [])
            if not patrol_points:
                continue

            current_index = npc.get("patrol_index", 0)
            target = patrol_points[current_index]

            # Определяем координаты цели
            if isinstance(target, list):
                target_x, target_y = target[0], target[1]
                action = None
            else:
                target_x = target.get("pos", [npc["x"], npc["y"]])[0]
                target_y = target.get("pos", [npc["x"], npc["y"]])[1]
                action = target.get("action")

            # Вычисляем направление к цели
            dx = 0
            dy = 0
            if npc["x"] < target_x:
                dx = 1
            elif npc["x"] > target_x:
                dx = -1
            elif npc["y"] < target_y:
                dy = 1
            elif npc["y"] > target_y:
                dy = -1

            new_x = npc["x"] + dx
            new_y = npc["y"] + dy

            # --- ОТКРЫТЬ ДВЕРЬ ПЕРЕД СОБОЙ (по направлению) ---
            door_ahead_x = npc["x"] + dx
            door_ahead_y = npc["y"] + dy
            tile_ahead = self.get_tile_type(door_ahead_x, door_ahead_y)
            if tile_ahead in (5, 6, 7, 8, 9):
                self.open_door(door_ahead_x, door_ahead_y)
                self.reset_npcs_near_door(door_ahead_x, door_ahead_y)
                print(f"NPC {npc['name']} открыл дверь впереди {door_ahead_x},{door_ahead_y}")
                npc["last_move_time"] = current_time
                continue

            # Проверка: если уже стоим на цели ИЛИ сделали шаг и попали
            already_on_target = (dx == 0 and dy == 0)
            reached = (new_x == target_x and new_y == target_y)

            if already_on_target or reached:
                # Выполняем действие, если есть
                if action:
                    if action == "open_door":
                        door_dir = target.get("direction", (0, 0))
                        door_x = npc["x"] + door_dir[0]
                        door_y = npc["y"] + door_dir[1]
                        self.open_door(door_x, door_y)
                        self.reset_npcs_near_door(door_x, door_y)
                        print(f"NPC {npc['name']} выполнил open_door {door_x},{door_y}")
                    elif action == "close_door":
                        door_dir = target.get("direction", (0, 0))
                        door_x = npc["x"] + door_dir[0]
                        door_y = npc["y"] + door_dir[1]
                        self.close_door(door_x, door_y)
                        self.reset_npcs_near_door(door_x, door_y)
                        print(f"NPC {npc['name']} выполнил close_door {door_x},{door_y}")
                    elif action == "face":
                        npc["facing"] = target.get("direction", (0, 0))
                    elif action == "wait":
                        duration = target.get("duration", 500)
                        npc["wait_until"] = current_time + duration
                        npc["last_move_time"] = current_time
                        continue

                # Переход к следующей точке
                next_index = (current_index + 1) % len(patrol_points)
                npc["patrol_index"] = next_index
                npc["last_move_time"] = current_time
                continue

            # Движение к цели (проверка коллизий)
            if self.is_walkable_for_npc(new_x, new_y, npc):
                npc["x"] = new_x
                npc["y"] = new_y
                npc["last_move_time"] = current_time
                npc["stuck_counter"] = 0
            else:
                npc["stuck_counter"] = npc.get("stuck_counter", 0) + 1
                if npc["stuck_counter"] > 3 and npc["movement"] == "random":
                    npc["last_move_time"] = current_time - npc.get("move_delay_ms", 1000) + 50