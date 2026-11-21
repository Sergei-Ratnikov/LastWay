# objects/item_tool.py
# =============================================================================
# ИНСТРУМЕНТЫ (ToolItem)
# Отмычки, фонарь, верёвка. Используются для взлома, ремонта, побега.
# =============================================================================

from objects.item import Item, ItemCategory, PaperDollSlot
from world.item_data import ItemData
from logger import log


class ToolItem(Item):
    """
    Инструменты (отмычки, резец, верёвка, фонарь, письменный прибор).
    Используются для взлома, ремонта, допроса, побега.
    Хранятся в Поклаже, могут надеваться на слот TOOL.
    
    Специфичные атрибуты:
        slot (PaperDollSlot): Слот экипировки (TOOL).
    """
    
    def __init__(self, item_id: str, quantity: int = 1, slot: str = "tool"):
        """
        Создаёт экземпляр инструмента.
        
        Аргументы:
            item_id (str): ID предмета из items.json.
            quantity (int): Количество в стаке.
            slot (str): Слот экипировки ("tool").
                        Параметр нужен для ItemCreator.
        """
        super().__init__(item_id, quantity)
        
        if self.category != ItemCategory.TOOL:
            log.warning(
                f"ToolItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'tool'"
            )
        
        # Читаем слот из items.json
        item_data = ItemData()
        props = item_data.get(item_id) or {}
        slot_str = props.get("slot", slot)
        
        try:
            self.slot = PaperDollSlot(slot_str)
        except ValueError:
            log.warning(f"ToolItem: неизвестный слот '{slot_str}' для {item_id}, использую TOOL")
            self.slot = PaperDollSlot.TOOL
    
    def use(self, actor, target=None):
        """Инструмент требует цель для применения."""
        log.info(f"ToolItem: {actor.name} готовит '{self.name}' к работе")
        pass