# objects/container.py
# =============================================================================
# КОНТЕЙНЕР
# Объект мира, в котором хранятся предметы. Может быть открыт/закрыт, заперт.
# Может занимать несколько клеток и иметь сторону доступа.
# =============================================================================

class Container:
    """
    Контейнер (сундук, стол, шкаф и т.д.).
    Хранит предметы, может быть открыт/закрыт, заперт.
    """
    
    def __init__(self, container_id, x, y, name="Ящик", locked=False, items=None, 
                 width=1, height=1, access_side="all"):
        """
        Инициализация контейнера.
        
        Аргументы:
            container_id (str): Уникальный идентификатор.
            x, y (int): Координаты на карте.
            name (str): Отображаемое имя.
            locked (bool): Заперт ли контейнер.
            items (list): Список ID предметов внутри.
            width, height (int): Размеры контейнера (в клетках).
            access_side (str): Сторона доступа ("all", "north", "south", "east", "west").
        """
        self.id = container_id
        self.x = x
        self.y = y
        self.name = name
        self.locked = locked
        self.items = items if items else []
        self.is_open = False
        self.is_destroyed = False
        self.width = width
        self.height = height
        self.facing = (0, 0)
        self.access_side = access_side
    
    def get_occupied_cells(self):
        """Возвращает список клеток, которые занимает контейнер."""
        cells = []
        for dy in range(self.height):
            for dx in range(self.width):
                cells.append((self.x + dx, self.y + dy))
        return cells
    
    def occupies(self, x, y):
        """Проверяет, занимает ли контейнер клетку (x, y)."""
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height
    
    def can_interact_from(self, player_x, player_y):
        """
        Проверяет, может ли игрок в клетке (player_x, player_y) взаимодействовать с контейнером.
        Учитывает access_side.
        """
        if self.access_side == "all":
            return True
        
        # Для односторонних проверяем, что игрок стоит с нужной стороны
        if self.access_side == "north":
            return (player_y == self.y - 1 and self.x <= player_x < self.x + self.width)
        if self.access_side == "south":
            return (player_y == self.y + self.height and self.x <= player_x < self.x + self.width)
        if self.access_side == "west":
            return (player_x == self.x - 1 and self.y <= player_y < self.y + self.height)
        if self.access_side == "east":
            return (player_x == self.x + self.width and self.y <= player_y < self.y + self.height)
        
        return False
    
    def open(self):
        """Открывает контейнер. Возвращает "locked" если заперт, иначе "opened"."""
        if self.locked:
            return "locked"
        self.is_open = True
        return "opened"
    
    def close(self):
        """Закрывает контейнер."""
        self.is_open = False
    
    def add_item(self, item_id):
        """Добавляет предмет в контейнер."""
        self.items.append(item_id)
    
    def remove_item(self, item_id):
        """Удаляет предмет из контейнера. Возвращает предмет или None."""
        if item_id in self.items:
            self.items.remove(item_id)
            return item_id
        return None
    
    def get_items(self):
        """Возвращает копию списка предметов."""
        return self.items.copy()