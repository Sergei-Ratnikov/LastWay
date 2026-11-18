# objects/inventory.py
# =============================================================================
# ИНВЕНТАРЬ
# Логика хранения предметов игрока.
# Считает вес, проверяет лимиты, добавляет/удаляет предметы.
# =============================================================================

from world.item_data import ItemData


class Inventory:
    """
    Инвентарь игрока.
    Хранит список предметов, считает вес, проверяет лимиты.
    """
    
    def __init__(self):
        """Инициализация инвентаря."""
        self.items = []
        self.max_weight = 50.0  # Пока фиксированный лимит
        self.item_data = ItemData()
    
    def add_item(self, item_id):
        """
        Добавляет предмет в инвентарь.
        Возвращает True, если успешно, False, если не влезает.
        """
        mass = self.item_data.get_mass(item_id)
        if self.get_total_weight() + mass > self.max_weight:
            return False  # Не влезает
        self.items.append(item_id)
        return True
    
    def remove_item(self, item_id):
        """Удаляет предмет из инвентаря. Возвращает True, если успешно."""
        if item_id in self.items:
            self.items.remove(item_id)
            return True
        return False
    
    def has_item(self, item_id):
        """Проверяет, есть ли предмет в инвентаре."""
        return item_id in self.items
    
    def get_items(self):
        """Возвращает копию списка предметов."""
        return self.items.copy()
    
    def get_total_weight(self):
        """Вычисляет общий вес всех предметов."""
        total = 0.0
        for item_id in self.items:
            total += self.item_data.get_mass(item_id)
        return total
    
    def is_empty(self):
        """Проверяет, пуст ли инвентарь."""
        return len(self.items) == 0