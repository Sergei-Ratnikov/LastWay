# world/map.py
# =============================================================================
# КАРТА ЛОКАЦИИ
# Загружает данные из JSON, управляет тайлами, NPC, животными, контейнерами, дропами.
# =============================================================================

import json
import pygame
import os
import random
from settings import *
from world.location_manager import LocationManager
from world.tile_data import TileData
from logger import log

from entities.npc import NPC
from entities.animal import Animal


class Map:
    def __init__(self, location_id, game_state, location_manager=None):
        self.location_id = location_id
        self.game_state = game_state
        self.location_manager = location_manager or LocationManager()
        self.width = 0
        self.height = 0
        self.tiles = []

        self.npcs = []
        self.animals = []
        self.containers = []
        self.drops = []

        self.exits = []
        self.player_start = (0, 0)
        self.tile_data = TileData()
        self.load()

    def load(self):
        """Загружает данные локации из JSON и создаёт объекты сущностей."""
        data = self.location_manager.get_location_data(self.location_id)
        self.width = data.get("width", 18)
        self.height = data.get("height", 14)
        self.tiles = data.get("tiles", [])

        # --- NPC ---
        npc_refs = data.get("npcs", [])
        for npc_ref in npc_refs:
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

            npc = NPC(
                npc_id=npc_id,
                name=npc_data.get("name", "Незнакомец"),
                x=npc_ref.get("x", 0),
                y=npc_ref.get("y", 0),
                dialog_id=npc_data.get("dialog_id", npc_id),
                gender=npc_data.get("gender", "male")
            )

            npc.movement = npc_data.get("movement", "stationary")
            npc.move_delay_ms = npc_data.get("move_delay_ms", 1000)
            npc.patrol_points = npc_data.get("patrol_points", [])
            npc.follow_target = npc_data.get("follow_target", None)

            self.npcs.append(npc)

        # --- КОНТЕЙНЕРЫ ---
        for container_data in data.get("containers", []):
            from objects.container import Container
            container = Container(
                container_id=container_data.get("id"),
                x=container_data.get("x"),
                y=container_data.get("y"),
                name=container_data.get("name", "Сундук"),
                locked=container_data.get("locked", False),
                items=container_data.get("items", []),
                width=container_data.get("width", 1),
                height=container_data.get("height", 1),
                access_side=container_data.get("access_side", "all")
            )
            self.containers.append(container)

        # --- ДРОПЫ ---
        for drop_data in data.get("drops", []):
            from objects.drop import ItemDrop
            drop = ItemDrop(
                drop_id=drop_data.get("id"),
                x=drop_data.get("x"),
                y=drop_data.get("y"),
                items=drop_data.get("items", [])
            )
            self.drops.append(drop)

        # --- ЖИВОТНЫЕ ---
        # FIX: читаем из "animals" (ранее был legacy-ключ "cats")
        for animal_data in data.get("animals", []):
            animal = Animal(
                animal_id=animal_data.get("id"),
                name="Кошка",
                x=animal_data.get("x", 0),
                y=animal_data.get("y", 0),
                species="cat",
                behavior_type="emergent_needs"
            )

            food_pos = animal_data.get("food_pos")
            bed_pos = animal_data.get("bed_pos")
            toy_pos = animal_data.get("toy_pos")

            if food_pos:
                animal.points_of_interest["food"] = tuple(food_pos)
            if bed_pos:
                animal.points_of_interest["home"] = tuple(bed_pos)
            if toy_pos:
                animal.points_of_interest["toy"] = tuple(toy_pos)

            self.animals.append(animal)

        # --- ВЫХОДЫ И СТАРТОВАЯ ПОЗИЦИЯ ---
        self.exits = data.get("exits", [])
        self.player_start = data.get("player_start", [1, 1])

    # -------------------------------------------------------------------------
    # ПРОВЕРКИ ПРОХОДИМОСТИ
    # -------------------------------------------------------------------------

    def is_walkable(self, x, y):
        """Проходимость для игрока: пол, открытая дверь, нет NPC/контейнера."""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        if self.get_npc_at(x, y) or self.get_container_at(x, y):
            return False
        tile = self.tiles[y][x]
        return self.tile_data.is_walkable(tile)

    def is_walkable_for_npc(self, x, y, current_npc, ignore_doors=False):
        """Проверяет, может ли NPC войти в клетку (x, y)."""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        tile = self.tiles[y][x]
        if ignore_doors:
            prop = self.tile_data.get(tile)
            is_door = prop.get("is_door", False) if prop else False
            if not is_door and not self.tile_data.is_walkable(tile):
                return False
        else:
            if not self.tile_data.is_walkable(tile):
                return False
        if self.game_state.player.x == x and self.game_state.player.y == y:
            return False
        for npc in self.npcs:
            if npc != current_npc and npc.x == x and npc.y == y:
                return False
        if self.get_container_at(x, y) is not None:
            return False
        return True

    def is_walkable_static(self, x, y):
        """Проверка для BFS: стены и контейнеры. Двери и NPC игнорируются."""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        tile = self.tiles[y][x]
        prop = self.tile_data.get(tile)
        if not prop:
            return False
        if prop.get("is_door", False):
            return True
        if not prop.get("walkable", False):
            return False
        if self.get_container_at(x, y) is not None:
            return False
        return True

    def is_walkable_for_animal(self, x, y):
        """
        Проверка проходимости для животных.
        FIX (#8): теперь животные блокируются контейнерами (сундуки, столы).
        Логика симметрична is_walkable_for_npc, но без параметра current_npc
        и без игнорирования дверей.
        # TODO (#8-продолжение): вынести/доделать логику движения животных.
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        tile = self.tiles[y][x]
        if not self.tile_data.is_walkable(tile):
            return False
        # Животное не может проходить сквозь игрока
        if self.game_state.player.x == x and self.game_state.player.y == y:
            return False
        # Животное не может проходить сквозь NPC
        if self.get_npc_at(x, y) is not None:
            return False
        # Животное не может проходить сквозь контейнеры
        if self.get_container_at(x, y) is not None:
            return False
        return True

    def is_door(self, x, y):
        tile = self.get_tile_type(x, y)
        if tile is None:
            return False
        prop = self.tile_data.get(tile)
        return prop.get("is_door", False) if prop else False

    def _get_adjacent_door(self, x, y):
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if self.is_door(nx, ny):
                return (nx, ny)
        return None

    def open_door(self, x, y):
        if x == self.game_state.player.x and y == self.game_state.player.y:
            log.warning("Нельзя открыть дверь там, где стоит игрок")
            return False
        if not self.is_door(x, y):
            log.warning(f"Не удалось открыть: ({x},{y}) не дверь")
            return False
        self.tiles[y][x] = 2
        self.game_state.set_door_state(x, y, 2)
        log.info(f"Дверь {x},{y} успешно открыта")
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
        self.tiles[y][x] = 5
        self.game_state.set_door_state(x, y, 5)
        log.info(f"Дверь {x},{y} закрыта")
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

    # -------------------------------------------------------------------------
    # ПОИСК СУЩНОСТЕЙ ПО КООРДИНАТАМ
    # -------------------------------------------------------------------------

    def get_npc_at(self, x, y):
        for npc in self.npcs:
            if npc.x == x and npc.y == y:
                return npc
        return None

    def get_animal_at(self, x, y):
        for animal in self.animals:
            if animal.x == x and animal.y == y:
                return animal
        return None

    def get_container_at(self, x, y):
        for container in self.containers:
            if not container.is_destroyed and container.occupies(x, y):
                return container
        return None

    def get_drop_at(self, x, y):
        for drop in self.drops:
            if drop.x == x and drop.y == y and not drop.is_empty:
                return drop
        return None

    def get_exit_at(self, x, y):
        for exit_data in self.exits:
            if exit_data.get("x") == x and exit_data.get("y") == y:
                return exit_data
        return None

    # -------------------------------------------------------------------------
    # ОТРИСОВКА
    # -------------------------------------------------------------------------

    # TODO: перенести в Renderer.py (Map — только данные, Renderer — отрисовка).
    # Делать вместе с шагом 1 (камера), т.к. API render(screen, camera_x, camera_y)
    # всё равно поменяется.
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
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, BLACK, rect, 1)

        # 2. Выходы
        for exit_data in self.exits:
            x = exit_data.get("x")
            y = exit_data.get("y")
            if x is not None and y is not None:
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, EXIT_COLOR, rect)
                pygame.draw.rect(screen, BLACK, rect, 2)

        # 3. Контейнеры
        for container in self.containers:
            if container.is_destroyed:
                continue
            rect = pygame.Rect(
                container.x * TILE_SIZE,
                container.y * TILE_SIZE,
                container.width * TILE_SIZE,
                container.height * TILE_SIZE
            )
            if container.locked:
                color = (150, 50, 0)
            elif container.is_open:
                color = (180, 120, 50)
            else:
                color = (120, 80, 30)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, BLACK, rect, 2)
            font = pygame.font.Font(None, 16)
            name_text = font.render(container.name, True, WHITE)
            screen.blit(name_text, (container.x * TILE_SIZE, container.y * TILE_SIZE - 15))
            if container.access_side != "all":
                cx, cy = rect.centerx, rect.centery
                radius = 4
                if container.access_side == "north":
                    marker_pos = (cx, rect.top + 6)
                elif container.access_side == "south":
                    marker_pos = (cx, rect.bottom - 6)
                elif container.access_side == "west":
                    marker_pos = (rect.left + 6, cy)
                elif container.access_side == "east":
                    marker_pos = (rect.right - 6, cy)
                else:
                    marker_pos = None
                if marker_pos:
                    pygame.draw.circle(screen, WHITE, marker_pos, radius)
                    pygame.draw.circle(screen, BLACK, marker_pos, radius, 1)

        # 4. Дропы
        for drop in self.drops:
            if drop.is_empty:
                continue
            rect = pygame.Rect(drop.x * TILE_SIZE, drop.y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, (255, 255, 100), rect)
            pygame.draw.rect(screen, BLACK, rect, 2)
            font = pygame.font.Font(None, 14)
            count_text = font.render(str(len(drop.items)), True, BLACK)
            screen.blit(count_text, (drop.x * TILE_SIZE + 18, drop.y * TILE_SIZE + 15))

        # 5. Животные
        for animal in self.animals:
            rect = pygame.Rect(animal.x * TILE_SIZE, animal.y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, (255, 180, 100), rect)
            pygame.draw.rect(screen, BLACK, rect, 2)
            font = pygame.font.Font(None, 14)
            needs_text = font.render(
                f"{animal.hunger} {animal.energy} {animal.boredom}",
                True, BLACK
            )
            screen.blit(needs_text, (animal.x * TILE_SIZE + 2, animal.y * TILE_SIZE + 18))

        # 6. Точки интереса
        for animal in self.animals:
            font = pygame.font.Font(None, 14)
            food_pos = animal.points_of_interest.get("food")
            home_pos = animal.points_of_interest.get("home")
            toy_pos = animal.points_of_interest.get("toy")

            if food_pos:
                fx, fy = food_pos
                rect = pygame.Rect(fx * TILE_SIZE, fy * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, (100, 255, 100), rect, 2)
                label = font.render("еда", True, (100, 255, 100))
                screen.blit(label, (fx * TILE_SIZE + 4, fy * TILE_SIZE + 4))
            if home_pos:
                bx, by = home_pos
                rect = pygame.Rect(bx * TILE_SIZE, by * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, (100, 100, 255), rect, 2)
                label = font.render("сон", True, (100, 100, 255))
                screen.blit(label, (bx * TILE_SIZE + 4, by * TILE_SIZE + 4))
            if toy_pos:
                tx, ty = toy_pos
                rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, (255, 255, 100), rect, 2)
                label = font.render("игра", True, (255, 255, 100))
                screen.blit(label, (tx * TILE_SIZE + 4, ty * TILE_SIZE + 4))

        # 7. NPC
        for npc in self.npcs:
            rect = pygame.Rect(npc.x * TILE_SIZE, npc.y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, NPC_COLOR, rect)
            pygame.draw.rect(screen, BLACK, rect, 2)
            font = pygame.font.Font(None, 16)
            name_text = font.render(npc.name, True, WHITE)
            screen.blit(name_text, (npc.x * TILE_SIZE, npc.y * TILE_SIZE - 15))
            if npc.movement != "stationary" and len(npc.patrol_points) > 0:
                patrol_points = npc.patrol_points
                current_index = npc.patrol_index
                target = patrol_points[current_index]
                if isinstance(target, dict):
                    target_x, target_y = target.get("pos", [npc.x, npc.y])
                else:
                    target_x, target_y = target[0], target[1]
                dx = target_x - npc.x
                dy = target_y - npc.y
                if dx != 0:
                    dx = 1 if dx > 0 else -1
                if dy != 0:
                    dy = 1 if dy > 0 else -1
                cx = npc.x * TILE_SIZE + TILE_SIZE // 2
                cy = npc.y * TILE_SIZE + TILE_SIZE // 2
                end_x = cx + dx * 20
                end_y = cy + dy * 20
                pygame.draw.line(screen, (255, 200, 0), (cx, cy), (end_x, end_y), 2)

    # -------------------------------------------------------------------------
    # УПРАВЛЕНИЕ NPC
    # -------------------------------------------------------------------------

    def reset_npcs_near_door(self, door_x, door_y):
        for npc in self.npcs:
            if abs(npc.x - door_x) <= 1 and abs(npc.y - door_y) <= 1:
                npc.last_move_time = 0

    def reset_all_npcs_timer(self):
        for npc in self.npcs:
            npc.last_move_time = 0

    # -------------------------------------------------------------------------
    # ОБНОВЛЕНИЕ ЖИВОТНЫХ
    # -------------------------------------------------------------------------

    def update_animals(self, current_time):
        for animal in self.animals:
            animal.update_needs(current_time)
            animal.decide_action(self)
            animal.move_towards_target(self, current_time)