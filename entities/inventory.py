# entities/inventory.py
from world.item_data import ItemData

class Inventory:
    def __init__(self):
        self.items = []
        self.max_weight = 50.0  # Пока фиксированный лимит
        self.item_data = ItemData()

    def add_item(self, item_id):
        mass = self.item_data.get_mass(item_id)
        if self.get_total_weight() + mass > self.max_weight:
            return False  # Не влезает
        self.items.append(item_id)
        return True

    def remove_item(self, item_id):
        if item_id in self.items:
            self.items.remove(item_id)
            return True
        return False

    def has_item(self, item_id):
        return item_id in self.items

    def get_items(self):
        return self.items.copy()

    def get_total_weight(self):
        total = 0.0
        for item_id in self.items:
            total += self.item_data.get_mass(item_id)
        return total

    def is_empty(self):
        return len(self.items) == 0