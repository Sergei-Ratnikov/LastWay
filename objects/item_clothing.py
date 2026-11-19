# objects/item_clothing.py

from objects.item import Item, ItemCategory, PaperDollSlot
from logger import log


class ClothingItem(Item):
    """
    Одежда и нашивки (ряса монаха, бригантина, траурное платье, знак инквизиции).
    Меняет НЕ очки брони, а социальные теги и доступ к диалогам/локациям.
    Хранится в Поклаже, надевается на слоты CLOTHING или PATCH.
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ АТРИБУТЫ:
    ----------------------------------------------------------------------
    - slot (PaperDollSlot): CLOTHING или PATCH.
    - social_tags (list[str]): ["clergy", "monk", "noble", "inquisition"].
    - condition (str): "clean", "dirty", "torn", "bloodied" (влияет на реакцию).
    - warmth (int): Утепление (для системы холода в будущем).
    - noise_modifier (float): Модификатор шума при движении.
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ МЕТОДЫ:
    ----------------------------------------------------------------------
    - equip(actor): Надеть на слот, обновить социальные теги актёра.
    - unequip(actor): Снять, убрать теги.
    - repair(actor, tool): Починить (нужен инструмент).
    - dye(actor, ingredient): Покрасить (нужен ингредиент-краска).
    """
    
    def __init__(self, item_id: str, quantity: int = 1):
        super().__init__(item_id, quantity)
        
        if self.category != ItemCategory.CLOTHING:
            log.warning(
                f"ClothingItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'clothing'"
            )
    
    def use(self, actor, target=None):
        """Использование одежды = надеть/снять."""
        log.info(f"ClothingItem: {actor.name} примеряет '{self.name}'")
        # Будущая логика: экипировка на Paper Doll.
        pass