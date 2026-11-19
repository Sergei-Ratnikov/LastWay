# objects/item_valuable.py

from objects.item import Item, ItemCategory
from logger import log


class ValuableItem(Item):
    """
    Ценности и монеты (кошелёк серебра, богато украшенный кинжал).
    Используются как награда, плата, взятка. Влияют на поведение NPC.
    Хранятся в Ларце (скрытое хранение при обыске).
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ АТРИБУТЫ:
    ----------------------------------------------------------------------
    - bribe_value (int): Сила взятки (для диалогов со стражниками).
    - is_stolen (bool): Украдено (нельзя продать легально).
    - fence_price_multiplier (float): Множитель цены у скупщика.
    - noble_value (int): Ценность для дворян (гербы, украшения).
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ МЕТОДЫ:
    ----------------------------------------------------------------------
    - bribe(actor, npc): Предложить взятку (проверка жадности NPC).
    - sell(actor, merchant) -> int: Продать торговцу.
    - appraise(actor) -> int: Оценить реальную стоимость.
    - hide_in(actor, container): Спрятать в тайник (от обыска).
    """
    
    def __init__(self, item_id: str, quantity: int = 1):
        super().__init__(item_id, quantity)
        
        if self.category != ItemCategory.VALUABLE:
            log.warning(
                f"ValuableItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'valuable'"
            )
    
    def use(self, actor, target=None):
        """Ценности сами по себе не используются — их продают/дарят."""
        log.info(f"ValuableItem: {actor.name} рассматривает '{self.name}'")
        pass