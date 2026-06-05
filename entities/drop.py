# entities/drop.py

class ItemDrop:
    """Куча предметов на земле. Может содержать один или несколько предметов."""

    def __init__(self, drop_id, x, y, items=None):
        """
        Аргументы:
            drop_id (str): Уникальный идентификатор кучи (например, "drop_001").
            x, y (int): Координаты на карте.
            items (list): Список ID предметов (например, ["key_01", "apple"]).
        """
        self.id = drop_id
        self.x = x
        self.y = y
        self.items = items if items is not None else []
        self.is_empty = False  # Станет True, когда все предметы подобраны

    def is_empty(self):
        """Возвращает True, если в куче больше нет предметов."""
        return len(self.items) == 0

    def take_item(self, item_id):
        """Забирает предмет из кучи. Возвращает предмет или None, если его нет."""
        if item_id in self.items:
            self.items.remove(item_id)
            return item_id
        return None

    def add_item(self, item_id):
        """Добавляет предмет в кучу (например, игрок выбросил)."""
        self.items.append(item_id)

    def get_items(self):
        """Возвращает копию списка предметов."""
        return self.items.copy()