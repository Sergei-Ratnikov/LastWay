# objects/item_quest.py

from objects.item import Item, ItemCategory
from logger import log


class QuestItem(Item):
    """
    Квестовый предмет (детская лошадка, шапка кардинала, платок с монограммой).
    Хранится в Ларце (скрытое хранение).
    При осмотре в правильном месте / предъявлении NPC триггерит воспоминание
    или открывает новую опцию диалога.
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ АТРИБУТЫ:
    ----------------------------------------------------------------------
    - quest_flag (str): Флаг, который активируется при триггере.
    - memory_id (str): ID воспоминания (flashback).
    - trigger_location (str): ID локации, где предмет "оживает".
    - trigger_npc (str): ID NPC, которому нужно показать.
    - description_lore (str): Расширенное описание при осмотре.
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ МЕТОДЫ:
    ----------------------------------------------------------------------
    - inspect(actor): Осмотр предмета (может триггернуть воспоминание).
    - present_to(actor, npc): Показать NPC (новая опция диалога).
    - check_trigger(actor, context) -> bool: Проверка условий триггера.
    """
    
    def __init__(self, item_id: str, quantity: int = 1):
        super().__init__(item_id, quantity)
        
        if self.category != ItemCategory.QUEST:
            log.warning(
                f"QuestItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'quest'"
            )
    
    def use(self, actor, target=None):
        """Осмотр квестового предмета."""
        log.info(f"QuestItem: {actor.name} осматривает '{self.name}'")
        # Будущая логика: показать описание + проверить триггеры.
        pass