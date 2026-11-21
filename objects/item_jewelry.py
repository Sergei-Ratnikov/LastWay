# objects/item_jewelry.py
# =============================================================================
# УКРАШЕНИЯ (JewelryItem)
# Перстни, амулеты, кресты. Надеваются для демонстрации статуса.
# =============================================================================

from objects.item import Item, ItemCategory, PaperDollSlot
from world.item_data import ItemData
from logger import log


class JewelryItem(Item):
    """
    Знаковые украшения (перстень с гербом, цеховой знак, жемчужный крест).
    Надеваются для демонстрации статуса, принадлежности.
    Хранятся в Ларце, надеваются на слоты RING или AMULET.
    
    Специфичные атрибуты:
        slot (PaperDollSlot): Слот экипировки (RING или AMULET).
    """
    
    def __init__(self, item_id: str, quantity: int = 1, slot: str = "ring"):
        """
        Создаёт экземпляр украшения.
        
        Аргументы:
            item_id (str): ID предмета из items.json.
            quantity (int): Количество в стаке.
            slot (str): Слот экипировки ("ring" или "amulet").
                        Параметр нужен для ItemCreator.
        """
        super().__init__(item_id, quantity)
        
        if self.category != ItemCategory.JEWELRY:
            log.warning(
                f"JewelryItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'jewelry'"
            )
        
        # Читаем слот из items.json
        item_data = ItemData()
        props = item_data.get(item_id) or {}
        slot_str = props.get("slot", slot)
        
        try:
            self.slot = PaperDollSlot(slot_str)
        except ValueError:
            log.warning(f"JewelryItem: неизвестный слот '{slot_str}' для {item_id}, использую RING")
            self.slot = PaperDollSlot.RING
    
    def use(self, actor, target=None):
        """Использование украшения = надеть/снять."""
        log.info(f"JewelryItem: {actor.name} примеряет '{self.name}'")
        pass