# game_engine.py
import pygame
import sys
from settings import *
from game_state import GameState
from world.map import Map
from systems.dialog_system import DialogSystem
from world.location_manager import LocationManager


class GameEngine:
    """Главный игровой движок. Управляет циклом, событиями, обновлением и отрисовкой."""

    def __init__(self, location_id: str, game_state: GameState = None):
        """
        Инициализация движка.

        Аргументы:
            map_id (str): ID локации для загрузки (например, "001_map_hospital")
            game_state (GameState, optional): Состояние игры. Если None, создаётся новое.
        """
        # Инициализация Pygame (если ещё не инициализирована)
        if not pygame.get_init():
            pygame.init()

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Last Way — пре-альфа")
        self.clock = pygame.time.Clock()

        # Состояние и системы
        self.game_state = game_state if game_state else GameState()

        self.location_manager = LocationManager()
        
        dialogs_dir = os.path.join(
            self.location_manager.get_location_path(location_id),
            "dialogs"
        )
        self.dialog_system = DialogSystem(self.game_state, dialogs_dir)

        
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
        """Обрабатывает все события клавиатуры и закрытия окна."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                self.exit_code = "exit"

            if event.type == pygame.KEYDOWN:
                # ESCAPE: закрыть диалог или выйти
                if event.key == pygame.K_ESCAPE:
                    if self.game_state.dialog_active:
                        self.dialog_system.close_dialog()
                        self.current_map.reset_all_npcs_timer()
                    else:
                        self.running = False
                        self.exit_code = "exit"

                # E: взаимодействие
                if event.key == pygame.K_e:
                    if self.game_state.dialog_active:
                        if not self.game_state.dialog_options:
                            self.dialog_system.close_dialog()
                            self.current_map.reset_all_npcs_timer()
                        continue

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

                # Цифры 1-4: выбор в диалоге
                if self.game_state.dialog_active and self.game_state.dialog_options:
                    if event.key == pygame.K_1:
                        self.dialog_system.choose_option(0)
                    elif event.key == pygame.K_2:
                        self.dialog_system.choose_option(1)
                    elif event.key == pygame.K_3:
                        self.dialog_system.choose_option(2)
                    elif event.key == pygame.K_4:
                        self.dialog_system.choose_option(3)

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