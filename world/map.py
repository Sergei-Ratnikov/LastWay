# world/map.py
import json
import pygame
import os
import random
from settings import *
from world.location_manager import LocationManager
from world.tile_data import TileData
from logger import log

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
        self.containers = []    # список объектов Container - entities/container.py
        self.drops = []         # список объектов ItemDrop - entities/drop.py
        self.cats = []          # кошка - entities/cat.py
        self.player_start = (0, 0)
        self.tile_data = TileData()
        self.load()

    def load(self):
        data = self.location_manager.get_location_data(self.location_id)
        
        self.width = data.get("width", 18)
        self.height = data.get("height", 14)
        self.tiles = data.get("tiles", [])
        self.npcs = data.get("npcs", [])

        # Загрузка контейнеров
        for container_data in data.get("containers", []):
            from entities.container import Container
            container = Container(
                container_id=container_data.get("id"),
                x=container_data.get("x"),
                y=container_data.get("y"),
                name=container_data.get("name", "Сундук"),
                locked=container_data.get("locked", False),
                items=container_data.get("items", [])
            )
            self.containers.append(container)

        # Загрузка дропов
        for drop_data in data.get("drops", []):
            from entities.drop import ItemDrop
            drop = ItemDrop(
                drop_id=drop_data.get("id"),
                x=drop_data.get("x"),
                y=drop_data.get("y"),
                items=drop_data.get("items", [])
            )
            self.drops.append(drop)

        # Загрузка кошек (эмерджентные NPC)
        for cat_data in data.get("cats", []):
            from entities.cat import Cat
            cat = Cat(
                cat_id=cat_data.get("id"),
                x=cat_data.get("x"),
                y=cat_data.get("y"),
                food_pos=cat_data.get("food_pos"),
                bed_pos=cat_data.get("bed_pos"),
                toy_pos=cat_data.get("toy_pos")
            )
            self.cats.append(cat)

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
                log.warning(f"Ошибка загрузки NPC {npc_id}: {e}")
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
                "stuck_counter": 0,
                "follow_target": npc_data.get("follow_target", None)
            })

        self.npcs = npcs_loaded

        self.exits = data.get("exits", [])
        self.player_start = data.get("player_start", [1, 1])

    def is_walkable(self, x, y):
        """
        Проходимость для игрока: пол (1), открытая дверь (2), и нет NPC
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        
        # Нельзя проходить сквозь NPC и контейнеры
        if self.get_npc_at(x, y) or self.get_container_at(x, y):
            return False

        tile = self.tiles[y][x]
        return self.tile_data.is_walkable(tile)

    def is_walkable_for_npc(self, x, y, current_npc, ignore_doors=False):
        """
        Проверяет, может ли NPC войти в клетку (x, y).
        Если ignore_doors=True — двери считаются проходимыми (для BFS).
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False

        tile = self.tiles[y][x]
        if ignore_doors:
            # Двери считаем проходимыми, стены — нет
            prop = self.tile_data.get(tile)
            is_door = prop.get("is_door", False) if prop else False
            if not is_door and not self.tile_data.is_walkable(tile):
                return False
        else:
            if not self.tile_data.is_walkable(tile):
                return False

        # Нельзя проходить сквозь игрока
        if self.game_state.player["x"] == x and self.game_state.player["y"] == y:
            return False

        # Нельзя проходить сквозь других NPC
        for npc in self.npcs:
            if npc != current_npc and npc["x"] == x and npc["y"] == y:
                return False

        # Нельзя проходить сквозь контейнеры
        if self.get_container_at(x, y) is not None:
            return False

        return True


    def is_walkable_static(self, x, y):
        """
        Проверка для BFS: стены и контейнеры. 
        Двери и NPC игнорируются (двери можно открыть, NPC обойти).
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
            
        tile = self.tiles[y][x]
        prop = self.tile_data.get(tile)
        if not prop:
            return False
            
        # Двери считаем проходимыми для прокладки маршрута
        if prop.get("is_door", False):
            return True
            
        # Стены и прочее (если не walkable) блокируют
        if not prop.get("walkable", False):
            return False
            
        # Контейнеры (сундуки) блокируют
        if self.get_container_at(x, y) is not None:
            return False
            
        return True


    def is_walkable_for_cat(self, x, y):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        tile = self.tiles[y][x]
        if not self.tile_data.is_walkable(tile):
            return False
        # Кошка не может проходить сквозь NPC и игрока
        if self.get_npc_at(x, y) is not None:
            return False
        if self.game_state.player["x"] == x and self.game_state.player["y"] == y:
            return False
        # Дропы и контейнеры НЕ блокируют кошку
        return True

    def is_door(self, x, y):
        """Универсальная проверка: является ли клетка дверью (открытой или закрытой)."""
        tile = self.get_tile_type(x, y)
        if tile is None:
            return False
        prop = self.tile_data.get(tile)
        return prop.get("is_door", False) if prop else False

    def _get_adjacent_door(self, x, y):
        """Ищет соседнюю дверь (по горизонтали или вертикали), чтобы сделать дверь шириной в 2 клетки."""
        # Проверяем 4 направления
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if self.is_door(nx, ny):
                return (nx, ny)
        return None

    def open_door(self, x, y):
        if x == self.game_state.player["x"] and y == self.game_state.player["y"]:
            log.warning("Нельзя открыть дверь там, где стоит игрок")
            return False
            
        if not self.is_door(x, y):
            log.warning(f"Не удалось открыть: ({x},{y}) не дверь")
            return False

        # Открываем первую половину
        self.tiles[y][x] = 2
        self.game_state.set_door_state(x, y, 2)
        log.info(f"Дверь {x},{y} успешно открыта")
        
        # Ищем и открываем вторую половину
        adjacent = self._get_adjacent_door(x, y)
        if adjacent:
            ax, ay = adjacent
            self.tiles[ay][ax] = 2
            self.game_state.set_door_state(ax, ay, 2)
            log.info(f"Соседняя дверь {ax},{ay} тоже открыта (дверь 2x1)")
            
        return True

    def close_door(self, x, y):
        if not self.is_door(x, y):
            return False

        # Закрываем первую половину
        self.tiles[y][x] = 5
        self.game_state.set_door_state(x, y, 5)
        log.info(f"Дверь {x},{y} закрыта")
        
        # Ищем и закрываем вторую половину
        adjacent = self._get_adjacent_door(x, y)
        if adjacent:
            ax, ay = adjacent
            self.tiles[ay][ax] = 5
            self.game_state.set_door_state(ax, ay, 5)
            log.info(f"Соседняя дверь {ax},{ay} тоже закрыта")
            
        return True

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
        # 1. Отрисовка тайлов
        for y in range(self.height):
            for x in range(self.width):
                tile = self.tiles[y][x]
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

                prop = self.tile_data.get(tile)
                if prop and "color" in prop:
                    color = tuple(prop["color"])
                else:
                    color = BLACK

                pygame.draw.rect(screen, color, rect)      # ← ЭТО БЫЛО ПРОПУЩЕНО
                pygame.draw.rect(screen, BLACK, rect, 1)   # рамка

        # 2. Отрисовка точек выхода (поверх тайлов)
        for exit_data in self.exits:
            x = exit_data.get("x")
            y = exit_data.get("y")
            if x is not None and y is not None:
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, EXIT_COLOR, rect)
                pygame.draw.rect(screen, BLACK, rect, 2)   # толстая рамка

        # 3. Отрисовка контейнеров
        for container in self.containers:
            if container.is_destroyed:
                continue
            rect = pygame.Rect(container.x * TILE_SIZE, container.y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            # Цвет: замок и состояние
            if container.locked:
                color = (150, 50, 0)  # тёмно-оранжевый
            elif container.is_open:
                color = (180, 120, 50)  # светло-коричневый
            else:
                color = (120, 80, 30)  # коричневый
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, BLACK, rect, 2)
            font = pygame.font.Font(None, 16)
            name_text = font.render(container.name, True, WHITE)
            screen.blit(name_text, (container.x * TILE_SIZE, container.y * TILE_SIZE - 15))


        # 4. Отрисовка дропов (предметов на земле)
        for drop in self.drops:
            if drop.is_empty:
                continue
            rect = pygame.Rect(drop.x * TILE_SIZE, drop.y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            # Временно жёлтый цвет, потом заменишь на иконку
            pygame.draw.rect(screen, (255, 255, 100), rect)
            pygame.draw.rect(screen, BLACK, rect, 2)
            # Маленький текст с количеством предметов
            font = pygame.font.Font(None, 14)
            count_text = font.render(str(len(drop.items)), True, BLACK)
            screen.blit(count_text, (drop.x * TILE_SIZE + 18, drop.y * TILE_SIZE + 15))


        # Отрисовка кошек
        for cat in self.cats:
            rect = pygame.Rect(cat.x * TILE_SIZE, cat.y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, (255, 180, 100), rect)
            pygame.draw.rect(screen, BLACK, rect, 2)

            # Три цифры потребностей (голод, энергия, скука)
            font = pygame.font.Font(None, 14)
            needs_text = font.render(
                f"{cat.hunger} {cat.energy} {cat.boredom}",
                True, BLACK
            )
            screen.blit(needs_text, (cat.x * TILE_SIZE + 2, cat.y * TILE_SIZE + 18))


        # Отрисовка точек интереса кошек (для отладки)
        for cat in self.cats:
            font = pygame.font.Font(None, 14)
            
            if cat.food_pos:
                fx, fy = cat.food_pos
                rect = pygame.Rect(fx * TILE_SIZE, fy * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, (100, 255, 100), rect, 2)  # зелёная рамка
                label = font.render("еда", True, (100, 255, 100))
                screen.blit(label, (fx * TILE_SIZE + 4, fy * TILE_SIZE + 4))
            
            if cat.bed_pos:
                bx, by = cat.bed_pos
                rect = pygame.Rect(bx * TILE_SIZE, by * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, (100, 100, 255), rect, 2)  # синяя рамка
                label = font.render("сон", True, (100, 100, 255))
                screen.blit(label, (bx * TILE_SIZE + 4, by * TILE_SIZE + 4))
            
            if cat.toy_pos:
                tx, ty = cat.toy_pos
                rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, (255, 255, 100), rect, 2)  # жёлтая рамка
                label = font.render("игра", True, (255, 255, 100))
                screen.blit(label, (tx * TILE_SIZE + 4, ty * TILE_SIZE + 4))


        # 5. Отрисовка NPC (поверх всего)
        for npc in self.npcs:
            rect = pygame.Rect(npc["x"] * TILE_SIZE, npc["y"] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, NPC_COLOR, rect)
            pygame.draw.rect(screen, BLACK, rect, 2)
            font = pygame.font.Font(None, 16)
            name_text = font.render(npc["name"], True, WHITE)
            screen.blit(name_text, (npc["x"] * TILE_SIZE, npc["y"] * TILE_SIZE - 15))

            # Линия направления для NPC
            if npc.get("movement") != "stationary" and len(npc.get("patrol_points", [])) > 0:
                patrol_points = npc["patrol_points"]
                current_index = npc.get("patrol_index", 0)
                target = patrol_points[current_index]

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

    def update_cats(self, current_time):
        for cat in self.cats:
            cat.update_needs(current_time)
            cat.decide_action(self)
            cat.move_towards_target(self, current_time)

    def get_exit_at(self, x, y):
        '''
        обработка перехода между локациями
        '''
        for exit_data in self.exits:
            if exit_data.get("x") == x and exit_data.get("y") == y:
                return exit_data
        return None
    
    def get_container_at(self, x, y):
        for container in self.containers:
            if container.x == x and container.y == y and not container.is_destroyed:
                return container
        return None

    def get_drop_at(self, x, y):
        '''Возвращает кучу предметов в клетке (x, y) или None'''
        for drop in self.drops:
            if drop.x == x and drop.y == y and not drop.is_empty:
                return drop
        return None

    def get_cat_at(self, x, y):
        for cat in self.cats:
            if cat.x == x and cat.y == y:
                return cat
        return None