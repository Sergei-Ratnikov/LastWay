# main.py
import pygame
import sys
from settings import *
from game_state import GameState
from world.map import Map
from systems.dialog_system import DialogSystem

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Last Way — пре-альфа")
clock = pygame.time.Clock()

game = GameState()
dialog_system = DialogSystem(game)
current_map = Map("001_map_hospital", game)
player_x, player_y = current_map.player_start

game.player["x"] = player_x
game.player["y"] = player_y
game.player["class"] = "Идальго"

last_move_time = 0
move_delay = MOVE_DELAY_MS
facing_direction = (0, 1)

running = True
while running:
    current_time = pygame.time.get_ticks()
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if game.dialog_active:
                    dialog_system.close_dialog()
                else:
                    running = False

            # --- Взаимодействие по E ---
            if event.key == pygame.K_e:
                if game.dialog_active:
                    # Если диалог активен и нет вариантов — закрываем
                    if not game.dialog_options:
                        dialog_system.close_dialog()
                    continue

                # Если диалог не активен — пытаемся взаимодействовать с миром
                nx = player_x + facing_direction[0]
                ny = player_y + facing_direction[1]
                npc = current_map.get_npc_at(nx, ny)

                if npc:
                    dialog_system.load_dialog(npc["dialog_id"])
                else:
                    tile_type = current_map.get_tile_type(nx, ny)
                    if tile_type in (5, 6, 7, 8, 9):
                        current_map.open_door(nx, ny)
                        current_map.reset_npcs_near_door(nx, ny)
                        print(f"Дверь открыта: {nx}, {ny}")
                    elif tile_type == 2:
                        current_map.close_door(nx, ny)
                        current_map.reset_npcs_near_door(nx, ny)
                        print(f"Дверь закрыта: {nx}, {ny}")

            # --- Обработка выбора в диалоге (цифры 1-4) ---
            if game.dialog_active and game.dialog_options:
                if event.key == pygame.K_1:
                    dialog_system.choose_option(0)
                elif event.key == pygame.K_2:
                    dialog_system.choose_option(1)
                elif event.key == pygame.K_3:
                    dialog_system.choose_option(2)
                elif event.key == pygame.K_4:
                    dialog_system.choose_option(3)

    # --- Движение игрока (только если не в диалоге) ---
    if not game.dialog_active:
        keys = pygame.key.get_pressed()
        dx = dy = 0
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

        if (dx != 0 or dy != 0) and current_time - last_move_time >= move_delay:
            new_x = player_x + dx
            new_y = player_y + dy

            if current_map.is_walkable(new_x, new_y):
                player_x, player_y = new_x, new_y
                game.player["x"] = player_x
                game.player["y"] = player_y
                last_move_time = current_time

    # --- Обновление движения NPC ---
    if not game.dialog_active:
        current_map.update_npcs(current_time, player_x, player_y)

    # --- Отрисовка ---
    screen.fill(BLACK)
    current_map.render(screen, 0, 0)

    # Рисуем игрока (только если не в диалоге, чтобы окно его не перекрывало)
    if not game.dialog_active:
        player_rect = pygame.Rect(player_x * TILE_SIZE, player_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        pygame.draw.rect(screen, GREEN, player_rect)

    # --- Интерфейс ---
    font = pygame.font.Font(None, 24)
    info = font.render(f"Класс: {game.player['class']}  |  Дней: {game.days_left}  |  Человечность: {game.humanity}", True, WHITE)
    screen.blit(info, (10, 10))

    if not game.dialog_active:
        help_text = font.render("E — открыть дверь / говорить с NPC", True, WHITE)
        screen.blit(help_text, (10, 40))
    else:
        help_text = font.render("E/ESC — закрыть диалог", True, WHITE)
        screen.blit(help_text, (10, 40))

    # --- Диалоговое окно ---
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

        # Варианты ответов
        for i, opt in enumerate(game.dialog_options):
            opt_text = font.render(f"{i+1}. {opt['text']}", True, GREEN)
            screen.blit(opt_text, (55, HEIGHT - 110 + i * 25))

        # Если нет вариантов, показываем подсказку закрыть
        if not game.dialog_options:
            close_hint = font.render("Нажми E или ESC, чтобы продолжить", True, (150, 150, 150))
            screen.blit(close_hint, (55, HEIGHT - 60))

    pygame.display.flip()

pygame.quit()
sys.exit()