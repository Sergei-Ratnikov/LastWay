# game_engine.py
import pygame
import sys
from settings import *
from game_state import GameState
from world.map import Map
from systems.dialog_system import DialogSystem
from world.location_manager import LocationManager
from input_handler import InputHandler

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
        """
        Обрабатывает команды от InputHandler
        """
        
        print(f"DEBUG game_engine.py: получена команда {command}")

        if isinstance(command, tuple):
            cmd_type = command[0]

            if cmd_type == "dialog_choice":
                choice_index = command[1]
                self.dialog_system.choose_option(choice_index)            
            elif cmd_type == "interact_npc":
                dialog_id = command[1]
                self.dialog_system.load_dialog(dialog_id)
            elif cmd_type == "interact_door":
                door_x, door_y = command[1]
                tile_type = self.current_map.get_tile_type(door_x, door_y)
                if tile_type in (5, 6, 7, 8, 9):
                    self.current_map.open_door(door_x, door_y)
                    self.current_map.reset_npcs_near_door(door_x, door_y)
                elif tile_type == 2:
                    self.current_map.close_door(door_x, door_y)
                    self.current_map.reset_npcs_near_door(door_x, door_y)
            elif cmd_type == "interact_container":
                container_id = command[1]
                # Находим контейнер
                for container in self.current_map.containers:
                    if container.id == container_id:
                        if container.locked:
                            self._show_message("Контейнер заперт")
                        elif not container.is_open:
                            container.open()
                            self._show_message(f"Ты открыл {container.name}. Внутри: {', '.join(container.items) if container.items else 'пусто'}")
                        else:
                            self._show_message(f"{container.name} уже открыт")
                        break
            elif cmd_type == "move_to":
                target_x, target_y = command[1]
                # Пока просто шаг, если цель — соседняя клетка
                dx = target_x - self.game_state.player["x"]
                dy = target_y - self.game_state.player["y"]
                if abs(dx) + abs(dy) == 1:
                    new_x = self.game_state.player["x"] + dx
                    new_y = self.game_state.player["y"] + dy
                    if self.current_map.is_walkable(new_x, new_y):
                        self.game_state.player["x"] = new_x
                        self.game_state.player["y"] = new_y
            elif cmd_type == "interact_container":
                container_id = command[1]
                for container in self.current_map.containers:
                    if container.id == container_id:
                        if container.locked:
                            self._show_message("Контейнер заперт")
                        elif not container.is_open:
                            container.open()
                            items_text = ', '.join(container.items) if container.items else "пусто"
                            self._show_message(f"Ты открыл {container.name}. Внутри: {items_text}")
                        else:
                            self._show_message(f"{container.name} уже открыт")
                        break

        else:
            if command == "interact":
                self._interact()
            elif command == "menu":
                if self.game_state.dialog_active:
                    self.dialog_system.close_dialog()
                else:
                    self.running = False
            elif command == "open_inventory":
                # TODO: открыть инвентарь
                pass
            elif command == "context_menu":
                # TODO: контекстное меню
                pass

    def _interact(self):
        """Взаимодействие с тем, что перед игроком."""
        nx = self.game_state.player["x"] + self.facing_direction[0]
        ny = self.game_state.player["y"] + self.facing_direction[1]
        npc = self.current_map.get_npc_at(nx, ny)
        
        if npc:
            self.dialog_system.load_dialog(npc["dialog_id"])
        else:
            tile_type = self.current_map.get_tile_type(nx, ny)
            if tile_type in (5, 6, 7, 8, 9):
                self.current_map.open_door(nx, ny)
                self.current_map.reset_npcs_near_door(nx, ny)
            elif tile_type == 2:
                self.current_map.close_door(nx, ny)
                self.current_map.reset_npcs_near_door(nx, ny)

    # -------------------------------------------------------------------------
    # ОБНОВЛЕНИЕ (логика)
    # -------------------------------------------------------------------------
    def update(self, current_time: int):
        """Обновляет движение игрока и NPC (только если не в диалоге)."""
        if self.game_state.dialog_active:
            return

        # ----- Движение игрока -----
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

        # ----- Движение NPC -----
        self.current_map.update_npcs(current_time, self.game_state.player["x"], self.game_state.player["y"])

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
                self.screen.blit(close_hint, (55, HEIGHT - 60))

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