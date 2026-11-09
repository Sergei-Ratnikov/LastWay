# logger.py
import logging
import os

def setup_logger():
    """Настраивает логирование в файл game_log.txt"""
    # Создаем логгер
    logger = logging.getLogger("LastWay")
    logger.setLevel(logging.DEBUG)

    # Если логгер уже настроен, не добавляем обработчики повторно
    if logger.handlers:
        return logger

    # Путь к файлу лога (в корне проекта)
    log_file = "game_log.txt"

    # Формат: [Время] [Уровень] Сообщение
    formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S')

    # Обработчик для записи в файл
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setFormatter(formatter)

    # Добавляем обработчик в логгер
    logger.addHandler(file_handler)

    return logger

# Создаем и экспортируем логгер
log = setup_logger()