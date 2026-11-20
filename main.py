# main.py
# =============================================================================
# ТОЧКА ВХОДА В ИГРУ
# Дирижёр: запускает главное меню, затем создаёт GameEngine.
# =============================================================================

import sys
import os
import pygame

# Добавляем корень проекта в sys.path (на случай запуска из другого места)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from logger import log
from game_engine import GameEngine
from game_state import GameState


def main():
    """Главная функция: показывает меню, затем запускает игру."""
    log.info("=" * 60)
    log.info("ЗАПУСК ИГРЫ: Last Way")
    log.info("=" * 60)
    
    # --- 1. ИНИЦИАЛИЗИРУЕМ PYGAME ---
    pygame.init()
    from settings import WIDTH, HEIGHT
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("The Last Way")
    
    # --- 2. ПОКАЗЫВАЕМ ГЛАВНОЕ МЕНЮ ---
    from ui.main_menu_ui import MainMenu
    menu = MainMenu(screen)
    result = menu.run()
    
    # --- 3. ОБРАБАТЫВАЕМ ВЫБОР ИГРОКА ---
    if result == "exit":
        log.info("МЕНЮ: игрок выбрал 'Выйти'")
        pygame.quit()
        return
    
    # Определяем стартовую локацию (пока хардкод 001_hospital)
    start_location_id = "001_hospital"
    
    if result == "new_game":
        log.info("МЕНЮ: игрок выбрал 'Новая игра'")
        # Создаём движок с нуля
        game_state = GameState()
        engine = GameEngine(start_location_id, game_state)
    
    elif isinstance(result, tuple) and result[0] == "load_game":
        save_name = result[1]
        log.info(f"МЕНЮ: игрок выбрал 'Загрузить' — {save_name}")
        # Создаём движок и сразу загружаем сохранение
        game_state = GameState()
        engine = GameEngine(start_location_id, game_state)
        if not engine.save_system.load(save_name):
            log.error(f"МЕНЮ: не удалось загрузить сохранение '{save_name}'")
            pygame.quit()
            return
    
    else:
        log.error(f"МЕНЮ: неизвестный результат '{result}'")
        pygame.quit()
        return
    
    # --- 4. ЗАПУСКАЕМ ИГРОВОЙ ЦИКЛ ---
    exit_code = engine.run()
    log.info(f"ИГРА: завершена с кодом '{exit_code}'")
    
    pygame.quit()


if __name__ == "__main__":
    main()