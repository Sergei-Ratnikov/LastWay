# ui/loot_menu_ui.py
# =============================================================================
# ОКНО ОБМЕНА ПРЕДМЕТАМИ (LOOT MENU)
# Отдельный модуль, инкапсулирующий состояние, логику и отрисовку окна обмена
# между инвентарём игрока и контейнером/дропом.
#
# Архитектурная роль:
#   - GameEngine только создаёт LootMenu и делегирует ему события/отрисовку.
#   - Renderer остаётся нетронутым — LootMenu рендерит себя сам.
#   - Логика переноса предметов (вес, удаление пустого дропа) живёт здесь.
# =============================================================================

import pygame
from settings import WIDTH, HEIGHT, BLACK, WHITE, YELLOW, GREEN, RED
from logger import log


# -----------------------------------------------------------------------------
# ЦВЕТОВАЯ КОДИРОВКА КАТЕГОРИЙ ПРЕДМЕТОВ
# -----------------------------------------------------------------------------
# Сопоставление значения Enum ItemCategory с цветом для отображения в списках.
# Это сильно улучшает читаемость, когда предметов много.
CATEGORY_COLORS = {
    "weapon":     (220, 70, 70),    # Оружие — красное
    "document":   (100, 150, 255),  # Документы — синие
    "key":        (255, 215, 0),    # Ключи — жёлтые
    "consumable": (100, 255, 100),  # Расходники — зелёные
    "clothing":   (200, 200, 200),  # Одежда — светло-серая
    "tool":       (200, 180, 120),  # Инструменты — коричневато-бежевые
    "valuable":   (255, 200, 100),  # Ценности — золотые
    "jewelry":    (255, 200, 100),  # Украшения — золотые
    "quest":      (200, 100, 255),  # Квестовые — фиолетовые
    "ingredient": (150, 255, 150),  # Ингредиенты — светло-зелёные
    "ammo":       (220, 180, 100),  # Боеприпасы — охра
}
DEFAULT_ITEM_COLOR = (230, 230, 230)  # Если категория неизвестна


class LootMenu:
    """
    Окно обмена предметами между инвентарём игрока и источником (контейнер/дроп).
    
    Состояние:
        is_active (bool): Открыто ли окно.
        source: Объект-источник (Container или ItemDrop).
        source_type (str): "container" или "drop".
        selected_side (str): "player" или "source" — активная панель.
        selected_index (int): Индекс выбранного предмета в активной панели.
    """
    
    def __init__(self, game_engine):
        self.engine = game_engine
        self.is_active = False
        self.source = None
        self.source_type = None
        self.selected_side = "player"
        self.selected_index = 0
        
        # Кэш шрифтов, как в Renderer — чтобы не дёргать pygame.font.Font каждый кадр
        self._fonts = {}
    
    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================
    
    def _get_font(self, size: int):
        """Возвращает шрифт заданного размера из кэша."""
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]
    
    def _get_item_color(self, item) -> tuple:
        """
        Возвращает цвет для отображения предмета на основе его категории.
        Работает и с объектами Item (через Enum.value), и защищает от ошибок.
        """
        try:
            category_value = item.category.value
            return CATEGORY_COLORS.get(category_value, DEFAULT_ITEM_COLOR)
        except Exception:
            return DEFAULT_ITEM_COLOR
    
    def _get_player_items(self) -> list:
        """Возвращает список предметов игрока (объекты Item)."""
        return self.engine.game_state.inventory.get_items()
    
    def _get_source_items(self) -> list:
        """Возвращает список предметов из источника (объекты Item)."""
        if self.source is None:
            return []
        return self.source.get_items()
    
    def _get_source_title(self) -> str:
        """Возвращает заголовок для правой панели."""
        if self.source_type == "container":
            return self.source.name
        elif self.source_type == "drop":
            return "Куча на земле"
        return "Источник"
    
    def _get_active_list(self) -> list:
        """Возвращает список предметов активной панели."""
        if self.selected_side == "player":
            return self._get_player_items()
        return self._get_source_items()
    
    def _clamp_index(self):
        """
        Корректирует selected_index, если после переноса список стал короче.
        Вызывается после каждого переноса предмета.
        """
        active_list = self._get_active_list()
        if not active_list:
            self.selected_index = 0
        else:
            self.selected_index = max(0, min(self.selected_index, len(active_list) - 1))
    
    # =========================================================================
    # ОТКРЫТИЕ / ЗАКРЫТИЕ
    # =========================================================================
    
    def open(self, source, source_type: str):
        """
        Открывает окно обмена.
        
        Аргументы:
            source: Объект Container или ItemDrop.
            source_type (str): "container" или "drop".
        """
        self.source = source
        self.source_type = source_type
        self.is_active = True
        self.selected_side = "player"
        self.selected_index = 0
        log.info(f"LOOT_MENU: открыт обмен с {source_type} '{getattr(source, 'name', source.id)}'")
    
    def close(self):
        """
        Закрывает окно обмена.
        Если источником был дроп и он опустел — удаляет его с карты.
        """
        # Проверяем, не опустел ли дроп — удаляем с карты
        if self.source_type == "drop" and self.source is not None:
            if self.source.is_empty:
                current_map = self.engine.current_map
                if self.source in current_map.drops:
                    current_map.drops.remove(self.source)
                    log.info(f"LOOT_MENU: пустой дроп {self.source.id} удалён с карты")
        
        log.info(f"LOOT_MENU: закрыт обмен с {self.source_type}")
        self.is_active = False
        self.source = None
        self.source_type = None
        self.selected_side = "player"
        self.selected_index = 0
    
    # =========================================================================
    # ОБРАБОТКА ВВОДА
    # =========================================================================
    
    def handle_event(self, event) -> bool:
        """
        Обрабатывает событие pygame, когда окно открыто.
        
        Возвращает:
            bool: True, если событие обработано (GameEngine не должен его передавать дальше).
        """
        if event.type != pygame.KEYDOWN:
            return False
        
        # --- ESC: закрыть окно ---
        if event.key == pygame.K_ESCAPE:
            self.close()
            return True
        
        # --- ← →: переключение активной панели ---
        if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.selected_side = "source" if self.selected_side == "player" else "player"
            # Сбрасываем индекс при смене панели (или оставляем — на выбор)
            self.selected_index = 0
            log.info(f"LOOT_MENU: активная панель = {self.selected_side}")
            return True
        
        # --- ↑ ↓: навигация по списку ---
        if event.key == pygame.K_UP:
            self.selected_index = max(0, self.selected_index - 1)
            return True
        if event.key == pygame.K_DOWN:
            active_list = self._get_active_list()
            self.selected_index = min(len(active_list) - 1, self.selected_index + 1)
            return True
        
        # --- Enter / Space: перенос выбранного предмета ---
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._transfer_item()
            return True
        
        # Любая другая клавиша — игнорируем (но событие считаем обработанным,
        # чтобы игрок случайно не открыл инвентарь или не начал движение)
        return True
    
    # =========================================================================
    # ЛОГИКА ПЕРЕНОСА ПРЕДМЕТОВ
    # =========================================================================
    
    def _transfer_item(self):
        """
        Переносит выбранный предмет из активной панели в противоположную.
        
        Логика:
            - player → source: всегда разрешено (контейнеры/дропы безлимитны).
            - source → player: проверяем вес через inventory.add_item().
        """
        active_list = self._get_active_list()
        if not active_list or self.selected_index >= len(active_list):
            return
        
        item = active_list[self.selected_index]
        inventory = self.engine.game_state.inventory
        
        if self.selected_side == "player":
            # --- ИГРОК → ИСТОЧНИК ---
            # Удаляем из инвентаря
            removed = inventory.remove_item(item)
            if removed:
                # Добавляем в источник
                self.source.add_item(item)
                log.info(f"LOOT_MENU: игрок положил {item.name} в {self._get_source_title()}")
                self.engine._show_message(f"Положено: {item.name}")
            else:
                log.warning(f"LOOT_MENU: не удалось удалить {item.name} из инвентаря")
                return
        else:
            # --- ИСТОЧНИК → ИГРОК ---
            # Пробуем добавить в инвентарь (там внутри проверка веса)
            added = inventory.add_item(item)
            if added:
                # Удаляем из источника
                if self.source_type == "container":
                    self.source.remove_item(item)
                else:
                    self.source.take_item(item)
                log.info(f"LOOT_MENU: игрок взял {item.name} из {self._get_source_title()}")
                self.engine._show_message(f"Взято: {item.name}")
            else:
                # Не влез по весу — предмет остаётся на месте
                log.info(f"LOOT_MENU: {item.name} не влез (превышен вес)")
                self.engine._show_message(f"{item.name} не влез (превышен вес)")
                return
        
        # Корректируем индекс (список мог стать короче)
        self._clamp_index()
    
    # =========================================================================
    # ОТРИСОВКА
    # =========================================================================
    
    def render(self, screen):
        """
        Отрисовывает окно обмена поверх карты.
        Вызывается из GameEngine.render() после основного рендера.
        """
        if not self.is_active:
            return
        
        # --- 1. ЗАТЕМНЕНИЕ ФОНА (как в save_menu) ---
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        
        # --- 2. РАЗМЕРЫ И ПОЗИЦИИ ---
        # Большое окно по центру, как save_menu, но шире для двух панелей
        box_width = 900
        box_height = 550
        box_x = WIDTH // 2 - box_width // 2
        box_y = HEIGHT // 2 - box_height // 2
        
        box_rect = pygame.Rect(box_x, box_y, box_width, box_height)
        pygame.draw.rect(screen, BLACK, box_rect)
        pygame.draw.rect(screen, WHITE, box_rect, 3)
        
        # Внутренние отступы
        padding = 20
        content_x = box_x + padding
        content_y = box_y + padding
        content_width = box_width - 2 * padding
        content_height = box_height - 2 * padding - 40  # 40 под подсказки внизу
        
        # --- 3. ДВЕ ПАНЕЛИ (по 48% ширины, 4% — разделитель) ---
        panel_width = int(content_width * 0.48)
        panel_height = content_height - 30  # 30 под заголовок
        left_x = content_x
        right_x = content_x + panel_width + int(content_width * 0.04)
        panels_y = content_y + 30
        
        # --- 4. ЗАГОЛОВКИ ПАНЕЛЕЙ ---
        title_font = self._get_font(28)
        
        # Левая панель: инвентарь игрока
        player_title = title_font.render(
            f"Инвентарь ({self.engine.game_state.player.player_class})",
            True, YELLOW
        )
        screen.blit(player_title, (left_x, content_y))
        
        # Правая панель: источник
        source_title = title_font.render(self._get_source_title(), True, YELLOW)
        screen.blit(source_title, (right_x, content_y))
        
        # --- 5. РАМКИ ПАНЕЛЕЙ (активная — яркая, неактивная — тусклая) ---
        left_rect = pygame.Rect(left_x, panels_y, panel_width, panel_height)
        right_rect = pygame.Rect(right_x, panels_y, panel_width, panel_height)
        
        if self.selected_side == "player":
            pygame.draw.rect(screen, YELLOW, left_rect, 3)     # Активная
            pygame.draw.rect(screen, (80, 80, 80), right_rect, 2)  # Неактивная
        else:
            pygame.draw.rect(screen, (80, 80, 80), left_rect, 2)
            pygame.draw.rect(screen, YELLOW, right_rect, 3)
        
        # --- 6. СПИСКИ ПРЕДМЕТОВ ---
        item_font = self._get_font(22)
        weight_font = self._get_font(18)
        row_height = 28
        max_visible = panel_height // row_height - 1  # Минус 1 для веса
        
        # 6.1. Список инвентаря (левая панель)
        player_items = self._get_player_items()
        if not player_items:
            empty_text = item_font.render("(пусто)", True, (120, 120, 120))
            screen.blit(empty_text, (left_x + 10, panels_y + 10))
        else:
            for i, item in enumerate(player_items):
                if i >= max_visible:
                    more_text = item_font.render(f"... ещё {len(player_items) - max_visible}", 
                                                  True, (150, 150, 150))
                    screen.blit(more_text, (left_x + 10, panels_y + 10 + max_visible * row_height))
                    break
                
                row_y = panels_y + 10 + i * row_height
                is_selected = (self.selected_side == "player" and i == self.selected_index)
                color = self._get_item_color(item)
                
                # Маркер выбора
                marker = "▶ " if is_selected else "  "
                
                # Формат: "▶ Ключ от часовни    0.1 кг"
                name_part = f"{marker}{item.name}"
                weight_part = f"{item.weight * item.quantity:.2f} кг"
                
                # Подсветка выбранной строки
                if is_selected:
                    highlight_rect = pygame.Rect(left_x + 2, row_y - 2, 
                                                  panel_width - 4, row_height)
                    pygame.draw.rect(screen, (60, 60, 20), highlight_rect)
                
                name_surf = item_font.render(name_part, True, color)
                weight_surf = weight_font.render(weight_part, True, (150, 150, 150))
                
                screen.blit(name_surf, (left_x + 10, row_y))
                # Вес справа
                screen.blit(weight_surf, 
                            (left_x + panel_width - weight_surf.get_width() - 10, 
                             row_y + 3))
        
        # 6.2. Список источника (правая панель)
        source_items = self._get_source_items()
        if not source_items:
            empty_text = item_font.render("(пусто)", True, (120, 120, 120))
            screen.blit(empty_text, (right_x + 10, panels_y + 10))
        else:
            for i, item in enumerate(source_items):
                if i >= max_visible:
                    more_text = item_font.render(f"... ещё {len(source_items) - max_visible}", 
                                                  True, (150, 150, 150))
                    screen.blit(more_text, (right_x + 10, panels_y + 10 + max_visible * row_height))
                    break
                
                row_y = panels_y + 10 + i * row_height
                is_selected = (self.selected_side == "source" and i == self.selected_index)
                color = self._get_item_color(item)
                
                marker = "▶ " if is_selected else "  "
                name_part = f"{marker}{item.name}"
                weight_part = f"{item.weight * item.quantity:.2f} кг"
                
                if is_selected:
                    highlight_rect = pygame.Rect(right_x + 2, row_y - 2, 
                                                  panel_width - 4, row_height)
                    pygame.draw.rect(screen, (60, 60, 20), highlight_rect)
                
                name_surf = item_font.render(name_part, True, color)
                weight_surf = weight_font.render(weight_part, True, (150, 150, 150))
                
                screen.blit(name_surf, (right_x + 10, row_y))
                screen.blit(weight_surf, 
                            (right_x + panel_width - weight_surf.get_width() - 10, 
                             row_y + 3))
        
        # --- 7. ИНФОРМАЦИЯ О ВЕСЕ ИГРОКА (под левой панелью) ---
        inv = self.engine.game_state.inventory
        weight_text = f"Вес: {inv.get_total_weight():.1f} / {inv.max_weight:.1f} кг"
        weight_surf = weight_font.render(weight_text, True, WHITE)
        screen.blit(weight_surf, (left_x, panels_y + panel_height + 5))
        
        # --- 8. ЦЕНТРАЛЬНЫЙ РАЗДЕЛИТЕЛЬ (стрелка ↔) ---
        arrow_font = self._get_font(36)
        arrow_surf = arrow_font.render("↔", True, (100, 100, 100))
        arrow_x = left_x + panel_width + (int(content_width * 0.04) - arrow_surf.get_width()) // 2
        arrow_y = panels_y + panel_height // 2 - arrow_surf.get_height() // 2
        screen.blit(arrow_surf, (arrow_x, arrow_y))
        
        # --- 9. ПОДСКАЗКИ УПРАВЛЕНИЯ (внизу окна) ---
        hint_font = self._get_font(18)
        hint_text = "← → — панели   |   ↑ ↓ — выбор   |   Enter — взять/положить   |   ESC — закрыть"
        hint_surf = hint_font.render(hint_text, True, (180, 180, 180))
        hint_x = box_x + (box_width - hint_surf.get_width()) // 2
        hint_y = box_y + box_height - 30
        screen.blit(hint_surf, (hint_x, hint_y))