# main.py
# =============================================================================
# ТОЧКА ВХОДА В ИГРУ И ГЛАВНЫЙ ИГРОВОЙ ЦИКЛ
# Инициализирует Pygame, загружает карту и NPC, обрабатывает ввод,
# управляет движением игрока и NPC, отрисовывает всё на экране.
# =============================================================================

import pygame
import sys
from settings import *
from game_state import GameState
from world.map import Map
from systems.dialog_system import DialogSystem

# -----------------------------------------------------------------------------
# ИНИЦИАЛИЗАЦИЯ PYGAME И ОКНА
# -----------------------------------------------------------------------------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Last Way — пре-альфа")
clock = pygame.time.Clock()                      # Для контроля FPS

# -----------------------------------------------------------------------------
# ЗАГРУЗКА СОСТОЯНИЯ, КАРТЫ И ДИАЛОГОВОЙ СИСТЕМЫ
# -----------------------------------------------------------------------------
game = GameState()
dialog_system = DialogSystem(game)
current_map = Map("001_map_hospital", game)      # Загружаем конкретную карту
player_x, player_y = current_map.player_start    # Начальная позиция с карты

game.player["x"] = player_x
game.player["y"] = player_y
game.player["class"] = "Идальго"                 # Временно, пока нет выбора класса

# -----------------------------------------------------------------------------
# ПЕРЕМЕННЫЕ ДЛЯ ДВИЖЕНИЯ ИГРОКА
# -----------------------------------------------------------------------------
last_move_time = 0
move_delay = MOVE_DELAY_MS                       # Задержка между шагами
facing_direction = (0, 1)                        # Куда смотрит игрок (0,1) — вниз

# -----------------------------------------------------------------------------
# ГЛАВНЫЙ ИГРОВОЙ ЦИКЛ
# -----------------------------------------------------------------------------
running = True
while running:
    current_time = pygame.time.get_ticks()       # Текущее время в миллисекундах
    clock.tick(60)                               # Ограничиваем 60 FPS

    # -------------------------------------------------------------------------
    # ОБРАБОТКА СОБЫТИЙ (клавиатура, закрытие окна)
    # -------------------------------------------------------------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            # --- ESCAPE: закрыть диалог или выйти из игры ---
            if event.key == pygame.K_ESCAPE:
                if game.dialog_active:
                    dialog_system.close_dialog()
                else:
                    running = False

            # -----------------------------------------------------------------
            # КЛАВИША E: взаимодействие
            # -----------------------------------------------------------------
            if event.key == pygame.K_e:
                if game.dialog_active:
                    # Если диалог активен и нет вариантов — закрываем
                    if not game.dialog_options:
                        dialog_system.close_dialog()
                        current_map.reset_all_npcs_timer()
                    continue

                # Если диалог не активен — пытаемся взаимодействовать с миром
                nx = player_x + facing_direction[0]
                ny = player_y + facing_direction[1]
                npc = current_map.get_npc_at(nx, ny)

                if npc:
                    # Перед NPC — начинаем диалог
                    dialog_system.load_dialog(npc["dialog_id"])
                else:
                    # Перед героем нет NPC — пробуем открыть/закрыть дверь
                    tile_type = current_map.get_tile_type(nx, ny)
                    if tile_type in (5, 6, 7, 8, 9):
                        current_map.open_door(nx, ny)
                        current_map.reset_npcs_near_door(nx, ny)
                    elif tile_type == 2:
                        current_map.close_door(nx, ny)
                        current_map.reset_npcs_near_door(nx, ny)
                        print(f"Дверь закрыта: {nx}, {ny}")

            # -----------------------------------------------------------------
            # ВЫБОР В ДИАЛОГЕ (цифры 1–4)
            # -----------------------------------------------------------------
            if game.dialog_active and game.dialog_options:
                if event.key == pygame.K_1:
                    dialog_system.choose_option(0)
                elif event.key == pygame.K_2:
                    dialog_system.choose_option(1)
                elif event.key == pygame.K_3:
                    dialog_system.choose_option(2)
                elif event.key == pygame.K_4:
                    dialog_system.choose_option(3)

    # -------------------------------------------------------------------------
    # ДВИЖЕНИЕ ИГРОКА (только если не в диалоге)
    # -------------------------------------------------------------------------
    if not game.dialog_active:
        keys = pygame.key.get_pressed()
        dx = dy = 0

        # Определяем направление по нажатым клавишам
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -1
            facing_direction = (-1, 0)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = 1
            facing_direction = (1, 0)
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -1
            facing_direction = (0, -1)
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = 1
            facing_direction = (0, 1)

        # Шаг с задержкой, чтобы герой не летал
        if (dx != 0 or dy != 0) and current_time - last_move_time >= move_delay:
            new_x = player_x + dx
            new_y = player_y + dy

            if current_map.is_walkable(new_x, new_y):
                player_x, player_y = new_x, new_y
                game.player["x"] = player_x
                game.player["y"] = player_y
                last_move_time = current_time

    # -------------------------------------------------------------------------
    # ОБНОВЛЕНИЕ ПОЗИЦИЙ NPC (только если не в диалоге)
    # -------------------------------------------------------------------------
    if not game.dialog_active:
        current_map.update_npcs(current_time, player_x, player_y)

    # -------------------------------------------------------------------------
    # ОТРИСОВКА ВСЕГО
    # -------------------------------------------------------------------------
    screen.fill(BLACK)
    current_map.render(screen, 0, 0)

    # --- Игрок (зелёный квадрат) ---
    player_rect = pygame.Rect(player_x * TILE_SIZE, player_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
    pygame.draw.rect(screen, GREEN, player_rect)

    # --- Линия направления игрока (желтая) ---
    cx = player_x * TILE_SIZE + TILE_SIZE // 2
    cy = player_y * TILE_SIZE + TILE_SIZE // 2
    end_x = cx + facing_direction[0] * 20
    end_y = cy + facing_direction[1] * 20
    pygame.draw.line(screen, YELLOW, (cx, cy), (end_x, end_y), 3)

    # --- Интерфейс (верхняя панель) ---
    font = pygame.font.Font(None, 24)
    info = font.render(
        f"Класс: {game.player['class']}  |  Дней: {game.days_left}  |  Человечность: {game.humanity}",
        True, WHITE
    )
    screen.blit(info, (10, 10))

    # Подсказки (меняются в зависимости от диалога)
    if not game.dialog_active:
        help_text = font.render("E — открыть дверь / говорить с NPC", True, WHITE)
        screen.blit(help_text, (10, 40))
    else:
        help_text = font.render("E/ESC — закрыть диалог", True, WHITE)
        screen.blit(help_text, (10, 40))

    # -------------------------------------------------------------------------
    # ДИАЛОГОВОЕ ОКНО (полупрозрачное, поверх всего)
    # -------------------------------------------------------------------------
    if game.dialog_active:
        surf = pygame.Surface((WIDTH - 100, 160))
        surf.set_alpha(220)
        surf.fill(BLACK)
        screen.blit(surf, (50, HEIGHT - 210))
        pygame.draw.rect(screen, WHITE, (50, HEIGHT - 210, WIDTH - 100, 160), 2)

        # Текст диалога (перенос строк)
        text_lines = game.dialog_text.split('\n')
        for i, line in enumerate(text_lines):
            if i * 25 < 100:
                rendered = font.render(line[:65], True, WHITE)
                screen.blit(rendered, (55, HEIGHT - 200 + i * 25))

        # Варианты ответов (зелёные)
        for i, opt in enumerate(game.dialog_options):
            opt_text = font.render(f"{i+1}. {opt['text']}", True, GREEN)
            screen.blit(opt_text, (55, HEIGHT - 110 + i * 25))

        # Если вариантов нет — подсказка закрыть диалог
        if not game.dialog_options:
            close_hint = font.render("Нажми E или ESC, чтобы продолжить", True, (150, 150, 150))
            screen.blit(close_hint, (55, HEIGHT - 60))

    # Обновляем экран
    pygame.display.flip()

# -----------------------------------------------------------------------------
# ЗАВЕРШЕНИЕ РАБОТЫ
# -----------------------------------------------------------------------------
pygame.quit()
sys.exit()