# entities/container.py
class Container:
    def __init__(self, container_id, x, y, name="Ящик", locked=False, items=None):
        self.id = container_id
        self.x = x
        self.y = y
        self.name = name
        self.locked = locked
        self.items = items if items else []  # список ID предметов
        self.is_open = False
        self.is_destroyed = False
        # Для будущих текстур
        self.facing = (0, 0)  # направление (если у стены)

    def open(self):
        if self.locked:
            return "locked"
        self.is_open = True
        return "opened"

    def close(self):
        self.is_open = False

    def add_item(self, item_id):
        self.items.append(item_id)

    def remove_item(self, item_id):
        if item_id in self.items:
            self.items.remove(item_id)
            return item_id
        return None

    def get_items(self):
        return self.items.copy()