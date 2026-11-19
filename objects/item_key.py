#  objects/item_key.py

from objects.item import Item, ItemCategory
from logger import log


class KeyItem(Item):
    """
    Ключ (от двери, сундука, секретного хода).
    Хранится в Архиве. Физически открывает привязанный замок.
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ АТРИБУТЫ:
    ----------------------------------------------------------------------
    - target_lock_id (str): ID замка/двери/контейнера, который открывает.
    - key_type (str): Тип ключа ("simple", "master", "skeleton").
    - is_master (bool): Отмычка-мастер (открывает все замки типа).
    - uses_left (int): Для отмычек — сколько применений осталось.
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ МЕТОДЫ:
    ----------------------------------------------------------------------
    - use_on(actor, target_object): Проверить совпадение target_lock_id.
    - fits_lock(lock_id) -> bool: Совместимость с конкретным замком.
    """
    
    def __init__(self, item_id: str, quantity: int = 1):
        super().__init__(item_id, quantity)
        
        if self.category != ItemCategory.KEY:
            log.warning(
                f"KeyItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'key'"
            )
    
    def use(self, actor, target=None):
        """
        Ключ нельзя просто "использовать" — его нужно применить к двери/сундуку.
        """
        log.info(f"KeyItem: {actor.name} вертит в руках '{self.name}' (нужна цель)")
        # Будущая логика: открыть меню выбора цели или проверить клетку перед игроком.
        pass