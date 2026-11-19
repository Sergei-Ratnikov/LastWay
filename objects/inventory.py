# objects/inventory.py
# =============================================================================
# ИНВЕНТАРЬ
# Логика хранения предметов игрока.
# Хранит экземпляры класса Item, считает вес, проверяет лимиты.
# =============================================================================

from objects.item import Item, create_item
from logger import log


class Inventory:
    """
    Инвентарь игрока.
    Хранит список объектов Item (не строки ID).
    Считает общий вес, проверяет лимиты при добавлении.
    """
    
    def __init__(self, max_weight: float = 50.0):
        """
        Инициализация инвентаря.
        
        Аргументы:
            max_weight (float): Максимальный переносимый вес в кг.
        """
        # Список объектов Item (не строк!)
        self.items: list[Item] = []
        # Лимит веса (синхронизируется с классом игрока в GameEngine)
        self.max_weight = max_weight
    
    # =========================================================================
    # ДОБАВЛЕНИЕ / УДАЛЕНИЕ
    # =========================================================================
        
    def add_item(self, item: Item) -> bool:
        """
        Добавляет предмет в инвентарь.
        Логирует реальный класс предмета для диагностики.
        """
        new_weight = self.get_total_weight() + (item.weight * item.quantity)
        if new_weight > self.max_weight:
            log.info(f"ИНВЕНТАРЬ: {item.name} не влез (превышен вес)")
            return False
        
        self.items.append(item)
        # ДИАГНОСТИКА: печатаем реальный тип объекта (KeyItem, DocumentItem и т.д.)
        log.info(
            f"ИНВЕНТАРЬ: добавлен {item.name} (x{item.quantity}) "
            f"[класс: {type(item).__name__}, id объекта: {id(item)}]"
        )
        return True

    
    def remove_item(self, item: Item) -> Item | None:
        """
        Удаляет конкретный экземпляр предмета из инвентаря.
        
        Аргументы:
            item (Item): Экземпляр предмета для удаления.
            
        Возвращает:
            Item | None: Удалённый предмет или None, если не найден.
        """
        if item in self.items:
            self.items.remove(item)
            log.info(f"ИНВЕНТАРЬ: удалён {item.name}")
            return item
        return None
    
    def remove_item_by_id(self, item_id: str) -> Item | None:
        """
        Удаляет первый найденный предмет с указанным ID.
        Используется, когда нужен именно ID (например, для квестов).
        
        Аргументы:
            item_id (str): ID предмета для удаления.
            
        Возвращает:
            Item | None: Удалённый предмет или None, если не найден.
        """
        for item in self.items:
            if item.id == item_id:
                self.items.remove(item)
                log.info(f"ИНВЕНТАРЬ: удалён {item.name} (по ID {item_id})")
                return item
        return None
    
    # =========================================================================
    # ЗАПРОСЫ
    # =========================================================================
    
    def has_item(self, item_id: str) -> bool:
        """
        Проверяет наличие предмета по ID (для квестов/диалогов).
        
        Аргументы:
            item_id (str): ID предмета для проверки.
            
        Возвращает:
            bool: True, если предмет есть в инвентаре.
        """
        return any(item.id == item_id for item in self.items)
    
    def get_item_by_id(self, item_id: str) -> Item | None:
        """
        Возвращает первый найденный предмет с указанным ID.
        
        Аргументы:
            item_id (str): ID предмета.
            
        Возвращает:
            Item | None: Найденный предмет или None.
        """
        for item in self.items:
            if item.id == item_id:
                return item
        return None
    
    def get_items(self) -> list[Item]:
        """
        Возвращает копию списка предметов.
        
        Возвращает:
            list[Item]: Копия списка объектов Item.
        """
        return self.items.copy()
    
    def get_total_weight(self) -> float:
        """
        Вычисляет общий вес всех предметов в инвентаре.
        
        Возвращает:
            float: Общий вес в кг.
        """
        return sum(item.weight * item.quantity for item in self.items)
    
    def is_empty(self) -> bool:
        """
        Проверяет, пуст ли инвентарь.
        
        Возвращает:
            bool: True, если предметов нет.
        """
        return len(self.items) == 0
    
    # =========================================================================
    # СЕРИАЛИЗАЦИЯ ДЛЯ СОХРАНЕНИЙ
    # =========================================================================
    
    def to_dict_list(self) -> list[dict]:
        """
        Сериализует все предметы в список словарей для JSON.
        
        Возвращает:
            list[dict]: Список словарей (каждый — результат item.to_dict()).
        """
        return [item.to_dict() for item in self.items]
    
    def load_from_dict_list(self, data_list: list[dict]):
        """
        Загружает предметы из списка словарей (из JSON сохранения).
        Очищает текущий инвентарь перед загрузкой.
        
        Аргументы:
            data_list (list[dict]): Список словарей с данными предметов.
        """
        self.items.clear()
        for item_dict in data_list:
            try:
                item = Item.from_dict(item_dict)
                self.items.append(item)
            except Exception as e:
                log.error(f"ИНВЕНТАРЬ: ошибка загрузки предмета из dict: {e}")