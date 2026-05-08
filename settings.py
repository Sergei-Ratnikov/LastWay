# settings.py
import os

WIDTH = 1024
HEIGHT = 768
TILE_SIZE = 48

# Задержка между шагами (в миллисекундах) — чем больше, тем медленнее герой
MOVE_DELAY_MS = 150  # 150 мс = ~6-7 шагов в секунду

# Цвета
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (200, 0, 0)
BROWN = (139, 69, 19)
LIGHT_GREY = (150, 150, 150)
DARK_GREY = (40, 40, 40)
YELLOW = (255, 215, 0)
BLUE = (0, 0, 255)
NPC_COLOR = (0, 150, 200)

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MAPS_DIR = os.path.join(DATA_DIR, "maps")
NPCS_DIR = os.path.join(DATA_DIR, "npcs")
DIALOGS_DIR = os.path.join(DATA_DIR, "dialogs")
