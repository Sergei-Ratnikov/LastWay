# objects/item_document.py
# =============================================================================
# ДОКУМЕНТ (DocumentItem)
# Письма, дневники, пропуска, доносы.
# Можно прочитать (открывает окно с текстом), предъявить NPC, подделать.
# =============================================================================

from objects.item import Item, ItemCategory
from world.item_data import ItemData
from logger import log


class DocumentItem(Item):
    """
    Документ (письмо, пропуск, дневник, долговая расписка, донос).
    Хранится в Архиве для быстрого доступа.
    
    Специфичные атрибуты:
        text (str): Текст документа (читается из items.json).
                    Поддерживает \n для разделения абзацев.
    """
    
    def __init__(self, item_id: str, quantity: int = 1):
        super().__init__(item_id, quantity)
        
        # Защита от дурака: проверяем, что категория правильная
        if self.category != ItemCategory.DOCUMENT:
            log.warning(
                f"DocumentItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'document'"
            )
        
        # Читаем текст документа из items.json
        item_data = ItemData()
        props = item_data.get(item_id) or {}
        self.text = props.get("text", "")
        
        if not self.text:
            log.warning(f"DocumentItem: у документа '{item_id}' отсутствует поле 'text'")
    
    def use(self, engine):
        """
        Чтение документа: открывает модальное окно с текстом.
        
        Аргументы:
            engine: GameEngine (нужен для доступа к document_viewer).
        """
        log.info(f"DocumentItem: {engine.game_state.player.name} читает '{self.name}'")
        
        # Открываем окно просмотра документа
        if hasattr(engine, 'document_viewer'):
            engine.document_viewer.open(self.text, self.name)
        else:
            log.error("DocumentItem: у GameEngine нет document_viewer")