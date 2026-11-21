# ui/inventory_ui.py
# =============================================================================
# ИНВЕНТАРЬ (INVENTORY MENU)
# Полноэкранное модальное окно с тремя блоками:
#   1. ЭКИПИРОВКА (слева) — Paper Doll с 6 слотами
#   2. ИНВЕНТАРЬ (в центре) — 3 вкладки по категории хранения
#   3. ИСТОЧНИК (справа) — контейнер/дроп (опционально, в режиме обмена)
#
# Архитектурная роль:
#   - GameEngine только создаёт InventoryMenu и делегирует события/отрисовку.
#   - Renderer остаётся нетронутым.
#   - Полностью заменяет старый LootMenu.
#
# Управление:
#   ← → — переключение блоков
#   ↑ ↓ — выбор предмета/слота в активном блоке
#   Enter — использовать предмет (заглушка, реализуется на Этапе 2)
#   E — экипировать/снять (заглушка, реализуется на Этапе 2)
#   Delete — выбросить под ноги
#   I / ESC — закрыть
# =============================================================================

import pygame
import os
from settings import WIDTH, HEIGHT, BLACK, WHITE, YELLOW, GREEN, RED
from logger import log
from objects.item import PaperDollSlot

# Путь к фоновому изображению (опционально)
BG_IMAGE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "images", "inventory_bg.png"
)

# Порядок блоков при навигации ← →
# Источник добавляется только в режиме обмена
BLOCK_ORDER_DEFAULT = ["paper_doll", "archive", "casket", "burden"]
BLOCK_ORDER_EXCHANGE = ["paper_doll", "archive", "casket", "burden", "source"]

# Подписи блоков
BLOCK_LABELS = {
    "paper_doll": "ЭКИПИРОВКА",
    "archive": "АРХИВ",
    "casket": "ЛАРЕЦ",
    "burden": "ПОКЛАЖА",
    "source": "ИСТОЧНИК",
}

# Подписи слотов Paper Doll
PAPERDOLL_SLOTS = [
    ("clothing", "Одежда"),
    ("patch", "Вышивка"),
    ("weapon", "Оружие"),
    ("tool", "Инструмент"),
    ("ring", "Перстень"),
    ("amulet", "Амулет"),
]

# Цветовая кодировка категорий (совпадает с loot_menu_ui)
CATEGORY_COLORS = {
    "weapon":     (220, 70, 70),
    "document":   (100, 150, 255),
    "key":        (255, 215, 0),
    "consumable": (100, 255, 100),
    "clothing":   (200, 200, 200),
    "tool":       (200, 180, 120),
    "valuable":   (255, 200, 100),
    "jewelry":    (255, 200, 100),
    "quest":      (200, 100, 255),
    "ingredient": (150, 255, 150),
    "ammo":       (220, 180, 100),
}
DEFAULT_ITEM_COLOR = (230, 230, 230)


class InventoryMenu:
    """
    Полноэкранное окно инвентаря с тремя блоками.
    
    Режимы работы:
        - "inventory" — открыт по клавише I, правый блок скрыт
        - "exchange"  — открыт при взаимодействии с контейнером/дропом,
                        правый блок показывает содержимое источника
    """
    
    def __init__(self, game_engine):
        self.engine = game_engine
        self.is_active = False
        self.mode = "inventory"  # "inventory" | "exchange"
        
        # Источник обмена (только в режиме exchange)
        self.source = None
        self.source_type = None  # "container" | "drop"
        
        # Активный блок
        self.active_block = "archive"  # По умолчанию — Архив
        
        # Индексы выбора внутри каждого блока
        self.paper_doll_selected = 0
        self.archive_selected = 0
        self.casket_selected = 0
        self.burden_selected = 0
        self.source_selected = 0
        
        # Кэш шрифтов
        self._fonts = {}
        
        # Фоновое изображение (опционально)
        self.bg_image = self._load_background()
    
    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================
    
    def _get_font(self, size: int):
        """Возвращает шрифт заданного размера из кэша."""
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]
    
    def _load_background(self):
        """Загружает фоновое изображение (если есть)."""
        if os.path.exists(BG_IMAGE_PATH):
            try:
                image = pygame.image.load(BG_IMAGE_PATH)
                return pygame.transform.scale(image, (WIDTH, HEIGHT))
            except Exception as e:
                log.warning(f"INVENTORY: не удалось загрузить фон {BG_IMAGE_PATH}: {e}")
        return None
    
    def _get_item_color(self, item) -> tuple:
        """Возвращает цвет предмета по его категории."""
        try:
            return CATEGORY_COLORS.get(item.category.value, DEFAULT_ITEM_COLOR)
        except Exception:
            return DEFAULT_ITEM_COLOR

    def _get_source_title(self) -> str:
        """
        Возвращает заголовок для правого блока (источника обмена).
        
        Возвращает:
            str: Имя контейнера или "Куча на земле" для дропа.
        """
        if self.source is None:
            return "Источник"
        if self.source_type == "container":
            return getattr(self.source, 'name', 'Контейнер')
        elif self.source_type == "drop":
            return "Куча на земле"
        return "Источник"
    
    def _get_block_order(self) -> list:
        """Возвращает порядок блоков с учётом текущего режима."""
        if self.mode == "exchange":
            return BLOCK_ORDER_EXCHANGE
        return BLOCK_ORDER_DEFAULT
    
    def _get_selected_index(self) -> int:
        """Возвращает индекс выбора в активном блоке."""
        return {
            "paper_doll": self.paper_doll_selected,
            "archive": self.archive_selected,
            "casket": self.casket_selected,
            "burden": self.burden_selected,
            "source": self.source_selected,
        }.get(self.active_block, 0)
    
    def _set_selected_index(self, value: int):
        """Устанавливает индекс выбора в активном блоке."""
        if self.active_block == "paper_doll":
            self.paper_doll_selected = value
        elif self.active_block == "archive":
            self.archive_selected = value
        elif self.active_block == "casket":
            self.casket_selected = value
        elif self.active_block == "burden":
            self.burden_selected = value
        elif self.active_block == "source":
            self.source_selected = value
    
    def _get_active_items(self) -> list:
        """Возвращает список предметов активного блока."""
        inv = self.engine.game_state.inventory
        
        if self.active_block == "paper_doll":
            return []  # На Этапе 1 слоты пустые
        elif self.active_block == "archive":
            return inv.get_items_by_storage("archive")
        elif self.active_block == "casket":
            return inv.get_items_by_storage("casket")
        elif self.active_block == "burden":
            return inv.get_items_by_storage("burden")
        elif self.active_block == "source":
            if self.source is None:
                return []
            return self.source.get_items()
        return []
    
    def _clamp_active_index(self):
        """Корректирует индекс после изменений списка."""
        items = self._get_active_items()
        max_idx = max(0, len(items) - 1) if items else 0
        
        # Для paper_doll индекс ограничен количеством слотов
        if self.active_block == "paper_doll":
            max_idx = len(PAPERDOLL_SLOTS) - 1
        
        current = self._get_selected_index()
        self._set_selected_index(max(0, min(current, max_idx)))
    
    # =========================================================================
    # ОТКРЫТИЕ / ЗАКРЫТИЕ
    # =========================================================================
    
    def open(self, source=None, source_type: str = None):
        """
        Открывает окно инвентаря.
        
        Аргументы:
            source: Container или ItemDrop (опционально).
            source_type: "container" | "drop" (опционально).
            
        Если source передан — режим "exchange" (с правым блоком).
        Если не передан — режим "inventory" (только свои предметы).
        """
        self.is_active = True
        
        if source is not None:
            self.mode = "exchange"
            self.source = source
            self.source_type = source_type
            # При обмене фокусируемся на источнике
            self.active_block = "source"
            self.source_selected = 0
            log.info(f"INVENTORY: открыт в режиме обмена с {source_type} "
                     f"'{getattr(source, 'name', source.id)}'")
        else:
            self.mode = "inventory"
            self.source = None
            self.source_type = None
            # По умолчанию — Архив
            self.active_block = "archive"
            self.archive_selected = 0
            log.info("INVENTORY: открыт")
    
    def close(self):
        """
        Закрывает окно инвентаря.
        Если был режим обмена с дропом и дроп опустел — удаляет его с карты.
        """
        if self.mode == "exchange" and self.source_type == "drop" and self.source is not None:
            if self.source.is_empty:
                current_map = self.engine.current_map
                if self.source in current_map.drops:
                    current_map.drops.remove(self.source)
                    log.info(f"INVENTORY: пустой дроп {self.source.id} удалён с карты")
        
        log.info(f"INVENTORY: закрыт (режим {self.mode})")
        self.is_active = False
        self.mode = "inventory"
        self.source = None
        self.source_type = None
    
    # =========================================================================
    # ОБРАБОТКА ВВОДА
    # =========================================================================
    
    def handle_event(self, event) -> bool:
        """
        Обрабатывает событие pygame. Возвращает True, если событие обработано.
        """
        if event.type != pygame.KEYDOWN:
            return False
        
        # --- I / ESC: закрыть окно ---
        if event.key in (pygame.K_i, pygame.K_ESCAPE):
            self.close()
            return True
        
        # --- ← →: переключение блоков ---
        if event.key == pygame.K_LEFT:
            blocks = self._get_block_order()
            current_idx = blocks.index(self.active_block) if self.active_block in blocks else 0
            new_idx = (current_idx - 1) % len(blocks)
            self.active_block = blocks[new_idx]
            self._clamp_active_index()
            log.info(f"INVENTORY: активный блок = {self.active_block}")
            return True
        
        if event.key == pygame.K_RIGHT:
            blocks = self._get_block_order()
            current_idx = blocks.index(self.active_block) if self.active_block in blocks else 0
            new_idx = (current_idx + 1) % len(blocks)
            self.active_block = blocks[new_idx]
            self._clamp_active_index()
            log.info(f"INVENTORY: активный блок = {self.active_block}")
            return True
        
        # --- ↑ ↓: навигация внутри активного блока ---
        if event.key == pygame.K_UP:
            self._set_selected_index(max(0, self._get_selected_index() - 1))
            return True
        
        if event.key == pygame.K_DOWN:
            items = self._get_active_items()
            if self.active_block == "paper_doll":
                max_idx = len(PAPERDOLL_SLOTS) - 1
            else:
                max_idx = max(0, len(items) - 1) if items else 0
            self._set_selected_index(min(max_idx, self._get_selected_index() + 1))
            return True
        
        # --- Enter: использовать (заглушка на Этапе 1) ---
        if event.key == pygame.K_RETURN:
            self._on_enter()
            return True
        
        # --- E: экипировать (заглушка на Этапе 1) ---
        if event.key == pygame.K_e:
            self._on_equip()
            return True
        
        # --- Delete: выбросить под ноги ---
        if event.key == pygame.K_DELETE:
            self._on_drop()
            return True
        
        return True  # Любая другая клавиша — поглощаем
    
    # -------------------------------------------------------------------------
    # ДЕЙСТВИЯ (заглушки для Этапа 1)
    # -------------------------------------------------------------------------
    
    def _on_enter(self):
        """
        Enter: перенос предмета между панелями или использование.
        Защищённая версия с полным try/except и детальным логированием.
        """
        try:
            inv = self.engine.game_state.inventory
            
            # =================================================================
            # БЛОК SOURCE: перенос предмета в инвентарь игрока
            # =================================================================
            if self.active_block == "source":
                log.info("INVENTORY._on_enter: блок source, начинаю перенос")
                
                items = self.source.get_items() if self.source else []
                idx = self.source_selected
                
                if not items or idx >= len(items):
                    self.engine._show_message("Нечего брать")
                    return
                
                item = items[idx]
                log.info(f"INVENTORY._on_enter: выбран {item.name} (ID: {item.id})")
                
                # Пробуем добавить в инвентарь (проверка веса внутри add_item)
                added = inv.add_item(item)
                if not added:
                    self.engine._show_message(f"{item.name} не влез (превышен вес)")
                    log.info(f"INVENTORY._on_enter: {item.name} не влез")
                    return
                
                log.info(f"INVENTORY._on_enter: предмет добавлен в инвентарь")
                
                # Удаляем из source
                if self.source_type == "container":
                    self.source.remove_item(item)
                else:
                    self.source.take_item(item)
                
                log.info(f"INVENTORY._on_enter: предмет удалён из source")
                
                # Сообщение игроку
                source_title = self._get_source_title() if self.source else "источник"
                log.info(f"INVENTORY: взято {item.name} из {source_title}")
                self.engine._show_message(f"Взято: {item.name}")
                
                # Автопереключение на блок, соответствующий storage_type предмета
                try:
                    # Безопасно получаем storage_type
                    storage = None
                    if hasattr(item, 'storage_type') and item.storage_type is not None:
                        if hasattr(item.storage_type, 'value'):
                            storage = item.storage_type.value
                        else:
                            storage = str(item.storage_type)
                    
                    if storage in ("archive", "casket", "burden"):
                        self.active_block = storage
                        # Устанавливаем индекс на последнюю позицию
                        items_in_block = inv.get_items_by_storage(storage)
                        if items_in_block:
                            self._set_selected_index(len(items_in_block) - 1)
                        log.info(f"INVENTORY._on_enter: автопереключение на блок {storage}")
                except Exception as e:
                    log.warning(f"INVENTORY._on_enter: ошибка автопереключения: {e}")
                
                # Корректируем индекс в блоке source
                remaining = self.source.get_items() if self.source else []
                if remaining:
                    self.source_selected = min(self.source_selected, len(remaining) - 1)
                else:
                    self.source_selected = 0
                
                log.info("INVENTORY._on_enter: перенос из source завершён успешно")
                return
            
            # =================================================================
            # БЛОК PAPER DOLL: ничего не делаем (снятие через E)
            # =================================================================
            if self.active_block == "paper_doll":
                log.info("INVENTORY._on_enter: блок paper_doll, игнорирую Enter")
                return
            
            # =================================================================
            # БЛОКИ ИНВЕНТАРЯ (archive / casket / burden)
            # =================================================================
            items = self._get_active_items()
            idx = self._get_selected_index()
            
            if not items or idx >= len(items):
                return
            
            item = items[idx]
            log.info(f"INVENTORY._on_enter: выбран {item.name} в блоке {self.active_block}")
            
            # --- Документ → читаем ---
            from objects.item import ItemCategory
            if item.category == ItemCategory.DOCUMENT:
                if hasattr(self.engine, 'document_viewer'):
                    log.info(f"INVENTORY: чтение документа {item.name}")  # 1. Логируем намерение
                    self.close()  # 2. Закрыли инвентарь
                    self.engine.document_viewer.open(item.text, item.name)  # 3. Открыли окно
                return
            
            # --- Режим exchange → перенос в source ---
            if self.mode == "exchange" and self.source is not None:
                removed = inv.remove_item(item)
                if not removed:
                    log.warning(f"INVENTORY._on_enter: не удалось удалить {item.name}")
                    return
                
                self.source.add_item(item)
                log.info(f"INVENTORY: положено {item.name} в {self._get_source_title()}")
                self.engine._show_message(f"Положено: {item.name}")
                self._clamp_active_index()
                return
            
            # --- Иначе — заглушка ---
            self.engine._show_message(f"Использование {item.name} (скоро)")
            log.info(f"INVENTORY: попытка использовать {item.name} (заглушка)")
        
        except Exception as e:
            # Глобальный отлов — игра не упадёт
            import traceback
            log.error(f"INVENTORY._on_enter: КРИТИЧЕСКАЯ ОШИБКА: {e}")
            log.error(f"INVENTORY._on_enter: traceback:\n{traceback.format_exc()}")
            self.engine._show_message(f"Ошибка: {type(e).__name__}")

    def _on_equip(self):
        """
        Экипировка/снятие предмета.
        
        Логика:
            - В блоке paper_doll (выбран занятый слот) → снять предмет в инвентарь.
            - В блоке archive/casket/burden (выбран экипируемый предмет) → надеть.
            - В блоке source → ничего.
        """
        inv = self.engine.game_state.inventory
        
        if self.active_block == "paper_doll":
            # Снятие предмета с Paper Doll
            slot_id = PAPERDOLL_SLOTS[self.paper_doll_selected][0]
            try:
                slot = PaperDollSlot(slot_id)
            except ValueError:
                return
            
            item = inv.get_equipped(slot)
            if item is None:
                self.engine._show_message("Слот пуст")
                return
            
            removed = inv.unequip(slot)
            if removed:
                self.engine._show_message(f"Снято: {removed.name}")
            return
        
        if self.active_block in ("archive", "casket", "burden"):
            # Экипировка предмета из инвентаря
            items = self._get_active_items()
            idx = self._get_selected_index()
            
            if not items or idx >= len(items):
                self.engine._show_message("Нечего экипировать")
                return
            
            item = items[idx]
            
            if not item.equippable:
                self.engine._show_message("Этот предмет нельзя надеть")
                return
            
            if not hasattr(item, 'slot') or item.slot is None:
                self.engine._show_message("У предмета не указан слот")
                return
            
            if inv.equip(item):
                self.engine._show_message(f"Надето: {item.name}")
                # Корректируем индекс (предмет ушёл из инвентаря)
                self._clamp_active_index()
            return
        
        if self.active_block == "source":
            self.engine._show_message("Нельзя экипировать отсюда")
            return
    
    def _on_drop(self):
        """
        Выброс выбранного предмета под ноги.
        Работает для инвентаря (archive/casket/burden) и Paper Doll.
        """
        inv = self.engine.game_state.inventory
        
        # Выбрасывать можно из своих блоков инвентаря и Paper Doll
        if self.active_block == "source":
            self.engine._show_message("Нельзя выбросить отсюда")
            return
        
        # Определяем предмет для выброса
        if self.active_block == "paper_doll":
            # Выброс экипированного предмета
            slot_id = PAPERDOLL_SLOTS[self.paper_doll_selected][0]
            try:
                slot = PaperDollSlot(slot_id)
            except ValueError:
                return
            
            item = inv.get_equipped(slot)
            if item is None:
                self.engine._show_message("Слот пуст")
                return
            
            # Сначала снимаем в инвентарь
            inv.unequip(slot)
            # Теперь item в инвентаре, выбрасываем его
            removed = inv.remove_item(item)
            if not removed:
                log.warning(f"INVENTORY: не удалось удалить {item.name} для выброса")
                return
        else:
            # Выброс из инвентаря
            items = self._get_active_items()
            idx = self._get_selected_index()
            
            if not items or idx >= len(items):
                self.engine._show_message("Нечего выбрасывать")
                return
            
            item = items[idx]
            
            # Квестовые предметы нельзя выбрасывать
            from objects.item import ItemCategory
            if item.category == ItemCategory.QUEST:
                self.engine._show_message("Этот предмет слишком важен")
                log.info(f"INVENTORY: отказ в выбросе квестового {item.name}")
                return
            
            # Удаляем из инвентаря
            removed = inv.remove_item(item)
            if not removed:
                log.warning(f"INVENTORY: не удалось удалить {item.name} для выброса")
                return
        
        # Бросаем под ноги игрока
        player_x = self.engine.game_state.player.x
        player_y = self.engine.game_state.player.y
        self.engine.current_map.add_or_update_drop(player_x, player_y, item)
        
        log.info(f"INVENTORY: выброшено {item.name} на ({player_x},{player_y})")
        self.engine._show_message(f"Выброшено: {item.name}")
        
        # Корректируем индекс
        self._clamp_active_index()

    # =========================================================================
    # ОТРИСОВКА
    # =========================================================================
    
    def render(self, screen):
        """Отрисовывает окно инвентаря поверх карты."""
        if not self.is_active:
            return
        
        # --- 1. ФОН ---
        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
            # Затемнение поверх для читаемости
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(180)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))
        else:
            # Fallback: тёмный фон
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(220)
            overlay.fill((10, 8, 5))
            screen.blit(overlay, (0, 0))
        
        # --- 2. РАЗМЕРЫ ОКНА ---
        box_width = int(WIDTH * 0.9)
        box_height = int(HEIGHT * 0.85)
        box_x = (WIDTH - box_width) // 2
        box_y = (HEIGHT - box_height) // 2
        
        box_rect = pygame.Rect(box_x, box_y, box_width, box_height)
        pygame.draw.rect(screen, (20, 15, 10), box_rect)
        pygame.draw.rect(screen, (120, 100, 60), box_rect, 2)
        
        # Внутренние отступы
        padding = 20
        content_x = box_x + padding
        content_y = box_y + padding
        content_width = box_width - 2 * padding
        content_height = box_height - 2 * padding - 40  # 40 под подсказки
        
        # --- 3. ПРОПОРЦИИ БЛОКОВ ---
        if self.mode == "exchange":
            # 3 блока: 22% / 35% / 43%
            w1 = int(content_width * 0.22)
            w2 = int(content_width * 0.35)
            w3 = content_width - w1 - w2 - 20  # 20 на 2 разделителя
        else:
            # 2 блока: 28% / 72%
            w1 = int(content_width * 0.28)
            w2 = content_width - w1 - 10  # 10 на разделитель
            w3 = 0
        
        gap = 10
        h = content_height
        
        # Позиции блоков
        x1 = content_x
        x2 = content_x + w1 + gap
        x3 = content_x + w1 + gap + w2 + gap
        y = content_y
        
        # --- 4. ОТРИСОВКА БЛОКОВ ---
        self._render_paper_doll(screen, x1, y, w1, h)
        self._render_inventory_block(screen, x2, y, w2, h)
        
        if self.mode == "exchange":
            self._render_source_block(screen, x3, y, w3, h)
        
        # --- 5. ПОДСКАЗКИ ВНИЗУ ---
        self._render_hints(screen, box_x, box_y + box_height - 35, box_width)
    
    # -------------------------------------------------------------------------
    # БЛОК 1: ЭКИПИРОВКА (Paper Doll)
    # -------------------------------------------------------------------------
    def _render_paper_doll(self, screen, x, y, w, h):
        """Левый блок: список слотов Paper Doll с реальными предметами."""
        is_active = (self.active_block == "paper_doll")
        
        # Рамка блока
        rect = pygame.Rect(x, y, w, h)
        border_color = YELLOW if is_active else (80, 80, 80)
        border_width = 3 if is_active else 1
        pygame.draw.rect(screen, (30, 25, 20), rect)
        pygame.draw.rect(screen, border_color, rect, border_width)
        
        # Заголовок
        title_font = self._get_font(22)
        title_surf = title_font.render(BLOCK_LABELS["paper_doll"], True, YELLOW)
        screen.blit(title_surf, (x + 10, y + 8))
        
        # Разделитель
        pygame.draw.line(screen, (80, 70, 50), (x + 10, y + 35), (x + w - 10, y + 35), 1)
        
        # Слоты
        slot_font = self._get_font(18)
        item_font = self._get_font(16)
        slot_height = 45  # Увеличили высоту для двух строк
        start_y = y + 50
        
        inv = self.engine.game_state.inventory
        
        for i, (slot_id, slot_name) in enumerate(PAPERDOLL_SLOTS):
            slot_y = start_y + i * slot_height
            is_selected = (is_active and i == self.paper_doll_selected)
            
            # Подсветка выбранного слота
            if is_selected:
                highlight = pygame.Rect(x + 5, slot_y - 2, w - 10, slot_height - 4)
                pygame.draw.rect(screen, (60, 50, 20), highlight)
            
            # Маркер
            marker = "▶" if is_selected else " "
            marker_surf = slot_font.render(marker, True, YELLOW)
            screen.blit(marker_surf, (x + 10, slot_y + 5))
            
            # Название слота
            label_surf = slot_font.render(slot_name + ":", True, (200, 200, 200))
            screen.blit(label_surf, (x + 30, slot_y + 5))
            
            # Содержимое слота (реальный предмет или "—")
            try:
                slot = PaperDollSlot(slot_id)
                item = inv.get_equipped(slot)
                
                if item:
                    # Показываем имя предмета с цветом категории
                    color = self._get_item_color(item)
                    value_surf = item_font.render(item.name, True, color)
                else:
                    value_surf = item_font.render("—", True, (120, 120, 120))
            except ValueError:
                value_surf = item_font.render("—", True, (120, 120, 120))
            
            screen.blit(value_surf, (x + 30, slot_y + 25))
        
        # Вес внизу блока
        weight_text = f"Вес: {inv.get_total_weight():.1f}/{inv.max_weight:.1f} кг"
        weight_font = self._get_font(16)
        weight_surf = weight_font.render(weight_text, True, (180, 180, 180))
        screen.blit(weight_surf, (x + 10, y + h - 25))

    # -------------------------------------------------------------------------
    # БЛОК 2: ИНВЕНТАРЬ (3 секции)
    # -------------------------------------------------------------------------
    
    def _render_inventory_block(self, screen, x, y, w, h):
        """Средний блок: 3 секции (Архив / Ларец / Поклажа)."""
        # Рамка блока
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, (30, 25, 20), rect)
        pygame.draw.rect(screen, (80, 70, 50), rect, 1)
        
        # Заголовок
        title_font = self._get_font(22)
        title_surf = title_font.render("ИНВЕНТАРЬ", True, YELLOW)
        screen.blit(title_surf, (x + 10, y + 8))
        
        # Три секции, примерно равной высоты
        section_height = (h - 40) // 3  # 40 под заголовок
        sections = [
            ("archive", "АРХИВ", self.archive_selected),
            ("casket", "ЛАРЕЦ", self.casket_selected),
            ("burden", "ПОКЛАЖА", self.burden_selected),
        ]
        
        for i, (block_id, label, sel_idx) in enumerate(sections):
            sec_y = y + 40 + i * section_height
            self._render_storage_section(
                screen, x + 5, sec_y, w - 10, section_height - 5,
                block_id, label, sel_idx
            )
    
    def _render_storage_section(self, screen, x, y, w, h, block_id, label, sel_idx):
        """Отрисовка одной секции (Архив / Ларец / Поклажа)."""
        is_active = (self.active_block == block_id)
        
        # Фон секции
        if is_active:
            bg_color = (40, 35, 25)
            border_color = YELLOW
            border_width = 2
        else:
            bg_color = (25, 22, 18)
            border_color = (60, 55, 45)
            border_width = 1
        
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, bg_color, rect)
        pygame.draw.rect(screen, border_color, rect, border_width)
        
        # Заголовок секции
        label_font = self._get_font(16)
        label_color = YELLOW if is_active else (150, 140, 110)
        label_surf = label_font.render(f"[{label}]", True, label_color)
        screen.blit(label_surf, (x + 8, y + 4))
        
        # Список предметов
        inv = self.engine.game_state.inventory
        items = inv.get_items_by_storage(block_id)
        
        item_font = self._get_font(16)
        row_height = 22
        max_visible = (h - 30) // row_height
        list_y = y + 26
        
        if not items:
            empty_surf = item_font.render("(пусто)", True, (100, 95, 85))
            screen.blit(empty_surf, (x + 15, list_y))
        else:
            for i, item in enumerate(items):
                if i >= max_visible:
                    more = item_font.render(
                        f"... ещё {len(items) - max_visible}",
                        True, (120, 115, 100)
                    )
                    screen.blit(more, (x + 15, list_y + max_visible * row_height))
                    break
                
                row_y = list_y + i * row_height
                is_selected = (is_active and i == sel_idx)
                
                # Подсветка
                if is_selected:
                    hl = pygame.Rect(x + 3, row_y - 1, w - 6, row_height - 2)
                    pygame.draw.rect(screen, (60, 50, 20), hl)
                
                # Маркер + имя + вес
                marker = "▶ " if is_selected else "   "
                color = self._get_item_color(item)
                text = f"{marker}{item.name}"
                if item.quantity > 1:
                    text += f" (x{item.quantity})"
                
                name_surf = item_font.render(text, True, color)
                screen.blit(name_surf, (x + 10, row_y + 1))
                
                # Вес справа
                weight_text = f"{item.weight * item.quantity:.1f}"
                weight_surf = item_font.render(weight_text, True, (120, 115, 100))
                screen.blit(weight_surf, (x + w - weight_surf.get_width() - 8, row_y + 1))
    
    # -------------------------------------------------------------------------
    # БЛОК 3: ИСТОЧНИК (только в режиме exchange)
    # -------------------------------------------------------------------------
    
    def _render_source_block(self, screen, x, y, w, h):
        """Правый блок: содержимое контейнера или дропа."""
        is_active = (self.active_block == "source")
        
        # Рамка
        rect = pygame.Rect(x, y, w, h)
        border_color = YELLOW if is_active else (80, 80, 80)
        border_width = 3 if is_active else 1
        pygame.draw.rect(screen, (30, 25, 20), rect)
        pygame.draw.rect(screen, border_color, rect, border_width)
        
        # Заголовок — имя источника
        title_font = self._get_font(20)
        if self.source_type == "container":
            title_text = self.source.name
        else:
            title_text = "Куча на земле"
        
        title_surf = title_font.render(title_text.upper(), True, YELLOW)
        screen.blit(title_surf, (x + 10, y + 8))
        
        # Разделитель
        pygame.draw.line(screen, (80, 70, 50), (x + 10, y + 35), (x + w - 10, y + 35), 1)
        
        # Список предметов
        items = self.source.get_items() if self.source else []
        item_font = self._get_font(18)
        row_height = 26
        max_visible = (h - 50) // row_height
        list_y = y + 45
        
        if not items:
            empty = item_font.render("(пусто)", True, (120, 120, 120))
            screen.blit(empty, (x + 15, list_y))
        else:
            for i, item in enumerate(items):
                if i >= max_visible:
                    more = item_font.render(
                        f"... ещё {len(items) - max_visible}",
                        True, (150, 150, 150)
                    )
                    screen.blit(more, (x + 15, list_y + max_visible * row_height))
                    break
                
                row_y = list_y + i * row_height
                is_selected = (is_active and i == self.source_selected)
                
                if is_selected:
                    hl = pygame.Rect(x + 3, row_y - 1, w - 6, row_height - 2)
                    pygame.draw.rect(screen, (60, 50, 20), hl)
                
                marker = "▶ " if is_selected else "   "
                color = self._get_item_color(item)
                text = f"{marker}{item.name}"
                if item.quantity > 1:
                    text += f" (x{item.quantity})"
                
                name_surf = item_font.render(text, True, color)
                screen.blit(name_surf, (x + 10, row_y + 2))
                
                weight_text = f"{item.weight * item.quantity:.1f} кг"
                weight_surf = item_font.render(weight_text, True, (120, 115, 100))
                screen.blit(weight_surf, (x + w - weight_surf.get_width() - 10, row_y + 2))
    
    # -------------------------------------------------------------------------
    # ПОДСКАЗКИ
    # -------------------------------------------------------------------------
    
    def _render_hints(self, screen, x, y, w):
        """Подсказки управления внизу окна."""
        hint_font = self._get_font(16)
        
        hint_parts = [
            "← → — блоки",
            "↑ ↓ — выбор",
            "Enter — использовать",
            "E — экипировать",
            "Del — выбросить",
            "ESC — закрыть",
        ]
        hint_text = "   |   ".join(hint_parts)
        hint_surf = hint_font.render(hint_text, True, (180, 170, 140))
        hint_x = x + (w - hint_surf.get_width()) // 2
        screen.blit(hint_surf, (hint_x, y))