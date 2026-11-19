# objects/item_consumable.py

from objects.item import Item, ItemCategory
from logger import log


class ConsumableItem(Item):
    """
    Расходники (еда, вино, бинты, белладонна, набор лекаря).
    Влияют на состояние игрока и NPC. Хранятся в Поклаже.
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ АТРИБУТЫ:
    ----------------------------------------------------------------------
    - effects (dict): {"health": 20, "humanity": -5, "hunger": 30}.
    - charges (int): Количество доз (бутылка вина = 3 дозы).
    - is_poison (bool): Яд (можно подсыпать в еду NPC).
    - addiction_risk (float): Риск привыкания (опиум, вино).
    - spoil_timer (int): Время до порчи (для еды).
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ МЕТОДЫ:
    ----------------------------------------------------------------------
    - consume(actor): Применить эффекты, уменьшить charges.
    - apply_to(actor, target): Накладное применение (бинты на рану).
    - slip_into(actor, target_item): Подсыпать яд в еду/питьё.
    - get_effects_description() -> str: Человекочитаемый список эффектов.
    """
    
    def __init__(self, item_id: str, quantity: int = 1):
        super().__init__(item_id, quantity)
        
        if self.category != ItemCategory.CONSUMABLE:
            log.warning(
                f"ConsumableItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'consumable'"
            )
    
    def use(self, actor, target=None):
        """Использование расходника."""
        log.info(f"ConsumableItem: {actor.name} использует '{self.name}'")
        # Будущая логика: применить эффекты, уменьшить charges.
        pass