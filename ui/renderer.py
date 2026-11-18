# ui/renderer.py
# =============================================================================
# РЕНДЕРЕР ИНТЕРФЕЙСА
# Отвечает за отрисовку всех UI-элементов поверх карты:
# - игрок (спрайт + линия направления)
# - HUD (класс, дни, человечность)
# - диалоговое окно
# - окно инвентаря
# - временные сообщения
# - меню сохранений
# - подсказки управления
# =============================================================================

import pygame
from settings import *


class Renderer:
    """
    Класс для отрисовки UI.
    Получает ссылку на GameEngine, чтобы иметь доступ ко всем нужным данным
    (game_state, current_map, temp_message, inventory_open и т.д.).
    """
    
    def __init__(self, game_engine):
        """
        Инициализация рендерера.
        
        Аргументы:
            game_engine: Ссылка на GameEngine (источник всех данных для отрисовки).
        """
        self.engine = game_engine
    
    # -------------------------------------------------------------------------
    # ОСНОВНОЙ МЕТОД ОТРИСОВКИ
    # -------------------------------------------------------------------------
    
    def render(self, screen):
        """
        Главный метод отрисовки. Вызывается из GameEngine.render().
        Отрисовывает все UI-элементы поверх уже отрисованной карты.
        
        Аргументы:
            screen: Pygame-поверхность для отрисовки.
        """
        # Порядок важен: сначала фон, потом элементы снизу вверх
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
        """Отрисовка игрока: зелёный квадрат + жёлтая линия направления."""
        game_state = self.engine.game_state
        px, py = game_state.player.x, game_state.player.y
        
        # Зелёный квадрат игрока
        pygame.draw.rect(screen, GREEN, (px * TILE_SIZE, py * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        
        # Линия направления (куда смотрит игрок)
        cx = px * TILE_SIZE + TILE_SIZE // 2
        cy = py * TILE_SIZE + TILE_SIZE // 2
        dx, dy = self.engine.facing_direction
        ex = cx + dx * 20
        ey = cy + dy * 20
        pygame.draw.line(screen, YELLOW, (cx, cy), (ex, ey), 3)
    
    # -------------------------------------------------------------------------
    # HUD (ВЕРХНЯЯ ПАНЕЛЬ)
    # -------------------------------------------------------------------------
    
    def _render_hud(self, screen):
        """Отрисовка верхней панели: класс, дни, человечность, подсказка."""
        game_state = self.engine.game_state
        font = pygame.font.Font(None, 24)
        
        # Основная информация
        info = font.render(
            f"Класс: {game_state.player.player_class}  |  "
            f"Дней: {game_state.days_left}  |  "
            f"Человечность: {game_state.humanity}",
            True, WHITE
        )
        screen.blit(info, (10, 10))
        
        # Подсказка по E
        if not game_state.dialog_active:
            help_text = font.render("E — открыть дверь / говорить с NPC", True, WHITE)
        else:
            help_text = font.render("E/ESC — закрыть диалог", True, WHITE)
        screen.blit(help_text, (10, 40))
    
    # -------------------------------------------------------------------------
    # ДИАЛОГ
    # -------------------------------------------------------------------------
    
    def _render_dialog(self, screen):
        """Отрисовка диалогового окна (если диалог активен)."""
        game_state = self.engine.game_state
        if not game_state.dialog_active:
            return
        
        font = pygame.font.Font(None, 24)
        
        # Полупрозрачный фон
        surf = pygame.Surface((WIDTH - 100, 160))
        surf.set_alpha(220)
        surf.fill(BLACK)
        screen.blit(surf, (50, HEIGHT - 210))
        pygame.draw.rect(screen, WHITE, (50, HEIGHT - 210, WIDTH - 100, 160), 2)
        
        # Текст диалога (с переносом строк)
        for i, line in enumerate(game_state.dialog_text.split('\n')):
            if i * 25 < 100:
                screen.blit(font.render(line[:65], True, WHITE), (55, HEIGHT - 200 + i * 25))
        
        # Варианты ответов
        for i, opt in enumerate(game_state.dialog_options):
            screen.blit(font.render(f"{i+1}. {opt['text']}", True, GREEN), (55, HEIGHT - 110 + i * 25))
        
        # Подсказка, если вариантов нет
        if not game_state.dialog_options:
            hint = font.render("Нажми E или ESC, чтобы продолжить", True, (150, 150, 150))
            screen.blit(hint, (55, HEIGHT - 85))
    
    # -------------------------------------------------------------------------
    # ИНВЕНТАРЬ
    # -------------------------------------------------------------------------
    
    def _render_inventory(self, screen):
        """Отрисовка окна инвентаря (если открыто)."""
        if not self.engine.inventory_open:
            return
        
        # Полупрозрачный фон
        surf = pygame.Surface((WIDTH - 200, HEIGHT - 200))
        surf.set_alpha(230)
        surf.fill(BLACK)
        screen.blit(surf, (100, 100))
        pygame.draw.rect(screen, WHITE, (100, 100, WIDTH - 200, HEIGHT - 200), 3)
        
        # Заголовок
        title_font = pygame.font.Font(None, 36)
        screen.blit(title_font.render("Инвентарь", True, YELLOW), (120, 120))
        
        # Список предметов (максимум 15)
        item_font = pygame.font.Font(None, 24)
        items = self.engine.game_state.inventory.get_items()
        
        if not items:
            screen.blit(item_font.render("(пусто)", True, (150, 150, 150)), (120, 170))
        else:
            for i, item_id in enumerate(items):
                if i >= 15:
                    break
                screen.blit(item_font.render(f"{i+1}. {item_id}", True, WHITE), (120, 170 + i * 30))
        
        # Подсказка
        screen.blit(item_font.render("Нажми I, чтобы закрыть", True, (150, 150, 150)), (120, HEIGHT - 130))
    
    # -------------------------------------------------------------------------
    # ВРЕМЕННОЕ СООБЩЕНИЕ
    # -------------------------------------------------------------------------
    
    def _render_temp_message(self, screen):
        """Отрисовка временного сообщения (показывается 2 секунды)."""
        if not self.engine.temp_message:
            return
        
        current_time = pygame.time.get_ticks()
        if current_time - self.engine.temp_message_timer < 2000:
            font = pygame.font.Font(None, 28)
            text_surf = font.render(self.engine.temp_message, True, WHITE)
            text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT - 100))
            bg_rect = text_rect.inflate(20, 10)
            
            # Фон сообщения
            pygame.draw.rect(screen, BLACK, bg_rect)
            pygame.draw.rect(screen, WHITE, bg_rect, 2)
            screen.blit(text_surf, text_rect)
        else:
            # Сообщение устарело — очищаем
            self.engine.temp_message = None
    
    # -------------------------------------------------------------------------
    # МЕНЮ СОХРАНЕНИЙ
    # -------------------------------------------------------------------------
    
    def _render_save_menu(self, screen):
        """Отрисовка меню сохранений (если открыто)."""
        if not self.engine.save_menu_open:
            return
        
        # Затенение экрана
        surf = pygame.Surface((WIDTH, HEIGHT))
        surf.set_alpha(180)
        surf.fill(BLACK)
        screen.blit(surf, (0, 0))
        
        # Окно меню
        box = pygame.Rect(WIDTH // 2 - 250, 100, 500, 450)
        pygame.draw.rect(screen, BLACK, box)
        pygame.draw.rect(screen, WHITE, box, 3)
        
        title_font = pygame.font.Font(None, 36)
        item_font = pygame.font.Font(None, 26)
        hint_font = pygame.font.Font(None, 20)
        
        # Заголовок (зависит от режима)
        title_text = "Сохранить игру" if self.engine.save_menu_mode == "save" else "Загрузить игру"
        title = title_font.render(title_text, True, YELLOW)
        screen.blit(title, (box.x + 20, box.y + 20))
        
        # Список сохранений
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
        
        # Подсказка по Enter
        if self.engine.save_menu_mode == "save":
            hint = "Enter — создать новое сохранение (автономер)"
        else:
            hint = "Enter — загрузить выбранное"
        hint_text = hint_font.render(hint, True, (180, 180, 180))
        screen.blit(hint_text, (box.x + 20, box.y + box.height - 60))
        
        # Подсказка по ESC
        esc_text = hint_font.render("ESC — закрыть", True, (180, 180, 180))
        screen.blit(esc_text, (box.x + 20, box.y + box.height - 30))
    
    # -------------------------------------------------------------------------
    # ПОДСКАЗКИ УПРАВЛЕНИЯ
    # -------------------------------------------------------------------------
    
    def _render_hints(self, screen):
        """Отрисовка памятки управления внизу экрана."""
        help_font = pygame.font.Font(None, 20)
        hint = help_font.render(
            "WASD/стрелки — движение | E — взаимодействие | I — инвентарь | "
            "F5 — сохранить | F9 — загрузить | ESC — меню",
            True, (180, 180, 180)
        )
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 15)))