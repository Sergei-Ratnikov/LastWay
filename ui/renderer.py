# ui/renderer.py
# =============================================================================
# РЕНДЕРЕР ИНТЕРФЕЙСА
# Отвечает за отрисовку всех UI-элементов поверх карты.
# =============================================================================

import pygame
from settings import *
# FIX: для отображения имён предметов в инвентаре (а не item_id)
from world.item_data import ItemData


class Renderer:
    """
    Класс для отрисовки UI.
    Получает ссылку на GameEngine, чтобы иметь доступ ко всем нужным данным.
    """

    def __init__(self, game_engine):
        self.engine = game_engine
        # FIX: справочник предметов (singleton) для UI
        self.item_data = ItemData()

    # -------------------------------------------------------------------------
    # ОСНОВНОЙ МЕТОД ОТРИСОВКИ
    # -------------------------------------------------------------------------

    def render(self, screen):
        self._render_player(screen)
        self._render_hud(screen)
        self._render_dialog(screen)
        self._render_inventory(screen)
        self._render_temp_message(screen)
        self._render_save_menu(screen)
        self._render_hints(screen)

    # -------------------------------------------------------------------------
    # ИГРОК
    # -------------------------------------------------------------------------

    def _render_player(self, screen):
        """
        Отрисовка игрока: зелёный квадрат + жёлтая линия направления.
        FIX (#6): направление берётся из player.facing (единый источник).
        """
        game_state = self.engine.game_state
        px, py = game_state.player.x, game_state.player.y

        pygame.draw.rect(screen, GREEN, (px * TILE_SIZE, py * TILE_SIZE, TILE_SIZE, TILE_SIZE))

        cx = px * TILE_SIZE + TILE_SIZE // 2
        cy = py * TILE_SIZE + TILE_SIZE // 2
        dx, dy = game_state.player.get_facing_delta()
        ex = cx + dx * 20
        ey = cy + dy * 20
        pygame.draw.line(screen, YELLOW, (cx, cy), (ex, ey), 3)

    # -------------------------------------------------------------------------
    # HUD (ВЕРХНЯЯ ПАНЕЛЬ)
    # -------------------------------------------------------------------------

    def _render_hud(self, screen):
        game_state = self.engine.game_state
        font = pygame.font.Font(None, 24)

        info = font.render(
            f"Класс: {game_state.player.player_class}  |  "
            f"Дней: {game_state.days_left}  |  "
            f"Человечность: {game_state.humanity}",
            True, WHITE
        )
        screen.blit(info, (10, 10))

        if not game_state.dialog_active:
            help_text = font.render("E — открыть дверь / говорить с NPC", True, WHITE)
        else:
            help_text = font.render("E/ESC — закрыть диалог", True, WHITE)
        screen.blit(help_text, (10, 40))

    # -------------------------------------------------------------------------
    # ДИАЛОГ
    # -------------------------------------------------------------------------

    def _render_dialog(self, screen):
        game_state = self.engine.game_state
        if not game_state.dialog_active:
            return

        font = pygame.font.Font(None, 24)

        surf = pygame.Surface((WIDTH - 100, 160))
        surf.set_alpha(220)
        surf.fill(BLACK)
        screen.blit(surf, (50, HEIGHT - 210))
        pygame.draw.rect(screen, WHITE, (50, HEIGHT - 210, WIDTH - 100, 160), 2)

        for i, line in enumerate(game_state.dialog_text.split('\n')):
            if i * 25 < 100:
                screen.blit(font.render(line[:65], True, WHITE), (55, HEIGHT - 200 + i * 25))

        for i, opt in enumerate(game_state.dialog_options):
            screen.blit(font.render(f"{i+1}. {opt['text']}", True, GREEN), (55, HEIGHT - 110 + i * 25))

        if not game_state.dialog_options:
            hint = font.render("Нажми E или ESC, чтобы продолжить", True, (150, 150, 150))
            screen.blit(hint, (55, HEIGHT - 85))

    # -------------------------------------------------------------------------
    # ИНВЕНТАРЬ
    # -------------------------------------------------------------------------

    def _render_inventory(self, screen):
        """Отрисовка окна инвентаря."""
        if not self.engine.inventory_open:
            return

        surf = pygame.Surface((WIDTH - 200, HEIGHT - 200))
        surf.set_alpha(230)
        surf.fill(BLACK)
        screen.blit(surf, (100, 100))
        pygame.draw.rect(screen, WHITE, (100, 100, WIDTH - 200, HEIGHT - 200), 3)

        title_font = pygame.font.Font(None, 36)
        screen.blit(title_font.render("Инвентарь", True, YELLOW), (120, 120))

        item_font = pygame.font.Font(None, 24)
        items = self.engine.game_state.inventory.get_items()

        if not items:
            screen.blit(item_font.render("(пусто)", True, (150, 150, 150)), (120, 170))
        else:
            for i, item_id in enumerate(items):
                if i >= 15:
                    break
                # FIX: показываем человекочитаемое имя из items.json, а не item_id
                item_prop = self.item_data.get(item_id, {}) or {}
                item_name = item_prop.get("name", item_id)
                screen.blit(item_font.render(f"{i+1}. {item_name}", True, WHITE), (120, 170 + i * 30))

        # Показ текущего веса — полезно при разработке системы инвентаря
        inv = self.engine.game_state.inventory
        weight_text = f"Вес: {inv.get_total_weight():.1f} / {inv.max_weight:.1f} кг"
        screen.blit(item_font.render(weight_text, True, WHITE), (120, HEIGHT - 160))

        screen.blit(item_font.render("Нажми I, чтобы закрыть", True, (150, 150, 150)), (120, HEIGHT - 130))

    # -------------------------------------------------------------------------
    # ВРЕМЕННОЕ СООБЩЕНИЕ
    # -------------------------------------------------------------------------

    def _render_temp_message(self, screen):
        if not self.engine.temp_message:
            return

        current_time = pygame.time.get_ticks()
        if current_time - self.engine.temp_message_timer < 2000:
            font = pygame.font.Font(None, 28)
            text_surf = font.render(self.engine.temp_message, True, WHITE)
            text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT - 100))
            bg_rect = text_rect.inflate(20, 10)

            pygame.draw.rect(screen, BLACK, bg_rect)
            pygame.draw.rect(screen, WHITE, bg_rect, 2)
            screen.blit(text_surf, text_rect)
        else:
            self.engine.temp_message = None

    # -------------------------------------------------------------------------
    # МЕНЮ СОХРАНЕНИЙ
    # -------------------------------------------------------------------------

    def _render_save_menu(self, screen):
        if not self.engine.save_menu_open:
            return

        surf = pygame.Surface((WIDTH, HEIGHT))
        surf.set_alpha(180)
        surf.fill(BLACK)
        screen.blit(surf, (0, 0))

        box = pygame.Rect(WIDTH // 2 - 250, 100, 500, 450)
        pygame.draw.rect(screen, BLACK, box)
        pygame.draw.rect(screen, WHITE, box, 3)

        title_font = pygame.font.Font(None, 36)
        item_font = pygame.font.Font(None, 26)
        hint_font = pygame.font.Font(None, 20)

        title_text = "Сохранить игру" if self.engine.save_menu_mode == "save" else "Загрузить игру"
        title = title_font.render(title_text, True, YELLOW)
        screen.blit(title, (box.x + 20, box.y + 20))

        y = box.y + 80
        if not self.engine.save_menu_items:
            empty = item_font.render("(нет сохранений)", True, (150, 150, 150))
            screen.blit(empty, (box.x + 20, y))
        else:
            for i, name in enumerate(self.engine.save_menu_items):
                color = GREEN if i == self.engine.save_menu_selected else WHITE
                marker = "> " if i == self.engine.save_menu_selected else "  "
                text = item_font.render(marker + name, True, color)
                screen.blit(text, (box.x + 20, y + i * 30))

        if self.engine.save_menu_mode == "save":
            hint = "Enter — создать новое сохранение (автономер)"
        else:
            hint = "Enter — загрузить выбранное"
        hint_text = hint_font.render(hint, True, (180, 180, 180))
        screen.blit(hint_text, (box.x + 20, box.y + box.height - 60))

        esc_text = hint_font.render("ESC — закрыть", True, (180, 180, 180))
        screen.blit(esc_text, (box.x + 20, box.y + box.height - 30))

    # -------------------------------------------------------------------------
    # ПОДСКАЗКИ УПРАВЛЕНИЯ
    # -------------------------------------------------------------------------

    def _render_hints(self, screen):
        help_font = pygame.font.Font(None, 20)
        hint = help_font.render(
            "WASD/стрелки — движение | E — взаимодействие | I — инвентарь | "
            "F5 — сохранить | F9 — загрузить | ESC — меню",
            True, (180, 180, 180)
        )
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 15)))