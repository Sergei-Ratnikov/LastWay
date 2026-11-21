# objects/item_clothing.py
# =============================================================================
# ОДЕЖДА (ClothingItem)
# Рясы, бригантины, платья. Меняет социальные теги и доступ.
# =============================================================================

from objects.item import Item, ItemCategory, PaperDollSlot
from world.item_data import ItemData
from logger import log


class ClothingItem(Item):
    """
    Одежда и нашивки.
    Меняет социальные теги и доступ к диалогам/локациям.
    Хранится в Поклаже, надевается на слоты CLOTHING или PATCH.
    
    Специфичные атрибуты:
        slot (PaperDollSlot): Слот экипировки (CLOTHING или PATCH).
    """
    
    def __init__(self, item_id: str, quantity: int = 1, slot: str = "clothing"):
        """
        Создаёт экземпляр одежды.
        
        Аргументы:
            item_id (str): ID предмета из items.json.
            quantity (int): Количество в стаке.
            slot (str): Слот экипировки ("clothing" или "patch").
                        Параметр нужен для ItemCreator.
                        Реальное значение читается из items.json ниже.
        """
        super().__init__(item_id, quantity)
        
        if self.category != ItemCategory.CLOTHING:
            log.warning(
                f"ClothingItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'clothing'"
            )
        
        # Читаем слот из items.json
        item_data = ItemData()
        props = item_data.get(item_id) or {}
        slot_str = props.get("slot", slot)
        
        try:
            self.slot = PaperDollSlot(slot_str)
        except ValueError:
            log.warning(f"ClothingItem: неизвестный слот '{slot_str}' для {item_id}, использую CLOTHING")
            self.slot = PaperDollSlot.CLOTHING
    
    def use(self, actor, target=None):
        """Использование одежды = надеть/снять."""
        log.info(f"ClothingItem: {actor.name} примеряет '{self.name}'")
        pass