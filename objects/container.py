# objects/container.py
# =============================================================================
# КОНТЕЙНЕР
# Объект мира, в котором хранятся предметы. Может быть открыт/закрыт, заперт.
# Может занимать несколько клеток и иметь сторону доступа.
# =============================================================================

from objects.item import Item
from logger import log


class Container:
    """
    Контейнер (сундук, стол, шкаф и т.д.).
    Хранит объекты Item, может быть открыт/закрыт, заперт.
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
            items (list[Item]): Список объектов Item внутри.
            width, height (int): Размеры контейнера (в клетках).
            access_side (str): Сторона доступа ("all", "north", "south", "east", "west").
        """
        self.id = container_id
        self.x = x
        self.y = y
        self.name = name
        self.locked = locked
        # Список объектов Item (не строк!)
        self.items: list[Item] = items if items else []
        self.is_open = False
        self.is_destroyed = False
        self.width = width
        self.height = height
        self.facing = (0, 0)
        self.access_side = access_side
    
    # =========================================================================
    # ГЕОМЕТРИЯ
    # =========================================================================
    
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
        if self.access_side == "north":
            return (player_y == self.y - 1 and self.x <= player_x < self.x + self.width)
        if self.access_side == "south":
            return (player_y == self.y + self.height and self.x <= player_x < self.x + self.width)
        if self.access_side == "west":
            return (player_x == self.x - 1 and self.y <= player_y < self.y + self.height)
        if self.access_side == "east":
            return (player_x == self.x + self.width and self.y <= player_y < self.y + self.height)
        return False
    
    # =========================================================================
    # ОТКРЫТИЕ / ЗАКРЫТИЕ
    # =========================================================================
    
    def open(self):
        """Открывает контейнер. Возвращает "locked" если заперт, иначе "opened"."""
        if self.locked:
            return "locked"
        self.is_open = True
        return "opened"
    
    def close(self):
        """Закрывает контейнер."""
        self.is_open = False
    
    # =========================================================================
    # РАБОТА С ПРЕДМЕТАМИ
    # =========================================================================
    
    def add_item(self, item: Item):
        """
        Добавляет предмет в контейнер.
        
        Аргументы:
            item (Item): Экземпляр предмета для добавления.
        """
        self.items.append(item)
        log.info(f"КОНТЕЙНЕР: в {self.name} добавлен {item.name}")
    
    def remove_item(self, item: Item) -> Item | None:
        """
        Удаляет конкретный экземпляр предмета из контейнера.
        
        Аргументы:
            item (Item): Экземпляр предмета для удаления.
            
        Возвращает:
            Item | None: Удалённый предмет или None.
        """
        if item in self.items:
            self.items.remove(item)
            log.info(f"КОНТЕЙНЕР: из {self.name} удалён {item.name}")
            return item
        return None
    
    def remove_item_by_id(self, item_id: str) -> Item | None:
        """
        Удаляет первый найденный предмет с указанным ID.
        
        Аргументы:
            item_id (str): ID предмета.
            
        Возвращает:
            Item | None: Удалённый предмет или None.
        """
        for item in self.items:
            if item.id == item_id:
                self.items.remove(item)
                return item
        return None
    
    def get_items(self) -> list[Item]:
        """Возвращает копию списка предметов."""
        return self.items.copy()
    
    # =========================================================================
    # СЕРИАЛИЗАЦИЯ
    # =========================================================================
    
    def items_to_dict_list(self) -> list[dict]:
        """Сериализует предметы контейнера в список словарей."""
        return [item.to_dict() for item in self.items]
    
    def load_items_from_dict_list(self, data_list: list[dict]):
        """Загружает предметы из списка словарей."""
        self.items.clear()
        for item_dict in data_list:
            try:
                from objects.item import Item
                item = Item.from_dict(item_dict)
                self.items.append(item)
            except Exception as e:
                log.error(f"КОНТЕЙНЕР: ошибка загрузки предмета: {e}")