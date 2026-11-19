# objects/drop.py
# =============================================================================
# ДРОП (КУЧА ПРЕДМЕТОВ НА ЗЕМЛЕ)
# Объект мира, представляющий кучу предметов на земле.
# Может содержать один или несколько предметов (объектов Item).
# =============================================================================

from objects.item import Item
from logger import log


class ItemDrop:
    """
    Куча предметов на земле.
    Хранит объекты Item, может содержать один или несколько предметов.
    """
    
    def __init__(self, drop_id, x, y, items=None):
        """
        Инициализация дропа.
        
        Аргументы:
            drop_id (str): Уникальный идентификатор кучи.
            x, y (int): Координаты на карте.
            items (list[Item]): Список объектов Item.
        """
        self.id = drop_id
        self.x = x
        self.y = y
        # Список объектов Item (не строк!)
        self.items: list[Item] = items if items is not None else []
    
    @property
    def is_empty(self):
        """Возвращает True, если в куче больше нет предметов."""
        return len(self.items) == 0
    
    # =========================================================================
    # РАБОТА С ПРЕДМЕТАМИ
    # =========================================================================
    
    def take_item(self, item: Item) -> Item | None:
        """
        Забирает конкретный экземпляр предмета из кучи.
        
        Аргументы:
            item (Item): Экземпляр предмета для извлечения.
            
        Возвращает:
            Item | None: Извлечённый предмет или None.
        """
        if item in self.items:
            self.items.remove(item)
            log.info(f"ДРОП: из {self.id} извлечён {item.name}")
            return item
        return None
    
    def take_item_by_id(self, item_id: str) -> Item | None:
        """
        Забирает первый найденный предмет с указанным ID.
        
        Аргументы:
            item_id (str): ID предмета.
            
        Возвращает:
            Item | None: Извлечённый предмет или None.
        """
        for item in self.items:
            if item.id == item_id:
                self.items.remove(item)
                return item
        return None
    
    def add_item(self, item: Item):
        """
        Добавляет предмет в кучу.
        
        Аргументы:
            item (Item): Экземпляр предмета.
        """
        self.items.append(item)
        log.info(f"ДРОП: в {self.id} добавлен {item.name}")
    
    def get_items(self) -> list[Item]:
        """Возвращает копию списка предметов."""
        return self.items.copy()
    
    # =========================================================================
    # СЕРИАЛИЗАЦИЯ
    # =========================================================================
    
    def items_to_dict_list(self) -> list[dict]:
        """Сериализует предметы дропа в список словарей."""
        return [item.to_dict() for item in self.items]
    
    def load_items_from_dict_list(self, data_list: list[dict]):
        """Загружает предметы из списка словарей."""
        self.items.clear()
        for item_dict in data_list:
            try:
                from objects.item import Item
                item = Item.from_dict(item_dict)
                self.items.append(item)
            except Exception as e:
                log.error(f"ДРОП: ошибка загрузки предмета: {e}")