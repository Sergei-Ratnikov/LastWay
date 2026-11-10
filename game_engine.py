# game_engine.py
import random

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
        """
        Инициализация движка.

        Аргументы:
            map_id (str): ID локации для загрузки (например, "001_map_hospital")
            game_state (GameState, optional): Состояние игры. Если None, создаётся новое.
        """

        self.temp_message = None
        self.temp_message_timer = 0

        # Инициализация Pygame (если ещё не инициализирована)
        if not pygame.get_init():
            pygame.init()

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Last Way — пре-альфа")
        self.clock = pygame.time.Clock()

        # Состояние и системы
        self.game_state = game_state if game_state else GameState()
        self.location_manager = LocationManager()
        self.current_map = Map(location_id, self.game_state, self.location_manager)

        # Определяем путь к папке диалогов текущей локации
        dialogs_path = os.path.join(
            self.location_manager.get_location_path(location_id),
            "dialogs"
        )
        self.dialog_system = DialogSystem(self.game_state, dialogs_path)

        # Позиция игрока из карты
        player_x, player_y = self.current_map.player_start
        self.game_state.player["x"] = player_x
        self.game_state.player["y"] = player_y
        # Временно, пока нет выбора класса
        if not self.game_state.player["class"]:
            self.game_state.player["class"] = "Идальго"

        self.move_queue = []  # очередь клеток для автоматического движения игрока
        self.player_target = None  # <--- Куда игрок хочет прийти (конечная точка клика)
        
        # Обработчик ввода
        self.input_handler = InputHandler()

        # Переменные движения
        self.last_move_time = 0
        self.facing_direction = (0, 1)  # куда смотрит игрок (0,1) — вниз

        # Флаг работы цикла
        self.running = True
        self.exit_code = None  # "next_location", "exit"

    # -------------------------------------------------------------------------
    # ОСНОВНОЙ ЦИКЛ
    # -------------------------------------------------------------------------
    def run(self) -> str:
        """
        Запускает главный игровой цикл.

        Возвращает:
            str: "exit" — выход из игры, "next_location": <id> — переход на другую локацию
        """
        while self.running:
            current_time = pygame.time.get_ticks()
            self.clock.tick(60)

            self.handle_events()
            self.update(current_time)
            self.render()

            pygame.display.flip()

        return self.exit_code or "exit"

    # -------------------------------------------------------------------------
    # ОБРАБОТКА СОБЫТИЙ
    # -------------------------------------------------------------------------

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                self.exit_code = "exit"
            
            command = self.input_handler.handle_event(event, self.game_state, self.current_map)
            if command:
                self._process_command(command)

    def _process_command(self, command):
        log.info(f"Получена команда {command}")
        if isinstance(command, tuple):
            cmd_type = command[0]

            if cmd_type == "dialog_choice":
                choice_index = command[1]
                self.dialog_system.choose_option(choice_index)
            elif cmd_type == "interact":
                _, target_x, target_y = command
                self._handle_interaction(target_x, target_y)

            elif cmd_type == "move_to":
                _, target_x, target_y = command
                from world.pathfinding import find_path
                if not self.current_map.is_walkable(target_x, target_y):
                    return
                
                self.player_target = (target_x, target_y)  # <--- ЗАПОМИНАЕМ ЦЕЛЬ
                
                path = find_path(
                    self.game_state.player["x"],
                    self.game_state.player["y"],
                    target_x,
                    target_y,
                    self.current_map.is_walkable
                )
                if path:
                    self.move_queue = path

            elif cmd_type == "interact":
                _, target_x, target_y = command
                self._handle_interaction(target_x, target_y) # Проверка будет внутри


        else:
            if command == "interact":
                self._interact()
            elif command == "menu":
                if self.game_state.dialog_active:
                    self.dialog_system.close_dialog()
                else:
                    self.running = False
            elif command == "open_inventory":
                pass
            elif command == "context_menu":
                pass

    def _interact(self):
        nx = self.game_state.player["x"] + self.facing_direction[0]
        ny = self.game_state.player["y"] + self.facing_direction[1]
        if not self._is_in_range(nx, ny):
            self._show_message("Слишком далеко")
            return
        self._handle_interaction(nx, ny)
    
    def _handle_interaction(self, x, y):
        """
        Единый метод взаимодействия с объектом в клетке (x, y).
        Используется и для клавиши E, и для клика мышью.
        """

        # Проверка дистанции
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
            if container.locked:
                self._show_message("Контейнер заперт")
            elif not container.is_open:
                container.open()
                items_text = ', '.join(container.items) if container.items else "пусто"
                self._show_message(f"Ты открыл {container.name}. Внутри: {items_text}")
            else:
                self._show_message(f"{container.name} уже открыт")
            return

        # 3. Дроп
        drop = self.current_map.get_drop_at(x, y)
        if drop:
            items_text = ', '.join(drop.items) if drop.items else "пусто"
            self._show_message(f"На земле: {items_text}")
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
        """Проверяет, находится ли цель в радиусе взаимодействия от игрока."""
        if radius is None:
            radius = INTERACT_RADIUS
        px = self.game_state.player["x"]
        py = self.game_state.player["y"]
        distance = abs(px - target_x) + abs(py - target_y)
        return distance <= radius

    # -------------------------------------------------------------------------
    # ОБНОВЛЕНИЕ (логика)
    # -------------------------------------------------------------------------
    def update(self, current_time: int):
        """Обновляет движение игрока и NPC."""
        if self.game_state.dialog_active:
            return

        # ----- 1. Автоматическое движение игрока по пути (BFS) -----
        if self.move_queue:
            self._move_entity_step(self.game_state.player, is_player=True)
            
        # ----- 2. Ручное движение игрока (WASD) -----
        else:
            keys = pygame.key.get_pressed()
            dx = dy = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
                self.facing_direction = (-1, 0)
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1
                self.facing_direction = (1, 0)
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1
                self.facing_direction = (0, -1)
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1
                self.facing_direction = (0, 1)

            if (dx != 0 or dy != 0) and current_time - self.last_move_time >= MOVE_DELAY_MS:
                new_x = self.game_state.player["x"] + dx
                new_y = self.game_state.player["y"] + dy
                if self.current_map.is_walkable(new_x, new_y):
                    self.game_state.player["x"] = new_x
                    self.game_state.player["y"] = new_y
                    self.last_move_time = current_time

        # обработка точки перехода в другую локацию
        exit_point = self.current_map.get_exit_at(self.game_state.player["x"], self.game_state.player["y"])
        if exit_point:
            self.switch_location(exit_point["target_location"], exit_point["target_exit_id"])
            return

        # ----- 3. Движение NPC -----
        for npc in self.current_map.npcs:
            if npc["movement"] == "stationary": 
                continue

            # Если NPC ждет после застревания
            if npc.get("wait_until", 0) > current_time:
                continue


            # --- ЛОГИКА СЛЕДОВАНИЯ ---
            if npc["movement"] == "follow" and npc.get("follow_target"):
                # Ищем цель, за которой следуем
                target_npc = None
                for other in self.current_map.npcs:
                    if other["id"] == npc["follow_target"]:
                        target_npc = other
                        break
                
                if target_npc:
                    # Если мы уже рядом с целью (на соседней клетке), не дергаемся
                    if abs(npc["x"] - target_npc["x"]) + abs(npc["y"] - target_npc["y"]) <= 1:
                        npc["path"] = []
                        npc["last_move_time"] = current_time
                        continue
                    
                    # Если пути нет или цель сдвинулась, строим новый путь
                    if not npc.get("path"):
                        from world.pathfinding import find_path
                        path = find_path(npc["x"], npc["y"], target_npc["x"], target_npc["y"], self.current_map.is_walkable_static)
                        if path:
                            npc["path"] = path
                        else:
                            npc["last_move_time"] = current_time
                    
                    self._move_entity_step(npc, is_player=False)
                    continue  # Пропускаем логику патрулирования



            # ЛОГИКА ПАТРУЛИРОВАНИЯ
            # Если NPC достиг текущей цели — переключаем индекс
            if npc.get("patrol_points"):
                target = npc["patrol_points"][npc.get("patrol_index", 0)]
                
                # Извлекаем координаты цели (они могут быть списком или словарём)
                if isinstance(target, list):
                    tx, ty = target[0], target[1]
                else:
                    tx, ty = target.get("pos", [npc["x"], npc["y"]])[0], target.get("pos", [npc["x"], npc["y"]])[1]
                
                # Если мы УЖЕ на цели — переключаем индекс
                if (npc["x"], npc["y"]) == (tx, ty):
                    npc["patrol_index"] = (npc.get("patrol_index", 0) + 1) % len(npc["patrol_points"])
                    npc["last_move_time"] = current_time  # Сброс таймера, чтобы не бежал сразу
                    log.info(f"NPC {npc['name']} достиг цели, переход к индексу {npc['patrol_index']}")
                    continue # Пропускаем этот кадр, на следующем построит путь к новой цели

            # Если пути нет — строим заново
            if not npc.get("path") and npc.get("patrol_points"):
                # Если NPC ждет после застревания — не строим путь прямо сейчас
                if npc.get("wait_until", 0) > current_time:
                    continue
                target = npc["patrol_points"][npc.get("patrol_index", 0)]
                if isinstance(target, list):
                    tx, ty = target[0], target[1]
                else:
                    tx, ty = target.get("pos", [npc["x"], npc["y"]])[0], target.get("pos", [npc["x"], npc["y"]])[1]
                    
                from world.pathfinding import find_path
                # BFS ищет путь, игнорируя NPC и двери (is_walkable_static)
                path = find_path(npc["x"], npc["y"], tx, ty, self.current_map.is_walkable_static)
                log.info(f"PATH: NPC {npc['name']} на ({npc['x']},{npc['y']}). Цель: ({tx},{ty}). Путь: {path}")
                if path:
                    npc["path"] = path
                else:
                    npc["last_move_time"] = current_time

            # Делаем шаг
            self._move_entity_step(npc, is_player=False)



        # ----- 4. Обновление кошек -----
        self.current_map.update_cats(current_time)

    # -------------------------------------------------------------------------
    # ПЕРЕХОД МЕЖДУ ЛОКАЦИЯМИ
    # -------------------------------------------------------------------------
    def switch_location(self, target_location_id, target_exit_id):
        # Сохраняем состояние текущей локации (если нужно)
        # Загружаем новую локацию
        self.current_map = Map(target_location_id, self.game_state, self.location_manager)
        
        # Находим выход, на который нужно поставить игрока
        for exit_data in self.current_map.exits:
            if exit_data.get("id") == target_exit_id:
                self.game_state.player["x"] = exit_data["spawn_x"]
                self.game_state.player["y"] = exit_data["spawn_y"]
                break
        
        # Сбрасываем таймер движения
        self.last_move_time = pygame.time.get_ticks()
        self.move_queue = []
    # -------------------------------------------------------------------------
    # ОТРИСОВКА
    # -------------------------------------------------------------------------
    def render(self):
        """Отрисовка карты, игрока, интерфейса и диалогового окна."""
        self.screen.fill(BLACK)
        self.current_map.render(self.screen, 0, 0)

        # Игрок
        px = self.game_state.player["x"]
        py = self.game_state.player["y"]
        player_rect = pygame.Rect(px * TILE_SIZE, py * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        pygame.draw.rect(self.screen, GREEN, player_rect)

        # Линия направления игрока
        cx = px * TILE_SIZE + TILE_SIZE // 2
        cy = py * TILE_SIZE + TILE_SIZE // 2
        end_x = cx + self.facing_direction[0] * 20
        end_y = cy + self.facing_direction[1] * 20
        pygame.draw.line(self.screen, YELLOW, (cx, cy), (end_x, end_y), 3)

        # Интерфейс (верхняя панель)
        font = pygame.font.Font(None, 24)
        info = font.render(
            f"Класс: {self.game_state.player['class']}  |  Дней: {self.game_state.days_left}  |  Человечность: {self.game_state.humanity}",
            True, WHITE
        )
        self.screen.blit(info, (10, 10))

        if not self.game_state.dialog_active:
            help_text = font.render("E — открыть дверь / говорить с NPC", True, WHITE)
            self.screen.blit(help_text, (10, 40))
        else:
            help_text = font.render("E/ESC — закрыть диалог", True, WHITE)
            self.screen.blit(help_text, (10, 40))

        # Диалоговое окно
        if self.game_state.dialog_active:
            surf = pygame.Surface((WIDTH - 100, 160))
            surf.set_alpha(220)
            surf.fill(BLACK)
            self.screen.blit(surf, (50, HEIGHT - 210))
            pygame.draw.rect(self.screen, WHITE, (50, HEIGHT - 210, WIDTH - 100, 160), 2)

            text_lines = self.game_state.dialog_text.split('\n')
            for i, line in enumerate(text_lines):
                if i * 25 < 100:
                    rendered = font.render(line[:65], True, WHITE)
                    self.screen.blit(rendered, (55, HEIGHT - 200 + i * 25))

            for i, opt in enumerate(self.game_state.dialog_options):
                opt_text = font.render(f"{i+1}. {opt['text']}", True, GREEN)
                self.screen.blit(opt_text, (55, HEIGHT - 110 + i * 25))

            if not self.game_state.dialog_options:
                close_hint = font.render("Нажми E или ESC, чтобы продолжить", True, (150, 150, 150))
                self.screen.blit(close_hint, (55, HEIGHT - 85))

        # Временное сообщение (например, от контейнера)
        if self.temp_message:
            current_time = pygame.time.get_ticks()
            if current_time - self.temp_message_timer < 2000:  # показываем 2 секунды
                font = pygame.font.Font(None, 28)
                text_surf = font.render(self.temp_message, True, WHITE)
                text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT - 100))
                
                # Фон под сообщением
                bg_rect = text_rect.inflate(20, 10)
                pygame.draw.rect(self.screen, BLACK, bg_rect)
                pygame.draw.rect(self.screen, WHITE, bg_rect, 2)
                
                self.screen.blit(text_surf, text_rect)
            else:
                self.temp_message = None

    def _show_message(self, text):
        """Показывает временное сообщение (например, при открытии контейнера)."""
        self.temp_message = text
        self.temp_message_timer = pygame.time.get_ticks()

    def _move_entity_step(self, entity, is_player=False):
        """Универсальный шаг для игрока или NPC с обходом препятствий."""
        current_time = pygame.time.get_ticks()

        # Задержка движения
        delay = MOVE_DELAY_MS if is_player else entity.get("move_delay_ms", 1000)
        last_move = self.last_move_time if is_player else entity.get("last_move_time", 0)
        if current_time - last_move < delay:
            return

        # Пауза (если NPC застрял)
        if not is_player and entity.get("wait_until", 0) > current_time:
            return

        path = self.move_queue if is_player else entity.get("path", [])
        if not path:
            return

        next_x, next_y = path[0]
        curr_x = self.game_state.player["x"] if is_player else entity["x"]
        curr_y = self.game_state.player["y"] if is_player else entity["y"]

        # 1. Проверка на закрытую дверь
        tile_ahead = self.current_map.get_tile_type(next_x, next_y)
        if tile_ahead in (5, 6, 7, 8, 9):  # Только ЗАКРЫТЫЕ двери
            if self.current_map.open_door(next_x, next_y):
                self.current_map.reset_npcs_near_door(next_x, next_y)
                if not is_player:
                    entity["last_door_pos"] = (next_x, next_y)
                if is_player: self.last_move_time = current_time
                else: entity["last_move_time"] = current_time
                return

        # 2. Проверка на препятствия (игрок или другой NPC)
        def check_walkable(tx, ty):
            if is_player:
                return self.current_map.is_walkable(tx, ty)
            else:
                return self.current_map.is_walkable_for_npc(tx, ty, entity)

        blocked = not check_walkable(next_x, next_y)

        if blocked:
            log.info(f"БЛОК: {entity.get('name', 'Игрок')} на ({curr_x},{curr_y}) уперся. Цель: ({next_x},{next_y})")
            
            # Вычисляем векторы направления
            dx = next_x - curr_x
            dy = next_y - curr_y
            
            # Варианты обхода: Вправо, Влево, Назад
            right_x, right_y = curr_x - dy, curr_y + dx
            left_x, left_y = curr_x + dy, curr_y - dx
            back_x, back_y = curr_x - dx, curr_y - dy

            # Пробуем шагнуть в сторону
            if check_walkable(right_x, right_y):
                next_x, next_y = right_x, right_y
                log.info(f"ОБХОД: {entity.get('name', 'Игрок')} шагает ВПРАВО в ({next_x},{next_y})")
            elif check_walkable(left_x, left_y):
                next_x, next_y = left_x, left_y
                log.info(f"ОБХОД: {entity.get('name', 'Игрок')} шагает ВЛЕВО в ({next_x},{next_y})")
            elif check_walkable(back_x, back_y):
                next_x, next_y = back_x, back_y
                log.info(f"ОБХОД: {entity.get('name', 'Игрок')} шагает НАЗАД в ({next_x},{next_y})")
            else:
                log.info(f"ТУПИК: {entity.get('name', 'Игрок')} не может обойти.")
                if is_player:
                    self.move_queue = []
                    self.player_target = None
                else:
                    entity["path"] = []
                    entity["wait_until"] = current_time + 500
                return
                
            # Если шагнули в сторону, сбрасываем путь и строим новый (для игрока)
            if is_player:
                self.move_queue = []
                if self.player_target:
                    from world.pathfinding import find_path
                    path = find_path(next_x, next_y, self.player_target[0], self.player_target[1], self.current_map.is_walkable)
                    if path:
                        self.move_queue = path
                    else:
                        self.player_target = None
            else:
                entity["path"] = []
                entity["last_move_time"] = current_time
       
        # 3. Движение
        if check_walkable(next_x, next_y):
            if is_player:
                self.game_state.player["x"] = next_x
                self.game_state.player["y"] = next_y
                if self.move_queue:
                    self.move_queue.pop(0)
                self.last_move_time = current_time
            else:
                log.info(f"ШАГ: NPC {entity['name']} идет из ({entity['x']},{entity['y']}) в ({next_x},{next_y})")
                entity["x"] = next_x
                entity["y"] = next_y
                
                # Если шаг был в сторону (обход), НЕ удаляем клетку из пути!
                if path and (next_x, next_y) == path[0]:
                    path.pop(0)
                
                entity["last_move_time"] = current_time

                # Закрытие двери
                if entity.get("last_door_pos"):
                    ldx, ldy = entity["last_door_pos"]
                    if abs(entity["x"] - ldx) + abs(entity["y"] - ldy) >= 1:
                        self.current_map.close_door(ldx, ldy)
                        self.current_map.reset_npcs_near_door(ldx, ldy)
                        entity["last_door_pos"] = None