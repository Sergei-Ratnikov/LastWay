# game_engine.py
import random
import os

import pygame
import sys
from settings import *
from game_state import GameState
from world.map import Map
from systems.dialog_system import DialogSystem
from world.location_manager import LocationManager
from input_handler import InputHandler

from logger import log


class GameEngine:
    """Главный игровой движок. Управляет циклом, событиями, обновлением и отрисовкой."""

    def __init__(self, location_id: str, game_state: GameState = None):
        self.temp_message = None
        self.temp_message_timer = 0

        if not pygame.get_init():
            pygame.init()

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Last Way — пре-альфа")
        self.clock = pygame.time.Clock()

        # Состояние и системы
        self.game_state = game_state if game_state else GameState()
        self.location_manager = LocationManager()
        self.current_map = Map(location_id, self.game_state, self.location_manager)

        # Диалоги
        dialogs_path = os.path.join(
            self.location_manager.get_location_path(location_id),
            "dialogs"
        )
        self.dialog_system = DialogSystem(self.game_state, dialogs_path)

        # Позиция игрока
        player_x, player_y = self.current_map.player_start
        self.game_state.player["x"] = player_x
        self.game_state.player["y"] = player_y
        if not self.game_state.player["class"]:
            self.game_state.player["class"] = "Идальго"

        self.move_queue = []
        self.player_target = None
        self.stuck_counter = 0

        self.input_handler = InputHandler()

        self.last_move_time = 0
        self.facing_direction = (0, 1)

        self.running = True
        self.exit_code = None

        # Лимит веса по классу
        if self.game_state.player["class"] == "Геркулес":
            self.game_state.inventory.max_weight = 80.0
        elif self.game_state.player["class"] == "Идальго":
            self.game_state.inventory.max_weight = 50.0
        elif self.game_state.player["class"] == "Аббатисса":
            self.game_state.inventory.max_weight = 30.0

        self.inventory_open = False

        # ВАЖНО: передаём self (а не game_state и current_map)
        from systems.save_system import SaveSystem
        self.save_system = SaveSystem(self)

        self.save_menu_open = False
        self.save_menu_mode = None  # "save" или "load"
        self.save_menu_selected = 0
        self.save_menu_items = []

        # отработка логики подходить к объекту по клику
        self.pending_interaction = None  # (x, y) — куда взаимодействовать после прихода
        self.pending_target_cell = None  # (x, y) — куда идти
    # -------------------------------------------------------------------------
    # ОСНОВНОЙ ЦИКЛ
    # -------------------------------------------------------------------------
    def run(self) -> str:
        while self.running:
            current_time = pygame.time.get_ticks()
            self.clock.tick(60)
            self.handle_events()
            self.update(current_time)
            self.render()
            pygame.display.flip()
        return self.exit_code or "exit"

    # -------------------------------------------------------------------------
    # СОБЫТИЯ
    # -------------------------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                self.exit_code = "exit"

            # Меню сохранений
            if self.save_menu_open and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.save_menu_open = False
                    continue

                if event.key == pygame.K_UP:
                    self.save_menu_selected = max(0, self.save_menu_selected - 1)
                    continue
                if event.key == pygame.K_DOWN:
                    self.save_menu_selected = min(len(self.save_menu_items) - 1, self.save_menu_selected + 1)
                    continue

                if event.key == pygame.K_RETURN:
                    if self.save_menu_mode == "save":
                        # Создаём новое автосохранение
                        name = self.save_system.next_save_name()
                        if self.save_system.save(name):
                            self._show_message(f"Сохранено: {name}")
                            self.save_menu_open = False
                    elif self.save_menu_mode == "load":
                        if self.save_menu_items:
                            name = self.save_menu_items[self.save_menu_selected]
                            if self.save_system.load(name):
                                self.current_map.reset_all_npcs_timer()
                                # ▼▼▼ СБРОС ОТЛОЖЕННОГО ВЗАИМОДЕЙСТВИЯ ▼▼▼
                                self.pending_interaction = None
                                self.pending_target_cell = None
                                # ▲▲▲
                                self._show_message(f"Загружено: {name}")
                            self.save_menu_open = False
                    continue

            command = self.input_handler.handle_event(event, self.game_state, self.current_map)
            if command:
                self._process_command(command)

    def _process_command(self, command):
        log.info(f"Получена команда {command}")
        if isinstance(command, tuple):
            cmd_type = command[0]

            if cmd_type == "dialog_choice":
                self.dialog_system.choose_option(command[1])

            elif cmd_type == "interact":
                _, target_x, target_y = command
                # Если в радиусе — взаимодействуем сразу
                if self._is_in_range(target_x, target_y):
                    self._handle_interaction(target_x, target_y)
                    return

                # Иначе — идём к объекту
                approach = self._find_approach_cell(target_x, target_y)
                if not approach:
                    self._show_message("Не подойти к объекту")
                    return

                from world.pathfinding import find_path
                path = find_path(
                    self.game_state.player["x"],
                    self.game_state.player["y"],
                    approach[0], approach[1],
                    self.current_map.is_walkable
                )
                if path:
                    self.move_queue = path
                    self.pending_interaction = (target_x, target_y)
                    self.pending_target_cell = approach
                    log.info(f"АВТО-ПОДХОД: к {approach} для взаимодействия с ({target_x},{target_y})")
                else:
                    self._show_message("Путь не найден")

            elif cmd_type == "move_to":
                _, target_x, target_y = command
                from world.pathfinding import find_path
                if not self.current_map.is_walkable(target_x, target_y):
                    return
                self.player_target = (target_x, target_y)
                path = find_path(
                    self.game_state.player["x"],
                    self.game_state.player["y"],
                    target_x, target_y,
                    self.current_map.is_walkable
                )
                if path:
                    self.move_queue = path

        else:
            if command == "interact":
                self._interact()

            elif command == "menu":
                if self.game_state.dialog_active:
                    self.dialog_system.close_dialog()
                else:
                    self.running = False

            elif command == "open_inventory":
                self.inventory_open = not self.inventory_open
                log.info(f"Инвентарь: {'открыт' if self.inventory_open else 'закрыт'}")

            elif command == "context_menu":
                pass

            elif command == "open_save_menu":
                self.save_menu_open = True
                self.save_menu_mode = "save"
                self.save_menu_items = self.save_system.list_saves()
                self.save_menu_selected = 0

            elif command == "open_load_menu":
                self.save_menu_open = True
                self.save_menu_mode = "load"
                self.save_menu_items = self.save_system.list_saves()
                self.save_menu_selected = 0

    def _interact(self):
        nx = self.game_state.player["x"] + self.facing_direction[0]
        ny = self.game_state.player["y"] + self.facing_direction[1]
        if not self._is_in_range(nx, ny):
            self._show_message("Слишком далеко")
            return
        self._handle_interaction(nx, ny)

    def _handle_interaction(self, x, y):
        if not self._is_in_range(x, y):
            self._show_message("Слишком далеко")
            return

        # 1. NPC
        npc = self.current_map.get_npc_at(x, y)
        if npc:
            self.dialog_system.load_dialog(npc["dialog_id"])
            return

        # 2. Контейнер
        container = self.current_map.get_container_at(x, y)
        if container:
            # Проверка стороны доступа
            if not container.can_interact_from(self.game_state.player["x"], self.game_state.player["y"]):
                self._show_message("С этой стороны не подобраться")
                log.info(f"КОНТЕЙНЕР: {container.id} — неверная сторона доступа")
                return

            if container.locked:
                self._show_message("Контейнер заперт")
                log.info(f"КОНТЕЙНЕР: {container.id} заперт")
                return
            
            if not container.is_open:
                container.open()
                log.info(f"КОНТЕЙНЕР: {container.id} открыт")
            if not container.items:
                self._show_message(f"{container.name} пуст")
                return
            items_taken = []
            items_left = []
            for item_id in container.items[:]:
                if self.game_state.inventory.add_item(item_id):
                    container.items.remove(item_id)
                    items_taken.append(item_id)
                    log.info(f"ПЕРЕНОС: игрок забрал {item_id} из {container.name}")
                else:
                    items_left.append(item_id)
                    log.info(f"ПЕРЕНОС: {item_id} не влез (превышен вес)")
            if items_taken:
                self._show_message(f"Из {container.name} взято: {', '.join(items_taken)}")
            if items_left:
                self._show_message(f"Не влезло: {', '.join(items_left)}")
            return

        # 3. Дроп
        drop = self.current_map.get_drop_at(x, y)
        if drop:
            if drop.is_empty:
                self._show_message("Здесь пусто")
                return
            items_text = []
            items_not_taken = []
            for item_id in drop.items[:]:
                if self.game_state.inventory.add_item(item_id):
                    drop.items.remove(item_id)
                    items_text.append(item_id)
                    log.info(f"ПОДБОР: игрок подобрал {item_id} из {drop.id}")
                else:
                    items_not_taken.append(item_id)
                    log.info(f"ПОДБОР: {item_id} не влез (превышен вес)")
            if items_text:
                self._show_message(f"Подобрано: {', '.join(items_text)}")
            if items_not_taken:
                self._show_message(f"Не влезло: {', '.join(items_not_taken)}")
            if drop.is_empty:
                if drop in self.current_map.drops:
                    self.current_map.drops.remove(drop)
                log.info(f"ДРОП: {drop.id} удален с карты")
            return

        # 4. Дверь
        tile_type = self.current_map.get_tile_type(x, y)
        if tile_type in (5, 6, 7, 8, 9):
            self.current_map.open_door(x, y)
            self.current_map.reset_npcs_near_door(x, y)
        elif tile_type == 2:
            self.current_map.close_door(x, y)
            self.current_map.reset_npcs_near_door(x, y)

    def _is_in_range(self, target_x, target_y, radius=None):
        if radius is None:
            radius = INTERACT_RADIUS
        px, py = self.game_state.player["x"], self.game_state.player["y"]
        return abs(px - target_x) + abs(py - target_y) <= radius

    # -------------------------------------------------------------------------
    # ОБНОВЛЕНИЕ
    # -------------------------------------------------------------------------
    def update(self, current_time: int):
        if self.game_state.dialog_active:
            return
        if self.inventory_open:
            return

        if self.save_menu_open:
            return

        # Движение игрока
        if self.move_queue:
            self._move_entity_step(self.game_state.player, is_player=True)
        else:
            keys = pygame.key.get_pressed()
            dx = dy = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1; self.facing_direction = (-1, 0)
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1; self.facing_direction = (1, 0)
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1; self.facing_direction = (0, -1)
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1; self.facing_direction = (0, 1)

            if dx != 0 or dy != 0:
                self.pending_interaction = None
                self.pending_target_cell = None

            if (dx != 0 or dy != 0) and current_time - self.last_move_time >= MOVE_DELAY_MS:
                nx = self.game_state.player["x"] + dx
                ny = self.game_state.player["y"] + dy
                if self.current_map.is_walkable(nx, ny):
                    self.game_state.player["x"] = nx
                    self.game_state.player["y"] = ny
                    self.last_move_time = current_time

        # Проверяем отложенное взаимодействие
        # (подойти к объекту по клику)
        if self.pending_interaction and not self.move_queue:
            px, py = self.game_state.player["x"], self.game_state.player["y"]
            tx, ty = self.pending_interaction
            if self._is_in_range(tx, ty):
                self._handle_interaction(tx, ty)
                log.info(f"АВТО-ВЗАИМОДЕЙСТВИЕ: с ({tx},{ty})")
                self.pending_interaction = None
                self.pending_target_cell = None
            elif self.pending_target_cell == (px, py):
                # Мы на подходе, но не в радиусе — сброс
                self.pending_interaction = None
                self.pending_target_cell = None

        # Переход между локациями
        exit_point = self.current_map.get_exit_at(
            self.game_state.player["x"], self.game_state.player["y"]
        )
        if exit_point:
            self.switch_location(exit_point["target_location"], exit_point["target_exit_id"])
            return

        # Движение NPC
        for npc in self.current_map.npcs:
            if npc["movement"] == "stationary":
                continue
            if npc.get("wait_until", 0) > current_time:
                continue

            # Следование за другим NPC
            if npc["movement"] == "follow" and npc.get("follow_target"):
                target_npc = None
                for other in self.current_map.npcs:
                    if other["id"] == npc["follow_target"]:
                        target_npc = other
                        break
                if target_npc:
                    if abs(npc["x"] - target_npc["x"]) + abs(npc["y"] - target_npc["y"]) <= 1:
                        npc["path"] = []
                        npc["last_move_time"] = current_time
                        continue
                    if not npc.get("path"):
                        from world.pathfinding import find_path
                        path = find_path(npc["x"], npc["y"], target_npc["x"], target_npc["y"], self.current_map.is_walkable_static)
                        if path:
                            npc["path"] = path
                        else:
                            npc["last_move_time"] = current_time
                    self._move_entity_step(npc, is_player=False)
                    continue

            # Патрулирование
            if npc.get("patrol_points"):
                target = npc["patrol_points"][npc.get("patrol_index", 0)]
                if isinstance(target, list):
                    tx, ty = target[0], target[1]
                else:
                    tx, ty = target.get("pos", [npc["x"], npc["y"]])[0], target.get("pos", [npc["x"], npc["y"]])[1]
                if (npc["x"], npc["y"]) == (tx, ty):
                    npc["patrol_index"] = (npc.get("patrol_index", 0) + 1) % len(npc["patrol_points"])
                    npc["last_move_time"] = current_time
                    continue

            if not npc.get("path") and npc.get("patrol_points"):
                if npc.get("wait_until", 0) > current_time:
                    continue
                target = npc["patrol_points"][npc.get("patrol_index", 0)]
                if isinstance(target, list):
                    tx, ty = target[0], target[1]
                else:
                    tx, ty = target.get("pos", [npc["x"], npc["y"]])[0], target.get("pos", [npc["x"], npc["y"]])[1]
                from world.pathfinding import find_path
                path = find_path(npc["x"], npc["y"], tx, ty, self.current_map.is_walkable_static)
                if path:
                    npc["path"] = path

            self._move_entity_step(npc, is_player=False)

        # Кошки
        self.current_map.update_cats(current_time)

    # -------------------------------------------------------------------------
    # ПЕРЕХОД МЕЖДУ ЛОКАЦИЯМИ
    # -------------------------------------------------------------------------
    def switch_location(self, target_location_id, target_exit_id):
        # --- 1. СОХРАНЯЕМ СОСТОЯНИЕ ТЕКУЩЕЙ ЛОКАЦИИ ---
        current_location_id = self.current_map.location_id
        state_data = {
            "doors": dict(self.game_state.door_states),
            "npcs": [],
            "containers": [],
            "drops": [],
        }
        for npc in self.current_map.npcs:
            state_data["npcs"].append({
                "id": npc["id"], "x": npc["x"], "y": npc["y"],
                "patrol_index": npc.get("patrol_index", 0),
                "path": npc.get("path", []),
            })
        for container in self.current_map.containers:
            state_data["containers"].append({
                "id": container.id,
                "x": container.x,
                "y": container.y,
                "width": container.width,
                "height": container.height,
                "is_open": container.is_open,
                "items": container.items.copy(),
                "access_side": container.access_side,   # <-- сохраняем
            })

        for drop in self.current_map.drops:
            state_data["drops"].append({
                "id": drop.id, "x": drop.x, "y": drop.y, "items": drop.items.copy()
            })
        self.location_manager.save_location_state(current_location_id, state_data)
        log.info(f"ПЕРЕХОД: сохранено состояние {current_location_id}")

        # --- 2. ЗАГРУЖАЕМ НОВУЮ ЛОКАЦИЮ ---
        self.current_map = Map(target_location_id, self.game_state, self.location_manager)
        self.game_state.door_states = {}

        # Пересоздаём dialog_system под новую локацию
        dialogs_path = os.path.join(
            self.location_manager.get_location_path(target_location_id),
            "dialogs"
        )
        self.dialog_system = DialogSystem(self.game_state, dialogs_path)

        # --- 3. ПРИМЕНЯЕМ СОХРАНЁННОЕ СОСТОЯНИЕ ---
        saved_state = self.location_manager.get_location_state(target_location_id)
        if saved_state:
            log.info(f"ПЕРЕХОД: восстановлено состояние {target_location_id}")
            for coord, tile_type in saved_state["doors"].items():
                if "," in coord:
                    xs, ys = coord.split(",")
                    x, y = int(xs), int(ys)
                    if 0 <= x < self.current_map.width and 0 <= y < self.current_map.height:
                        self.current_map.tiles[y][x] = tile_type
                        self.game_state.door_states[coord] = tile_type
            for npc_save in saved_state["npcs"]:
                for npc in self.current_map.npcs:
                    if npc["id"] == npc_save["id"]:
                        npc["x"] = npc_save["x"]
                        npc["y"] = npc_save["y"]
                        npc["patrol_index"] = npc_save["patrol_index"]
                        npc["path"] = [tuple(p) for p in npc_save["path"]]
                        npc["wait_until"] = 0
                        break
            for cont_save in saved_state["containers"]:
                for container in self.current_map.containers:
                    if container.id == cont_save["id"]:
                        container.is_open = cont_save["is_open"]
                        container.items = cont_save["items"].copy()
                        break
            self.current_map.drops.clear()
            from entities.drop import ItemDrop
            for drop_save in saved_state["drops"]:
                self.current_map.drops.append(ItemDrop(
                    drop_id=drop_save["id"], x=drop_save["x"], y=drop_save["y"],
                    items=drop_save["items"].copy()
                ))

        # --- 4. СТАВИМ ИГРОКА НА ТОЧКУ ВЫХОДА ---
        for exit_data in self.current_map.exits:
            if exit_data.get("id") == target_exit_id:
                self.game_state.player["x"] = exit_data["spawn_x"]
                self.game_state.player["y"] = exit_data["spawn_y"]
                break

        self.last_move_time = pygame.time.get_ticks()
        self.move_queue = []
        # ▼▼▼ СБРОС ОТЛОЖЕННОГО ВЗАИМОДЕЙСТВИЯ ▼▼▼
        self.pending_interaction = None
        self.pending_target_cell = None
        # ▲▲▲

    # -------------------------------------------------------------------------
    # ОТРИСОВКА
    # -------------------------------------------------------------------------
    def render(self):
        self.screen.fill(BLACK)
        self.current_map.render(self.screen, 0, 0)

        # Игрок
        px, py = self.game_state.player["x"], self.game_state.player["y"]
        pygame.draw.rect(self.screen, GREEN, (px*TILE_SIZE, py*TILE_SIZE, TILE_SIZE, TILE_SIZE))
        cx = px*TILE_SIZE + TILE_SIZE//2
        cy = py*TILE_SIZE + TILE_SIZE//2
        ex = cx + self.facing_direction[0]*20
        ey = cy + self.facing_direction[1]*20
        pygame.draw.line(self.screen, YELLOW, (cx, cy), (ex, ey), 3)

        # Верхняя панель
        font = pygame.font.Font(None, 24)
        info = font.render(
            f"Класс: {self.game_state.player['class']}  |  Дней: {self.game_state.days_left}  |  Человечность: {self.game_state.humanity}",
            True, WHITE
        )
        self.screen.blit(info, (10, 10))
        if not self.game_state.dialog_active:
            help_text = font.render("E — открыть дверь / говорить с NPC", True, WHITE)
        else:
            help_text = font.render("E/ESC — закрыть диалог", True, WHITE)
        self.screen.blit(help_text, (10, 40))

        # Диалог
        if self.game_state.dialog_active:
            surf = pygame.Surface((WIDTH - 100, 160))
            surf.set_alpha(220)
            surf.fill(BLACK)
            self.screen.blit(surf, (50, HEIGHT - 210))
            pygame.draw.rect(self.screen, WHITE, (50, HEIGHT - 210, WIDTH - 100, 160), 2)
            for i, line in enumerate(self.game_state.dialog_text.split('\n')):
                if i * 25 < 100:
                    self.screen.blit(font.render(line[:65], True, WHITE), (55, HEIGHT - 200 + i * 25))
            for i, opt in enumerate(self.game_state.dialog_options):
                self.screen.blit(font.render(f"{i+1}. {opt['text']}", True, GREEN), (55, HEIGHT - 110 + i * 25))
            if not self.game_state.dialog_options:
                hint = font.render("Нажми E или ESC, чтобы продолжить", True, (150, 150, 150))
                self.screen.blit(hint, (55, HEIGHT - 85))

        # Инвентарь
        if self.inventory_open:
            surf = pygame.Surface((WIDTH - 200, HEIGHT - 200))
            surf.set_alpha(230)
            surf.fill(BLACK)
            self.screen.blit(surf, (100, 100))
            pygame.draw.rect(self.screen, WHITE, (100, 100, WIDTH - 200, HEIGHT - 200), 3)
            title_font = pygame.font.Font(None, 36)
            self.screen.blit(title_font.render("Инвентарь", True, YELLOW), (120, 120))
            item_font = pygame.font.Font(None, 24)
            items = self.game_state.inventory.get_items()
            if not items:
                self.screen.blit(item_font.render("(пусто)", True, (150, 150, 150)), (120, 170))
            else:
                for i, item_id in enumerate(items):
                    if i >= 15:
                        break
                    self.screen.blit(item_font.render(f"{i+1}. {item_id}", True, WHITE), (120, 170 + i*30))
            self.screen.blit(item_font.render("Нажми I, чтобы закрыть", True, (150, 150, 150)), (120, HEIGHT - 130))

        # Временное сообщение
        if self.temp_message:
            if pygame.time.get_ticks() - self.temp_message_timer < 2000:
                font = pygame.font.Font(None, 28)
                text_surf = font.render(self.temp_message, True, WHITE)
                text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT - 100))
                bg_rect = text_rect.inflate(20, 10)
                pygame.draw.rect(self.screen, BLACK, bg_rect)
                pygame.draw.rect(self.screen, WHITE, bg_rect, 2)
                self.screen.blit(text_surf, text_rect)
            else:
                self.temp_message = None

        # Меню сохранений
        if self.save_menu_open:
            # Затенение
            surf = pygame.Surface((WIDTH, HEIGHT))
            surf.set_alpha(180)
            surf.fill(BLACK)
            self.screen.blit(surf, (0, 0))

            # Окно
            box = pygame.Rect(WIDTH // 2 - 250, 100, 500, 450)
            pygame.draw.rect(self.screen, BLACK, box)
            pygame.draw.rect(self.screen, WHITE, box, 3)

            title_font = pygame.font.Font(None, 36)
            item_font = pygame.font.Font(None, 26)
            hint_font = pygame.font.Font(None, 20)

            title_text = "Сохранить игру" if self.save_menu_mode == "save" else "Загрузить игру"
            title = title_font.render(title_text, True, YELLOW)
            self.screen.blit(title, (box.x + 20, box.y + 20))

            # Список (для save показываем все существующие, для load — только их)
            y = box.y + 80
            if not self.save_menu_items:
                empty = item_font.render("(нет сохранений)", True, (150, 150, 150))
                self.screen.blit(empty, (box.x + 20, y))
            else:
                for i, name in enumerate(self.save_menu_items):
                    color = GREEN if i == self.save_menu_selected else WHITE
                    marker = "> " if i == self.save_menu_selected else "  "
                    text = item_font.render(marker + name, True, color)
                    self.screen.blit(text, (box.x + 20, y + i * 30))

            # Подсказка
            if self.save_menu_mode == "save":
                hint = "Enter — создать новое сохранение (автономер)"
            else:
                hint = "Enter — загрузить выбранное"
            hint_text = hint_font.render(hint, True, (180, 180, 180))
            self.screen.blit(hint_text, (box.x + 20, box.y + box.height - 60))

            esc_text = hint_font.render("ESC — закрыть", True, (180, 180, 180))
            self.screen.blit(esc_text, (box.x + 20, box.y + box.height - 30))

        # Памятка
        help_font = pygame.font.Font(None, 20)
        hint = help_font.render(
            "WASD/стрелки — движение | E — взаимодействие | I — инвентарь | F5 — сохранить | F9 — загрузить | ESC — меню",
            True, (180, 180, 180)
        )
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 15)))

    def _show_message(self, text):
        self.temp_message = text
        self.temp_message_timer = pygame.time.get_ticks()

    # -------------------------------------------------------------------------
    # ШАГ СУЩНОСТИ (игрок или NPC)
    # -------------------------------------------------------------------------
    def _move_entity_step(self, entity, is_player=False):
        current_time = pygame.time.get_ticks()
        delay = MOVE_DELAY_MS if is_player else entity.get("move_delay_ms", 1000)
        last_move = self.last_move_time if is_player else entity.get("last_move_time", 0)
        if current_time - last_move < delay:
            return
        if not is_player and entity.get("wait_until", 0) > current_time:
            return

        path = self.move_queue if is_player else entity.get("path", [])
        if not path:
            return

        next_x, next_y = path[0]
        curr_x = self.game_state.player["x"] if is_player else entity["x"]
        curr_y = self.game_state.player["y"] if is_player else entity["y"]

        # Двери
        tile_ahead = self.current_map.get_tile_type(next_x, next_y)
        if tile_ahead in (5, 6, 7, 8, 9):
            if self.current_map.open_door(next_x, next_y):
                self.current_map.reset_npcs_near_door(next_x, next_y)
                if not is_player:
                    entity["last_door_pos"] = (next_x, next_y)
                if is_player:
                    self.last_move_time = current_time
                else:
                    entity["last_move_time"] = current_time
                return

        def check_walkable(tx, ty):
            if is_player:
                return self.current_map.is_walkable(tx, ty)
            return self.current_map.is_walkable_for_npc(tx, ty, entity)

        blocked = not check_walkable(next_x, next_y)

        # Встречное движение
        if not is_player and blocked:
            other_npc = self.current_map.get_npc_at(next_x, next_y)
            if other_npc and other_npc.get("path") and other_npc["path"][0] == (curr_x, curr_y):
                if entity["id"] > other_npc["id"]:
                    log.info(f"ВСТРЕЧА: {entity['name']} уступает {other_npc['name']}")
                    entity["wait_until"] = current_time + 500
                    return

        if blocked:
            log.info(f"БЛОК: {entity.get('name', 'Игрок')} на ({curr_x},{curr_y})")
            if is_player:
                self.stuck_counter += 1
            else:
                entity["stuck_counter"] = entity.get("stuck_counter", 0) + 1
            current_stuck = self.stuck_counter if is_player else entity["stuck_counter"]
            if current_stuck > 2:
                log.info(f"ТУПИК: {entity.get('name', 'Игрок')}")
                if is_player:
                    self.move_queue = []
                    self.player_target = None
                    self.stuck_counter = 0
                else:
                    entity["path"] = []
                    entity["wait_until"] = current_time + 500
                    entity["stuck_counter"] = 0
                return

            dx = next_x - curr_x
            dy = next_y - curr_y
            right_x, right_y = curr_x - dy, curr_y + dx
            left_x, left_y = curr_x + dy, curr_y - dx
            back_x, back_y = curr_x - dx, curr_y - dy

            if check_walkable(right_x, right_y):
                next_x, next_y = right_x, right_y
                log.info(f"ОБХОД: {entity.get('name', 'Игрок')} ВПРАВО")
            elif check_walkable(left_x, left_y):
                next_x, next_y = left_x, left_y
                log.info(f"ОБХОД: {entity.get('name', 'Игрок')} ВЛЕВО")
            elif check_walkable(back_x, back_y):
                next_x, next_y = back_x, back_y
                log.info(f"ОБХОД: {entity.get('name', 'Игрок')} НАЗАД")
            else:
                log.info(f"ТУПИК: {entity.get('name', 'Игрок')} не может обойти")
                if is_player:
                    self.move_queue = []
                    self.player_target = None
                    self.stuck_counter = 0
                else:
                    entity["path"] = []
                    entity["wait_until"] = current_time + 500
                    entity["stuck_counter"] = 0
                return

            if is_player:
                self.move_queue = []
                if self.player_target:
                    from world.pathfinding import find_path
                    new_path = find_path(next_x, next_y, self.player_target[0], self.player_target[1], self.current_map.is_walkable)
                    if new_path:
                        self.move_queue = new_path
                    else:
                        self.player_target = None
                        self.stuck_counter = 0
            else:
                entity["path"] = []
                entity["last_move_time"] = current_time

        # Движение
        if check_walkable(next_x, next_y):
            if is_player:
                self.game_state.player["x"] = next_x
                self.game_state.player["y"] = next_y
                if self.move_queue:
                    self.move_queue.pop(0)
                self.last_move_time = current_time
                self.stuck_counter = 0
            else:
                log.info(f"ШАГ: NPC {entity['name']} ({entity['x']},{entity['y']}) -> ({next_x},{next_y})")
                entity["x"] = next_x
                entity["y"] = next_y
                if path and (next_x, next_y) == path[0]:
                    path.pop(0)
                    entity["stuck_counter"] = 0
                entity["last_move_time"] = current_time

                if entity.get("last_door_pos"):
                    ldx, ldy = entity["last_door_pos"]
                    if abs(entity["x"] - ldx) + abs(entity["y"] - ldy) >= 1:
                        self.current_map.close_door(ldx, ldy)
                        self.current_map.reset_npcs_near_door(ldx, ldy)
                        entity["last_door_pos"] = None

    def _find_approach_cell(self, obj_x, obj_y):
        """
        Находит клетку, к которой нужно подойти для взаимодействия с объектом в (obj_x, obj_y).
        Учитывает access_side у контейнеров.
        Возвращает (x, y) или None, если подойти некуда.
        """
        container = self.current_map.get_container_at(obj_x, obj_y)
        if container and container.access_side != "all":
            side = container.access_side
            # Клетки-кандидаты в зависимости от стороны
            candidates = []
            if side == "north":
                for dx in range(container.width):
                    candidates.append((container.x + dx, container.y - 1))
            elif side == "south":
                for dx in range(container.width):
                    candidates.append((container.x + dx, container.y + container.height))
            elif side == "west":
                for dy in range(container.height):
                    candidates.append((container.x - 1, container.y + dy))
            elif side == "east":
                for dy in range(container.height):
                    candidates.append((container.x + container.width, container.y + dy))
            # Ищем первую проходимую
            for cx, cy in candidates:
                if self.current_map.is_walkable(cx, cy):
                    return (cx, cy)
            return None

        # Для всех остальных объектов (NPC, дропы, двери, всесторонние контейнеры)
        # ищем любую соседнюю проходимую клетку
        px, py = self.game_state.player["x"], self.game_state.player["y"]
        best = None
        best_dist = 9999
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                cx, cy = obj_x + dx, obj_y + dy
                if self.current_map.is_walkable(cx, cy):
                    dist = abs(px - cx) + abs(py - cy)
                    if dist < best_dist:
                        best_dist = dist
                        best = (cx, cy)
        return best


    