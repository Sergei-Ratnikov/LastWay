# ui/document_viewer_ui.py
# =============================================================================
# ОКНО ПРОСМОТРА ДОКУМЕНТОВ (DOCUMENT VIEWER)
# Отдельный модуль для отображения текста документов.
# Поддерживает многострочный текст с \n и автоперенос длинных строк.
# =============================================================================

import pygame
from settings import WIDTH, HEIGHT, BLACK, WHITE, YELLOW
from logger import log


class DocumentViewer:
    """
    Модальное окно для чтения документов.
    
    Состояние:
        is_active (bool): Открыто ли окно.
        title (str): Заголовок документа (имя предмета).
        lines (list[str]): Разбитые по строкам абзацы текста.
        scroll_offset (int): Текущая позиция прокрутки (индекс первой видимой строки).
    """
    
    def __init__(self):
        self.is_active = False
        self.title = ""
        self.lines = []
        self.scroll_offset = 0
        
        # Параметры отображения
        self.max_visible_lines = 15  # Сколько строк помещается на экране
        self.chars_per_line = 70     # Символов в строке (для автопереноса)
        
        # Кэш шрифтов
        self._fonts = {}
    
    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================
    
    def _get_font(self, size: int):
        """Возвращает шрифт заданного размера из кэша."""
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]
    
    def _wrap_text(self, text: str) -> list[str]:
        """
        Разбивает текст на строки с учётом \n и автопереноса.
        
        Алгоритм:
            1. Разделяем по \n (абзацы).
            2. Каждый абзац разбиваем на строки по chars_per_line.
            3. Пустые строки сохраняем (для визуального разделения абзацев).
        
        Возвращает:
            list[str]: Список строк для отображения.
        """
        result = []
        paragraphs = text.split('\n')
        
        for para in paragraphs:
            if not para.strip():
                # Пустая строка (разделитель абзацев)
                result.append("")
                continue
            
            # Разбиваем длинный абзац на строки
            words = para.split()
            current_line = ""
            
            for word in words:
                # Проверяем, влезает ли слово в текущую строку
                if current_line:
                    test_line = current_line + " " + word
                else:
                    test_line = word
                
                if len(test_line) <= self.chars_per_line:
                    current_line = test_line
                else:
                    # Текущая строка заполнена, сохраняем и начинаем новую
                    if current_line:
                        result.append(current_line)
                    current_line = word
            
            # Добавляем последнюю строку абзаца
            if current_line:
                result.append(current_line)
        
        return result
    
    # =========================================================================
    # ОТКРЫТИЕ / ЗАКРЫТИЕ
    # =========================================================================
    
    def open(self, text: str, title: str = "Документ"):
        """
        Открывает окно с текстом документа.
        
        Аргументы:
            text (str): Текст документа (поддерживает \n).
            title (str): Заголовок окна (имя предмета).
        """
        self.title = title
        self.lines = self._wrap_text(text)
        self.scroll_offset = 0
        self.is_active = True
        log.info(f"DOCUMENT_VIEWER: открыт '{title}', строк={len(self.lines)}")
    
    def close(self):
        """Закрывает окно."""
        log.info(f"DOCUMENT_VIEWER: закрыт '{self.title}'")
        self.is_active = False
        self.title = ""
        self.lines = []
        self.scroll_offset = 0
    
    # =========================================================================
    # ОБРАБОТКА ВВОДА
    # =========================================================================
    
    def handle_event(self, event) -> bool:
        """
        Обрабатывает событие pygame, когда окно открыто.
        
        Возвращает:
            bool: True, если событие обработано.
        """
        if event.type != pygame.KEYDOWN:
            return False
        
        # --- ESC / Enter / Space: закрыть окно ---
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
            self.close()
            return True
        
        # --- ↑: прокрутка вверх ---
        if event.key == pygame.K_UP:
            self.scroll_offset = max(0, self.scroll_offset - 1)
            return True
        
        # --- ↓: прокрутка вниз ---
        if event.key == pygame.K_DOWN:
            max_scroll = max(0, len(self.lines) - self.max_visible_lines)
            self.scroll_offset = min(max_scroll, self.scroll_offset + 1)
            return True
        
        # --- PageUp: прокрутка на страницу вверх ---
        if event.key == pygame.K_PAGEUP:
            self.scroll_offset = max(0, self.scroll_offset - self.max_visible_lines)
            return True
        
        # --- PageDown: прокрутка на страницу вниз ---
        if event.key == pygame.K_PAGEDOWN:
            max_scroll = max(0, len(self.lines) - self.max_visible_lines)
            self.scroll_offset = min(max_scroll, self.scroll_offset + self.max_visible_lines)
            return True
        
        # Любая другая клавиша — игнорируем (но событие считаем обработанным)
        return True
    
    # =========================================================================
    # ОТРИСОВКА
    # =========================================================================
    
    def render(self, screen):
        """
        Отрисовывает окно просмотра документа поверх карты.
        Вызывается из GameEngine.render() после основного рендера.
        """
        if not self.is_active:
            return
        
        # --- 1. ЗАТЕМНЕНИЕ ФОНА ---
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(200)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        
        # --- 2. РАЗМЕРЫ И ПОЗИЦИИ ---
        box_width = 800
        box_height = 550
        box_x = WIDTH // 2 - box_width // 2
        box_y = HEIGHT // 2 - box_height // 2
        
        box_rect = pygame.Rect(box_x, box_y, box_width, box_height)
        pygame.draw.rect(screen, BLACK, box_rect)
        pygame.draw.rect(screen, YELLOW, box_rect, 3)
        
        # --- 3. ЗАГОЛОВОК ---
        title_font = self._get_font(28)
        title_surf = title_font.render(self.title, True, YELLOW)
        title_x = box_x + (box_width - title_surf.get_width()) // 2
        screen.blit(title_surf, (title_x, box_y + 15))
        
        # Разделительная линия
        pygame.draw.line(
            screen, YELLOW,
            (box_x + 20, box_y + 50),
            (box_x + box_width - 20, box_y + 50),
            2
        )
        
        # --- 4. ТЕКСТ ДОКУМЕНТА ---
        text_font = self._get_font(22)
        text_x = box_x + 30
        text_y_start = box_y + 70
        line_height = 30
        
        # Вычисляем диапазон видимых строк
        start_line = self.scroll_offset
        end_line = min(start_line + self.max_visible_lines, len(self.lines))
        
        for i in range(start_line, end_line):
            line = self.lines[i]
            y = text_y_start + (i - start_line) * line_height
            
            if line:
                # Обычная строка текста
                line_surf = text_font.render(line, True, WHITE)
            else:
                # Пустая строка (разделитель абзацев) — рисуем невидимую
                line_surf = text_font.render("", True, WHITE)
            
            screen.blit(line_surf, (text_x, y))
        
        # --- 5. ИНДИКАТОРЫ ПРОКРУТКИ ---
        hint_font = self._get_font(18)
        
        # Стрелка вверх (если можно прокрутить)
        if self.scroll_offset > 0:
            up_arrow = hint_font.render("▲", True, (150, 150, 150))
            screen.blit(up_arrow, (box_x + box_width // 2 - up_arrow.get_width() // 2, box_y + 55))
        
        # Стрелка вниз (если можно прокрутить)
        max_scroll = max(0, len(self.lines) - self.max_visible_lines)
        if self.scroll_offset < max_scroll:
            down_arrow = hint_font.render("▼", True, (150, 150, 150))
            screen.blit(down_arrow, (box_x + box_width // 2 - down_arrow.get_width() // 2, box_y + box_height - 55))
        
        # --- 6. ПОДСКАЗКИ УПРАВЛЕНИЯ ---
        hint_text = "↑ ↓ — прокрутка   |   Enter / ESC — закрыть"
        hint_surf = hint_font.render(hint_text, True, (180, 180, 180))
        hint_x = box_x + (box_width - hint_surf.get_width()) // 2
        hint_y = box_y + box_height - 25
        screen.blit(hint_surf, (hint_x, hint_y))