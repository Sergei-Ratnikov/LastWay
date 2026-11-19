# objects/item_jewelry.py

from objects.item import Item, ItemCategory, PaperDollSlot
from logger import log


class JewelryItem(Item):
    """
    Знаковые украшения (перстень с гербом, цеховой знак, жемчужный крест).
    Надеваются для демонстрации статуса, принадлежности.
    Хранятся в Ларце, надеваются на слоты RING или AMULET.
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ АТРИБУТЫ:
    ----------------------------------------------------------------------
    - slot (PaperDollSlot): RING или AMULET.
    - social_tags (list[str]): ["noble", "inquisition", "guild_member"].
    - is_cursed (bool): Проклятое (нельзя снять без ритуала).
    - magic_effect (str): Магический эффект (редкость в нашем сеттинге).
    - prestige (int): Очки престижа (для дворянского двора).
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ МЕТОДЫ:
    ----------------------------------------------------------------------
    - equip(actor): Надеть, обновить социальные теги актёра.
    - unequip(actor): Снять, убрать теги.
    - appraise(actor) -> int: Оценить (с учётом престижа).
    - consecrate(actor, location): Освятить (для крестов).
    """
    
    def __init__(self, item_id: str, quantity: int = 1):
        super().__init__(item_id, quantity)
        
        if self.category != ItemCategory.JEWELRY:
            log.warning(
                f"JewelryItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'jewelry'"
            )
    
    def use(self, actor, target=None):
        """Использование украшения = надеть/снять."""
        log.info(f"JewelryItem: {actor.name} примеряет '{self.name}'")
        # Будущая логика: экипировка на Paper Doll.
        pass