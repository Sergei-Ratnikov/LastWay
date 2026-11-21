# objects/inventory.py
# =============================================================================
# ИНВЕНТАРЬ
# Логика хранения предметов игрока.
# Хранит экземпляры класса Item, считает вес, проверяет лимиты.
# Управляет экипировкой (Paper Doll).
# =============================================================================

from objects.item import Item, create_item, PaperDollSlot
from logger import log


class Inventory:
    """
    Инвентарь игрока.
    Хранит список объектов Item (не строки ID).
    Управляет экипированными предметами (Paper Doll).
    Считает общий вес (включая экипированное), проверяет лимиты.
    """
    
    def __init__(self, max_weight: float = 50.0):
        """
        Инициализация инвентаря.
        
        Аргументы:
            max_weight (float): Максимальный переносимый вес в кг.
        """
        # Список объектов Item (не строк!)
        self.items: list[Item] = []
        
        # Экипированные предметы (Paper Doll)
        # Ключ — PaperDollSlot (Enum), значение — объект Item
        self.equipped: dict[PaperDollSlot, Item] = {}
        
        # Лимит веса (синхронизируется с классом игрока в GameEngine)
        self.max_weight = max_weight
    
    # =========================================================================
    # ДОБАВЛЕНИЕ / УДАЛЕНИЕ ИЗ ИНВЕНТАРЯ
    # =========================================================================
    
    def add_item(self, item: Item) -> bool:
        """
        Добавляет предмет в инвентарь.
        
        Аргументы:
            item (Item): Экземпляр предмета для добавления.
            
        Возвращает:
            bool: True, если успешно добавлен, False если не влез по весу.
        """
        # Проверяем, влезает ли предмет по весу
        new_weight = self.get_total_weight() + (item.weight * item.quantity)
        if new_weight > self.max_weight:
            log.info(f"ИНВЕНТАРЬ: {item.name} не влез (превышен вес)")
            return False
        
        self.items.append(item)
        log.info(f"ИНВЕНТАРЬ: добавлен {item.name} (x{item.quantity})")
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
    # ЭКИПИРОВКА (PAPER DOLL)
    # =========================================================================
    
    def equip(self, item: Item) -> bool:
        """
        Экипирует предмет на соответствующий слот Paper Doll.
        Если слот занят — автоматически снимает старый предмет в инвентарь.
        
        Аргументы:
            item (Item): Экземпляр предмета для экипировки.
            
        Возвращает:
            bool: True, если успешно экипирован.
        """
        # Проверяем, что предмет можно экипировать
        if not item.equippable:
            log.warning(f"ЭКИПИРОВКА: {item.name} нельзя экипировать")
            return False
        
        # Проверяем, что у предмета есть слот
        if not hasattr(item, 'slot') or item.slot is None:
            log.warning(f"ЭКИПИРОВКА: у {item.name} не указан слот")
            return False
        
        slot = item.slot
        
        # Если предмет уже экипирован на этом слоте — ничего не делаем
        if slot in self.equipped and self.equipped[slot] is item:
            log.info(f"ЭКИПИРОВКА: {item.name} уже экипирован")
            return True
        
        # Если слот занят — снимаем старый предмет в инвентарь
        if slot in self.equipped:
            old_item = self.equipped[slot]
            self.items.append(old_item)
            log.info(f"ЭКИПИРОВКА: снят {old_item.name} с {slot.value}")
        
        # Удаляем предмет из инвентаря
        if item in self.items:
            self.items.remove(item)
        
        # Экипируем
        self.equipped[slot] = item
        log.info(f"ЭКИПИРОВКА: надет {item.name} на {slot.value}")
        return True
    
    def unequip(self, slot: PaperDollSlot) -> Item | None:
        """
        Снимает предмет с указанного слота Paper Doll в инвентарь.
        
        Аргументы:
            slot (PaperDollSlot): Слот для снятия.
            
        Возвращает:
            Item | None: Снятый предмет или None, если слот пуст.
        """
        if slot not in self.equipped:
            log.info(f"ЭКИПИРОВКА: слот {slot.value} пуст")
            return None
        
        item = self.equipped[slot]
        
        # Добавляем в инвентарь
        self.items.append(item)
        
        # Удаляем из экипировки
        del self.equipped[slot]
        
        log.info(f"ЭКИПИРОВКА: снят {item.name} с {slot.value} в инвентарь")
        return item
    
    def get_equipped(self, slot: PaperDollSlot) -> Item | None:
        """
        Возвращает предмет, экипированный на указанном слоте.
        
        Аргументы:
            slot (PaperDollSlot): Слот.
            
        Возвращает:
            Item | None: Экипированный предмет или None.
        """
        return self.equipped.get(slot)
    
    def get_all_equipped(self) -> dict[PaperDollSlot, Item]:
        """
        Возвращает словарь всех экипированных предметов.
        
        Возвращает:
            dict[PaperDollSlot, Item]: Копия словаря экипировки.
        """
        return self.equipped.copy()
    
    # =========================================================================
    # ЗАПРОСЫ
    # =========================================================================
    
    def has_item(self, item_id: str) -> bool:
        """
        Проверяет наличие предмета по ID (для квестов/диалогов).
        Ищет и в инвентаре, и в экипировке.
        
        Аргументы:
            item_id (str): ID предмета для проверки.
            
        Возвращает:
            bool: True, если предмет есть.
        """
        # Проверяем инвентарь
        if any(item.id == item_id for item in self.items):
            return True
        # Проверяем экипировку
        if any(item.id == item_id for item in self.equipped.values()):
            return True
        return False
    
    def get_item_by_id(self, item_id: str) -> Item | None:
        """
        Возвращает первый найденный предмет с указанным ID.
        Ищет и в инвентаре, и в экипировке.
        
        Аргументы:
            item_id (str): ID предмета.
            
        Возвращает:
            Item | None: Найденный предмет или None.
        """
        # Ищем в инвентаре
        for item in self.items:
            if item.id == item_id:
                return item
        # Ищем в экипировке
        for item in self.equipped.values():
            if item.id == item_id:
                return item
        return None
    
    def get_items(self) -> list[Item]:
        """
        Возвращает копию списка предметов в инвентаре (без экипированных).
        
        Возвращает:
            list[Item]: Копия списка объектов Item.
        """
        return self.items.copy()
    
    def get_items_by_storage(self, storage_type) -> list:
        """
        Возвращает список предметов с указанной категорией хранения.
        
        Аргументы:
            storage_type: Значение StorageType (например, StorageType.ARCHIVE).
            
        Возвращает:
            list[Item]: Отфильтрованный список предметов.
        """
        from objects.item import StorageType
        if isinstance(storage_type, str):
            # Поддержка передачи строки ("archive")
            try:
                storage_type = StorageType(storage_type)
            except ValueError:
                return []
        return [item for item in self.items if item.storage_type == storage_type]
    
    def get_total_weight(self) -> float:
        """
        Вычисляет общий вес всех предметов (инвентарь + экипировка).
        
        Возвращает:
            float: Общий вес в кг.
        """
        # Вес предметов в инвентаре
        inv_weight = sum(item.weight * item.quantity for item in self.items)
        # Вес экипированных предметов
        equip_weight = sum(item.weight * item.quantity for item in self.equipped.values())
        return inv_weight + equip_weight
    
    def is_empty(self) -> bool:
        """
        Проверяет, пуст ли инвентарь (без учёта экипировки).
        
        Возвращает:
            bool: True, если предметов нет.
        """
        return len(self.items) == 0
    
    # =========================================================================
    # СЕРИАЛИЗАЦИЯ ДЛЯ СОХРАНЕНИЙ
    # =========================================================================
    
    def to_dict_list(self) -> list[dict]:
        """
        Сериализует все предметы инвентаря в список словарей для JSON.
        
        Возвращает:
            list[dict]: Список словарей (каждый — результат item.to_dict()).
        """
        return [item.to_dict() for item in self.items]
    
    def equipped_to_dict(self) -> dict:
        """
        Сериализует экипированные предметы в словарь для JSON.
        
        Возвращает:
            dict: {slot_name: item_dict} для каждого экипированного предмета.
        """
        result = {}
        for slot, item in self.equipped.items():
            result[slot.value] = item.to_dict()
        return result
    
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
    
    def load_equipped_from_dict(self, data_dict: dict):
        """
        Загружает экипированные предметы из словаря (из JSON сохранения).
        Очищает текущую экипировку перед загрузкой.
        
        Аргументы:
            data_dict (dict): {slot_name: item_dict} из сохранения.
        """
        self.equipped.clear()
        for slot_name, item_dict in data_dict.items():
            try:
                slot = PaperDollSlot(slot_name)
                item = Item.from_dict(item_dict)
                self.equipped[slot] = item
            except Exception as e:
                log.error(f"ИНВЕНТАРЬ: ошибка загрузки экипировки {slot_name}: {e}")