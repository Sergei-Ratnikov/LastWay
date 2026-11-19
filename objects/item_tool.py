# objects/item_tool.py

from objects.item import Item, ItemCategory, PaperDollSlot
from logger import log


class ToolItem(Item):
    """
    Инструменты (отмычки, резец, верёвка, фонарь, письменный прибор).
    Используются для взлома, ремонта, допроса, побега.
    Хранятся в Поклаже, могут надеваться на слот TOOL.
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ АТРИБУТЫ:
    ----------------------------------------------------------------------
    - tool_type (str): "lockpick", "lantern", "rope", "crowbar", "writing_kit".
    - efficiency (float): Модификатор успеха действия (0.0 - 2.0).
    - light_radius (int): Для фонаря — радиус освещения.
    - fuel_left (int): Для фонаря — сколько масла осталось.
    - max_uses (int): Для отмычек — сколько взломов выдержит.
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ МЕТОДЫ:
    ----------------------------------------------------------------------
    - use_on(actor, target): Взлом, связывание, освещение.
    - repair(target_item): Починить другой предмет.
    - combine_with(other_tool): Объединить (верёвка + крюк = кошка).
    - get_success_chance(actor, target) -> float: Шанс успеха.
    """
    
    def __init__(self, item_id: str, quantity: int = 1):
        super().__init__(item_id, quantity)
        
        if self.category != ItemCategory.TOOL:
            log.warning(
                f"ToolItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'tool'"
            )
    
    def use(self, actor, target=None):
        """Инструмент требует цель для применения."""
        log.info(f"ToolItem: {actor.name} готовит '{self.name}' к работе")
        # Будущая логика: выбор цели на карте или в инвентаре.
        pass