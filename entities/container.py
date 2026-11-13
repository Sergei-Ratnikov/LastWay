# entities/container.py

class Container:
    def __init__(self, container_id, x, y, name="Ящик", locked=False, items=None, width=1, height=1, access_side="all"):
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
        self.access_side = access_side  # "all", "north", "south", "east", "west"

    def get_occupied_cells(self):
        cells = []
        for dy in range(self.height):
            for dx in range(self.width):
                cells.append((self.x + dx, self.y + dy))
        return cells

    def occupies(self, x, y):
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

    def can_interact_from(self, player_x, player_y):
        """
        Проверяет, может ли игрок в клетке (player_x, player_y) взаимодействовать с контейнером.
        """
        if self.access_side == "all":
            return True

        # Для односторонних проверяем, что игрок стоит с нужной стороны от любой клетки контейнера
        if self.access_side == "north":
            # Игрок должен быть над контейнером (y меньше), и по x в диапазоне контейнера
            return (player_y == self.y - 1 and self.x <= player_x < self.x + self.width)
        if self.access_side == "south":
            return (player_y == self.y + self.height and self.x <= player_x < self.x + self.width)
        if self.access_side == "west":
            return (player_x == self.x - 1 and self.y <= player_y < self.y + self.height)
        if self.access_side == "east":
            return (player_x == self.x + self.width and self.y <= player_y < self.y + self.height)
        return False

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