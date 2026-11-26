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
                    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ АТРИБУТЫ (идеи на потом):
    ----------------------------------------------------------------------
    - lore_id (str): ID текста в архиве игры.
    - is_forged (bool): Подделан ли документ.
    - is_sealed (bool): Запечатан ли.
    - author (str): Автор документа.
    - recipient (str): Предназначен конкретному NPC.
    """
    
    # FIX: добавлен параметр text, чтобы Item Creator автоматически
    # увидел это поле через inspect.signature() и показал его в форме
    # редактирования для категории "document".
    def __init__(self, item_id: str, quantity: int = 1, text: str = ""):
        """
        Создаёт экземпляр документа.
        
        Аргументы:
            item_id (str): ID предмета из items.json.
            quantity (int): Количество в стаке.
            text (str): Текст документа (параметр нужен для Item Creator).
                        Реальное значение читается из items.json ниже.
        """
        super().__init__(item_id, quantity)
        
        # Защита от дурака: проверяем, что категория правильная
        if self.category != ItemCategory.DOCUMENT:
            log.warning(
                f"DocumentItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'document'"
            )
        
        # Читаем текст документа из items.json.
        # Параметр text в сигнатуре нужен только для Item Creator;
        # реальное значение всегда берётся из JSON.
        item_data = ItemData()
        props = item_data.get(item_id) or {}
        self.text = props.get("text", "")
        
        if not self.text:
            log.warning(f"DocumentItem: у документа '{item_id}' отсутствует поле 'text'")

    def use(self, actor, engine=None) -> bool:
        """
        Чтение документа: открывает модальное окно с текстом.
        Сигнатура (actor, engine) — единая для всех Item.use.
        """
        log.info(f"DocumentItem: {actor.name} читает '{self.name}'")
        if engine is not None and hasattr(engine, 'document_viewer'):
            engine.document_viewer.open(self.text, self.name)
            return True
        log.error("DocumentItem: нет engine.document_viewer")
        return False