# ui/main_menu_ui.py
# =============================================================================
# ГЛАВНОЕ МЕНЮ (MAIN MENU)
# Отдельный модуль, инкапсулирующий стартовое меню игры.
# Запускается ДО создания GameEngine, возвращает выбор игрока.
#
# Архитектурная роль:
# - main.py создаёт MainMenu и получает результат ("new_game" / ("load_game", name) / "exit")
# - В зависимости от результата создаётся GameEngine и начинается игра
# - GameEngine и Renderer не знают о существовании главного меню
#
# Поведение:
# - Показывает фоновое изображение (assets/images/main_menu_bg.png)
# - Три кнопки слева: Новая игра, Загрузить, Выйти
# - При выборе "Загрузить" — переключается в режим списка сохранений
# - Управление: стрелки ↑↓, Enter для выбора, ESC для выхода/назад
# =============================================================================

import pygame
import os
import sys
from settings import WIDTH, HEIGHT, BLACK, WHITE, YELLOW

# Путь к фоновому изображению (относительно корня проекта)
BG_IMAGE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "images", "main_menu_bg.png"
)

# Путь к папке сохранений
SAVES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "saves"
)


class MainMenu:
    """
    Главное меню игры.
    
    Состояния:
        mode (str): "main" — главное меню, "load" — список сохранений
        selected_index (int): индекс выбранного пункта
    
    Возвращаемые значения метода run():
        - "new_game" — начать новую игру
        - ("load_game", save_name) — загрузить сохранение
        - "exit" — выйти из игры
    """
    
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        
        # Состояние меню
        self.mode = "main"
        self.selected_index = 0
        
        # Загружаем фоновое изображение (или None, если файла нет)
        self.bg_image = self._load_background()
        
        # Кэш шрифтов
        self._fonts = {}
        
        # Пункты главного меню
        self.main_items = ["Новая игра", "Загрузить", "Выйти"]
        
        # Список сохранений (заполняется при входе в режим load)
        self.save_names = []
    
    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================
    
    def _get_font(self, size: int):
        """Возвращает шрифт заданного размера из кэша."""
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]
    
    def _load_background(self):
        """
        Пытается загрузить фоновое изображение.
        Возвращает Surface или None, если файла нет.
        """
        if os.path.exists(BG_IMAGE_PATH):
            try:
                image = pygame.image.load(BG_IMAGE_PATH)
                # Растягиваем на весь экран (пока без умного масштабирования)
                return pygame.transform.scale(image, (WIDTH, HEIGHT))
            except Exception as e:
                print(f"MainMenu: не удалось загрузить фон {BG_IMAGE_PATH}: {e}")
        return None
    
    def _load_save_names(self):
        """Читает список сохранений из папки saves/."""
        if not os.path.isdir(SAVES_DIR):
            return []
        files = [f for f in os.listdir(SAVES_DIR) if f.endswith(".json")]
        # Убираем расширение .json
        return sorted([f[:-5] for f in files])
    
    def _get_current_items(self) -> list:
        """Возвращает список пунктов для текущего режима."""
        if self.mode == "main":
            return self.main_items
        else:  # mode == "load"
            # Список сохранений + кнопка "Назад"
            items = list(self.save_names)
            if not items:
                items = ["(нет сохранений)"]
            items.append("← Назад")
            return items
    
    # =========================================================================
    # ГЛАВНЫЙ ЦИКЛ МЕНЮ
    # =========================================================================
    
    def run(self):
        """
        Запускает цикл главного меню.
        
        Возвращает:
            - "new_game" — начать новую игру
            - ("load_game", save_name) — загрузить сохранение
            - "exit" — выйти из игры
        """
        running = True
        while running:
            self.clock.tick(60)
            
            # --- ОБРАБОТКА СОБЫТИЙ ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "exit"
                
                if event.type == pygame.KEYDOWN:
                    result = self._handle_key(event.key)
                    if result is not None:
                        return result
            
            # --- ОТРИСОВКА ---
            self._render()
            pygame.display.flip()
    
    # =========================================================================
    # ОБРАБОТКА ВВОДА
    # =========================================================================
    
    def _handle_key(self, key) -> str | tuple | None:
        """
        Обрабатывает нажатие клавиши.
        Возвращает результат ("new_game", "exit" и т.п.) или None.
        """
        items = self._get_current_items()
        
        # --- NAVIGATION: ↑ ↓ ---
        if key == pygame.K_UP:
            self.selected_index = max(0, self.selected_index - 1)
            return None
        if key == pygame.K_DOWN:
            self.selected_index = min(len(items) - 1, self.selected_index + 1)
            return None
        
        # --- ESC ---
        if key == pygame.K_ESCAPE:
            if self.mode == "load":
                # Возвращаемся в главное меню
                self.mode = "main"
                self.selected_index = 0
                return None
            else:  # mode == "main"
                # Выход из игры
                return "exit"
        
        # --- ENTER / SPACE ---
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.mode == "main":
                return self._handle_main_selection()
            else:  # mode == "load"
                return self._handle_load_selection()
        
        return None
    
    def _handle_main_selection(self):
        """Обработка выбора в главном меню."""
        choice = self.main_items[self.selected_index]
        
        if choice == "Новая игра":
            return "new_game"
        elif choice == "Загрузить":
            # Переходим в режим выбора сохранения
            self.mode = "load"
            self.save_names = self._load_save_names()
            self.selected_index = 0
            return None
        elif choice == "Выйти":
            return "exit"
        
        return None
    
    def _handle_load_selection(self):
        """Обработка выбора в списке сохранений."""
        items = self._get_current_items()
        choice = items[self.selected_index]
        
        if choice == "← Назад":
            self.mode = "main"
            self.selected_index = 0
            return None
        
        if choice == "(нет сохранений)":
            return None
        
        # Это имя сохранения
        return ("load_game", choice)
    
    # =========================================================================
    # ОТРИСОВКА
    # =========================================================================
    
    def _render(self):
        """Отрисовывает меню."""
        # --- 1. ФОН ---
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            # Fallback: тёмный градиент (нет изображения)
            self.screen.fill((20, 15, 10))
            # Полупрозрачный тёмный оверлей для читаемости текста
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(180)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))
        
        # --- 2. КНОПКИ СЛЕВА ---
        items = self._get_current_items()
        
        # Позиция первой кнопки (слева, по вертикали — по центру группы)
        button_x = 50
        button_height = 50
        button_spacing = 15
        total_height = len(items) * button_height + (len(items) - 1) * button_spacing
        start_y = HEIGHT // 2 - total_height // 2
        
        font = self._get_font(32)
        button_width = 200
        
        for i, item_text in enumerate(items):
            y = start_y + i * (button_height + button_spacing)
            is_selected = (i == self.selected_index)
            
            # Прямоугольник кнопки (полупрозрачный)
            button_rect = pygame.Rect(button_x, y, button_width, button_height)
            
            # Фон кнопки
            if is_selected:
                bg_color = (60, 50, 20, 220)   # Тёмно-жёлтый для выбранной
            else:
                bg_color = (0, 0, 0, 180)      # Почти чёрный для остальных
            
            # Полупрозрачная поверхность
            button_surf = pygame.Surface((button_width, button_height), pygame.SRCALPHA)
            button_surf.fill(bg_color)
            self.screen.blit(button_surf, button_rect)
            
            # Рамка
            if is_selected:
                pygame.draw.rect(self.screen, YELLOW, button_rect, 3)
            else:
                pygame.draw.rect(self.screen, (100, 100, 100), button_rect, 2)
            
            # Маркер выбора (слева от текста)
            if is_selected:
                marker = font.render(">>", True, YELLOW)
                self.screen.blit(marker, (button_x + 15, y + button_height // 2 - marker.get_height() // 2))
            
            # Текст пункта меню
            text_color = YELLOW if is_selected else WHITE
            text_surf = font.render(item_text, True, text_color)
            # Текст с отступом от маркера (или от края, если не выбран)
            text_x = button_x + 50 if is_selected else button_x + 25
            text_y = y + button_height // 2 - text_surf.get_height() // 2
            self.screen.blit(text_surf, (text_x, text_y))
        
        # --- 3. ПОДСКАЗКИ УПРАВЛЕНИЯ ВНИЗУ ---
        hint_font = self._get_font(20)
        if self.mode == "main":
            hint_text = "↑ ↓ — выбор   |   Enter — подтвердить   |   ESC — выйти"
        else:
            hint_text = "↑ ↓ — выбор   |   Enter — загрузить   |   ESC — назад"
        hint_surf = hint_font.render(hint_text, True, (180, 180, 180))
        self.screen.blit(hint_surf, (WIDTH // 2 - hint_surf.get_width() // 2, HEIGHT - 30))