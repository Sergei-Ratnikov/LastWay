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
    Класс для отрисовки всего: карты, сущностей, UI.
    Получает ссылку на GameEngine, чтобы иметь доступ ко всем нужным данным.
    Это единственный модуль в игре, который знает про pygame.draw и pygame.font.
    """
    def __init__(self, game_engine):
        self.engine = game_engine
        # Справочник предметов (singleton) для UI инвентаря
        self.item_data = ItemData()
        
        # ---------------------------------------------------------------------
        # КЭШИРОВАНИЕ РЕСУРСОВ
        # ---------------------------------------------------------------------
        # Словарь шрифтов {размер: FontObject}. Создаём каждый размер один раз,
        # чтобы не дёргать pygame.font.Font() 60 раз в секунду.
        self._fonts_cache = {}
        
        # Цвета для точек интереса животных (едим/спим/играем)
        self._poi_colors = {
            "food": (100, 255, 100),   # зелёный
            "home": (100, 100, 255),   # синий
            "toy":  (255, 255, 100),   # жёлтый
        }
        self._poi_labels = {
            "food": "еда",
            "home": "сон",
            "toy":  "игра",
        }

    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ (ХЕЛПЕРЫ)
    # =========================================================================
    def _get_font(self, size: int):
        """
        Возвращает шрифт заданного размера из кэша.
        Если шрифта ещё нет — создаёт и сохраняет.
        Это убирает огромное количество повторяющихся вызовов pygame.font.Font().
        """
        if size not in self._fonts_cache:
            self._fonts_cache[size] = pygame.font.Font(None, size)
        return self._fonts_cache[size]

    def _draw_entity_rect(self, screen, x, y, w, h, fill_color, border_color=BLACK, border_width=2):
        """
        Универсальная отрисовка прямоугольника на карте с рамкой.
        Используется для NPC, контейнеров, дропов, животных.
        Координаты передаются в КЛЕТКАХ (не в пикселях).
        """
        rect = pygame.Rect(
            x * TILE_SIZE, 
            y * TILE_SIZE, 
            w * TILE_SIZE, 
            h * TILE_SIZE
        )
        pygame.draw.rect(screen, fill_color, rect)
        pygame.draw.rect(screen, border_color, rect, border_width)
        return rect

    def _draw_text_label(self, screen, text, x_px, y_px, color, font_size=16, bg_color=None):
        """
        Отрисовка текста с опциональной подложкой.
        Координаты передаются в ПИКСЕЛЯХ.
        """
        font = self._get_font(font_size)
        text_surf = font.render(str(text), True, color)
        if bg_color is not None:
            bg_rect = text_surf.get_rect(topleft=(x_px, y_px)).inflate(6, 4)
            pygame.draw.rect(screen, bg_color, bg_rect)
        screen.blit(text_surf, (x_px, y_px))

    def _draw_direction_line(self, screen, cx, cy, dx, dy, color=YELLOW, length=20, width=2):
        """
        Отрисовка линии взгляда из центра клетки в заданном направлении.
        Используется и для игрока, и для NPC.
        """
        # Нормализуем направление (оставляем только -1, 0, 1)
        if dx != 0:
            dx = 1 if dx > 0 else -1
        if dy != 0:
            dy = 1 if dy > 0 else -1
        end_x = cx + dx * length
        end_y = cy + dy * length
        pygame.draw.line(screen, color, (cx, cy), (end_x, end_y), width)

    def _draw_panel_rect(self, screen, rect, fill_alpha=220, border_color=WHITE, border_width=2):
        """
        Рисует полупрозрачную панель с рамкой (для окон диалога, инвентаря и т.п.).
        """
        surf = pygame.Surface((rect.width, rect.height))
        surf.set_alpha(fill_alpha)
        surf.fill(BLACK)
        screen.blit(surf, rect.topleft)
        pygame.draw.rect(screen, border_color, rect, border_width)

    # =========================================================================
    # ОСНОВНОЙ МЕТОД ОТРИСОВКИ
    # =========================================================================
    def render(self, screen):
        """
        Главный метод. Отрисовывает всё в правильном порядке слоёв (z-order):
        1. Карта (тайлы, выходы, контейнеры, дропы)
        2. Точки интереса животных (под картой, чтобы не перекрывали стены)
        3. Животные, NPC, Игрок
        4. UI поверх всего (HUD, диалог, инвентарь, сообщения)
        """
        # Сначала — карта и всё, что на ней
        self._render_map(screen)
        # Затем — UI
        self._render_player(screen)
        self._render_hud(screen)
        self._render_dialog(screen)
        self._render_inventory(screen)
        self._render_temp_message(screen)
        self._render_save_menu(screen)
        self._render_hints(screen)

    # =========================================================================
    # ОТРИСОВКА КАРТЫ (перенесено из world/map.py)
    # =========================================================================
    def _render_map(self, screen):
        """
        Отрисовывает всю текущую карту через специализированные методы.
        # TODO (Шаг 2): сюда будет передаваться camera_x, camera_y для сдвига.
        """
        current_map = self.engine.current_map
        self._render_tiles(screen, current_map)
        self._render_exits(screen, current_map)
        self._render_containers(screen, current_map)
        self._render_drops(screen, current_map)
        self._render_points_of_interest(screen, current_map)
        self._render_animals(screen, current_map)
        self._render_npcs(screen, current_map)

    # -------------------------------------------------------------------------
    # 1. ТАЙЛЫ (пол, стены, двери)
    # -------------------------------------------------------------------------
    def _render_tiles(self, screen, current_map):
        """Отрисовка сетки тайлов с цветами из tiles.json."""
        for y in range(current_map.height):
            for x in range(current_map.width):
                tile = current_map.tiles[y][x]
                prop = current_map.tile_data.get(tile)
                color = tuple(prop["color"]) if prop and "color" in prop else BLACK
                
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, color, rect)
                # Тонкая сетка для читаемости карты
                pygame.draw.rect(screen, BLACK, rect, 1)

    # -------------------------------------------------------------------------
    # 2. ВЫХОДЫ (переходы между локациями)
    # -------------------------------------------------------------------------
    def _render_exits(self, screen, current_map):
        """Зелёные квадраты на выходах из локации."""
        for exit_data in current_map.exits:
            x, y = exit_data.get("x"), exit_data.get("y")
            if x is not None and y is not None:
                self._draw_entity_rect(screen, x, y, 1, 1, EXIT_COLOR, BLACK, 2)

    # -------------------------------------------------------------------------
    # 3. КОНТЕЙНЕРЫ (сундуки, столы)
    # -------------------------------------------------------------------------
    def _render_containers(self, screen, current_map):
        """
        Отрисовка контейнеров с учётом их состояния (заперт/открыт),
        названия сверху и маркера стороны доступа.
        """
        for container in current_map.containers:
            if container.is_destroyed:
                continue
                
            # Цвет зависит от состояния контейнера
            if container.locked:
                color = (150, 50, 0)       # тёмно-красный — заперт
            elif container.is_open:
                color = (180, 120, 50)     # светло-коричневый — открыт
            else:
                color = (120, 80, 30)      # коричневый — закрыт
                
            rect = self._draw_entity_rect(
                screen, 
                container.x, container.y, 
                container.width, container.height, 
                color, BLACK, 2
            )
            
            # Название контейнера сверху
            self._draw_text_label(
                screen, container.name,
                container.x * TILE_SIZE, 
                container.y * TILE_SIZE - 15,
                WHITE, font_size=16
            )
            
            # Маркер стороны доступа (белый кружок с чёрной обводкой)
            if container.access_side != "all":
                cx, cy = rect.centerx, rect.centery
                radius = 4
                # Позиция маркера зависит от стороны доступа
                if container.access_side == "north":
                    marker_pos = (cx, rect.top + 6)
                elif container.access_side == "south":
                    marker_pos = (cx, rect.bottom - 6)
                elif container.access_side == "west":
                    marker_pos = (rect.left + 6, cy)
                elif container.access_side == "east":
                    marker_pos = (rect.right - 6, cy)
                else:
                    marker_pos = None
                    
                if marker_pos:
                    pygame.draw.circle(screen, WHITE, marker_pos, radius)
                    pygame.draw.circle(screen, BLACK, marker_pos, radius, 1)

    # -------------------------------------------------------------------------
    # 4. ДРОПЫ (кучи предметов на земле)
    # -------------------------------------------------------------------------
    def _render_drops(self, screen, current_map):
        """Жёлтые квадраты с количеством предметов внутри."""
        for drop in current_map.drops:
            if drop.is_empty:
                continue
                
            rect = self._draw_entity_rect(
                screen, drop.x, drop.y, 1, 1,
                (255, 255, 100), BLACK, 2
            )
            
            # Количество предметов в куче
            count_text = str(len(drop.items))
            self._draw_text_label(
                screen, count_text,
                drop.x * TILE_SIZE + 18, 
                drop.y * TILE_SIZE + 15,
                BLACK, font_size=14
            )

    # -------------------------------------------------------------------------
    # 5. ТОЧКИ ИНТЕРЕСА ЖИВОТНЫХ
    # -------------------------------------------------------------------------
    def _render_points_of_interest(self, screen, current_map):
        """
        Маркеры еды, сна и игрушек для всех животных.
        Рисуются ДО самих животных, чтобы не перекрывать их.
        """
        for animal in current_map.animals:
            for poi_type, pos in animal.points_of_interest.items():
                if pos is None:
                    continue
                px, py = pos
                color = self._poi_colors.get(poi_type, WHITE)
                label = self._poi_labels.get(poi_type, poi_type)
                
                # Рамка без заливки (толщиной 2 пикселя)
                rect = pygame.Rect(px * TILE_SIZE, py * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, color, rect, 2)
                
                # Подпись внутри клетки
                self._draw_text_label(
                    screen, label,
                    px * TILE_SIZE + 4, 
                    py * TILE_SIZE + 4,
                    color, font_size=14
                )

    # -------------------------------------------------------------------------
    # 6. ЖИВОТНЫЕ
    # -------------------------------------------------------------------------
    def _render_animals(self, screen, current_map):
        """Оранжевые квадраты с цифрами потребностей (сытость/энергия/скука)."""
        for animal in current_map.animals:
            self._draw_entity_rect(
                screen, animal.x, animal.y, 1, 1,
                (255, 180, 100), BLACK, 2
            )
            
            # Потребности одной строкой
            needs_text = f"{animal.hunger} {animal.energy} {animal.boredom}"
            self._draw_text_label(
                screen, needs_text,
                animal.x * TILE_SIZE + 2, 
                animal.y * TILE_SIZE + 18,
                BLACK, font_size=14
            )

    # -------------------------------------------------------------------------
    # 7. NPC
    # -------------------------------------------------------------------------
    def _render_npcs(self, screen, current_map):
        """
        Синие квадраты с именем сверху и линией взгляда.
        Линия взгляда рисуется в сторону текущей цели патруля.
        """
        for npc in current_map.npcs:
            rect = self._draw_entity_rect(
                screen, npc.x, npc.y, 1, 1,
                NPC_COLOR, BLACK, 2
            )
            
            # Имя NPC над головой
            self._draw_text_label(
                screen, npc.name,
                npc.x * TILE_SIZE, 
                npc.y * TILE_SIZE - 15,
                WHITE, font_size=16
            )
            
            # Линия взгляда в сторону цели патруля (если патрулирует)
            if npc.movement != "stationary" and npc.patrol_points:
                target = npc.patrol_points[npc.patrol_index]
                # Поддержка как списка [x, y], так и словаря {"pos": [x, y]}
                if isinstance(target, dict):
                    target_x, target_y = target.get("pos", [npc.x, npc.y])
                else:
                    target_x, target_y = target[0], target[1]
                    
                dx = target_x - npc.x
                dy = target_y - npc.y
                cx = npc.x * TILE_SIZE + TILE_SIZE // 2
                cy = npc.y * TILE_SIZE + TILE_SIZE // 2
                # Используем универсальный хелпер (тот же, что и у игрока)
                self._draw_direction_line(
                    screen, cx, cy, dx, dy,
                    color=(255, 200, 0), length=20, width=2
                )

    # =========================================================================
    # ИГРОК
    # =========================================================================
    def _render_player(self, screen):
        """
        Отрисовка игрока: зелёный квадрат + жёлтая линия направления.
        FIX (#6): направление берётся из player.facing (единый источник).
        """
        game_state = self.engine.game_state
        px, py = game_state.player.x, game_state.player.y
        
        # Сам игрок
        pygame.draw.rect(
            screen, GREEN, 
            (px * TILE_SIZE, py * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        )
        
        # Линия взгляда через универсальный хелпер
        cx = px * TILE_SIZE + TILE_SIZE // 2
        cy = py * TILE_SIZE + TILE_SIZE // 2
        dx, dy = game_state.player.get_facing_delta()
        self._draw_direction_line(screen, cx, cy, dx, dy, YELLOW, 20, 3)

    # =========================================================================
    # HUD (ВЕРХНЯЯ ПАНЕЛЬ)
    # =========================================================================
    def _render_hud(self, screen):
        game_state = self.engine.game_state
        font = self._get_font(24)
        
        info = font.render(
            f"Класс: {game_state.player.player_class}  |  "
            f"Дней: {game_state.days_left}  |  "
            f"Человечность: {game_state.humanity}",
            True, WHITE
        )
        screen.blit(info, (10, 10))
        
        # Подсказка зависит от состояния диалога
        if not game_state.dialog_active:
            help_text = font.render("E — открыть дверь / говорить с NPC", True, WHITE)
        else:
            help_text = font.render("E/ESC — закрыть диалог", True, WHITE)
        screen.blit(help_text, (10, 40))

    # =========================================================================
    # ДИАЛОГ
    # =========================================================================
    def _render_dialog(self, screen):
        game_state = self.engine.game_state
        if not game_state.dialog_active:
            return
            
        font = self._get_font(24)
        panel_rect = pygame.Rect(50, HEIGHT - 210, WIDTH - 100, 160)
        self._draw_panel_rect(screen, panel_rect, fill_alpha=220)
        
        # Текст диалога (многострочный, но с лимитом)
        for i, line in enumerate(game_state.dialog_text.split('\n')):
            if i * 25 < 100:
                screen.blit(
                    font.render(line[:65], True, WHITE), 
                    (55, HEIGHT - 200 + i * 25)
                )
                
        # Варианты ответов
        for i, opt in enumerate(game_state.dialog_options):
            screen.blit(
                font.render(f"{i+1}. {opt['text']}", True, GREEN), 
                (55, HEIGHT - 110 + i * 25)
            )
            
        # Подсказка, если вариантов нет
        if not game_state.dialog_options:
            hint = font.render("Нажми E или ESC, чтобы продолжить", True, (150, 150, 150))
            screen.blit(hint, (55, HEIGHT - 85))

    # =========================================================================
    # ИНВЕНТАРЬ
    # =========================================================================
    def _render_inventory(self, screen):
        """Отрисовка окна инвентаря."""
        if not self.engine.inventory_open:
            return
            
        panel_rect = pygame.Rect(100, 100, WIDTH - 200, HEIGHT - 200)
        self._draw_panel_rect(screen, panel_rect, fill_alpha=230, border_width=3)
        
        title_font = self._get_font(36)
        item_font = self._get_font(24)
        
        screen.blit(title_font.render("Инвентарь", True, YELLOW), (120, 120))
        
        items = self.engine.game_state.inventory.get_items()
        if not items:
            screen.blit(
                item_font.render("(пусто)", True, (150, 150, 150)), 
                (120, 170)
            )
        else:
            for i, item_id in enumerate(items):
                if i >= 15:
                    break
                # Показываем человекочитаемое имя из items.json
                item_prop = self.item_data.get(item_id, {}) or {}
                item_name = item_prop.get("name", item_id)
                screen.blit(
                    item_font.render(f"{i+1}. {item_name}", True, WHITE), 
                    (120, 170 + i * 30)
                )
                
        # Текущий вес
        inv = self.engine.game_state.inventory
        weight_text = f"Вес: {inv.get_total_weight():.1f} / {inv.max_weight:.1f} кг"
        screen.blit(item_font.render(weight_text, True, WHITE), (120, HEIGHT - 160))
        screen.blit(
            item_font.render("Нажми I, чтобы закрыть", True, (150, 150, 150)), 
            (120, HEIGHT - 130)
        )

    # =========================================================================
    # ВРЕМЕННОЕ СООБЩЕНИЕ (всплывающие уведомления)
    # =========================================================================
    def _render_temp_message(self, screen):
        if not self.engine.temp_message:
            return
        current_time = pygame.time.get_ticks()
        if current_time - self.engine.temp_message_timer < 2000:
            font = self._get_font(28)
            text_surf = font.render(self.engine.temp_message, True, WHITE)
            text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT - 100))
            bg_rect = text_rect.inflate(20, 10)
            pygame.draw.rect(screen, BLACK, bg_rect)
            pygame.draw.rect(screen, WHITE, bg_rect, 2)
            screen.blit(text_surf, text_rect)
        else:
            self.engine.temp_message = None

    # =========================================================================
    # МЕНЮ СОХРАНЕНИЙ
    # =========================================================================
    def _render_save_menu(self, screen):
        if not self.engine.save_menu_open:
            return
            
        # Затемнение фона
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        
        box = pygame.Rect(WIDTH // 2 - 250, 100, 500, 450)
        pygame.draw.rect(screen, BLACK, box)
        pygame.draw.rect(screen, WHITE, box, 3)
        
        title_font = self._get_font(36)
        item_font = self._get_font(26)
        hint_font = self._get_font(20)
        
        title_text = "Сохранить игру" if self.engine.save_menu_mode == "save" else "Загрузить игру"
        screen.blit(title_font.render(title_text, True, YELLOW), (box.x + 20, box.y + 20))
        
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
                
        # Подсказки управления
        if self.engine.save_menu_mode == "save":
            hint = "Enter — создать новое сохранение (автономер)"
        else:
            hint = "Enter — загрузить выбранное"
        screen.blit(hint_font.render(hint, True, (180, 180, 180)), 
                    (box.x + 20, box.y + box.height - 60))
        screen.blit(hint_font.render("ESC — закрыть", True, (180, 180, 180)), 
                    (box.x + 20, box.y + box.height - 30))

    # =========================================================================
    # ПОДСКАЗКИ УПРАВЛЕНИЯ (внизу экрана)
    # =========================================================================
    def _render_hints(self, screen):
        help_font = self._get_font(20)
        hint = help_font.render(
            "WASD/стрелки — движение | E — взаимодействие | I — инвентарь | "
            "F5 — сохранить | F9 — загрузить | ESC — меню",
            True, (180, 180, 180)
        )
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 15)))