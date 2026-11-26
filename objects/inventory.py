# objects/inventory.py

'''
ИНВЕНТАРЬ — «СКЛАД ФАКТОВ»
Хранит, ЧТО и ГДЕ лежит: items (список) + equipped (Paper Doll).
НЕ проверяет вес, НЕ решает «можно ли надеть», НЕ применяет эффекты.
Все правила и действия — в systems/inventory_system.py.
'''

from objects.item import Item, PaperDollSlot
from logger import log


class Inventory:
    """
    Инвентарь игрока.
    Отвечает только на вопросы «что где лежит» и «положи/убери».
    """

    def __init__(self, max_weight: float = 50.0):
        self.items: list[Item] = []
        self.equipped: dict[PaperDollSlot, Item] = {}
        self.max_weight = max_weight

    # =========================================================================
    # ДОБАВЛЕНИЕ / УДАЛЕНИЕ
    # =========================================================================

    def add_item(self, item: Item):
        """
        Кладёт предмет в инвентарь. Без проверок веса — это делает система.
        """
        self.items.append(item)
        log.info(f"ИНВЕНТАРЬ: добавлен {item.name} (x{item.quantity})")

    def try_stack(self, item: Item) -> int:
        """
        Пытается разложить item.quantity по существующим стакам того же id.
        Возвращает ОСТАТОК, который не поместился в существующие стаки.
        Сам item.quantity НЕ меняется (вызывает система).
        """
        if item.max_stack <= 1:
            return item.quantity

        remaining = item.quantity
        for existing in self.items:
            if existing.id != item.id:
                continue
            if existing.quantity >= existing.max_stack:
                continue
            space = existing.max_stack - existing.quantity
            move = min(space, remaining)
            existing.quantity += move
            remaining -= move
            if remaining == 0:
                break
        return remaining

    def remove_item(self, item: Item) -> Item | None:
        """Удаляет конкретный экземпляр из инвентаря."""
        if item in self.items:
            self.items.remove(item)
            log.info(f"ИНВЕНТАРЬ: удалён {item.name}")
            return item
        return None

    def remove_item_by_id(self, item_id: str) -> Item | None:
        """Удаляет первый найденный предмет с указанным ID."""
        for item in self.items:
            if item.id == item_id:
                self.items.remove(item)
                log.info(f"ИНВЕНТАРЬ: удалён {item.name} (по ID {item_id})")
                return item
        return None

    # =========================================================================
    # ЭКИПИРОВКА (PAPER DOLL) — только перекладывание
    # =========================================================================

    def equip(self, item: Item) -> bool:
        """
        Перекладывает предмет из items в equipped на его слот.
        Если слот занят — старый предмет возвращается в items.
        Проверки (equippable/slot/gender/requirements) — в InventorySystem.
        """
        slot = getattr(item, 'slot', None)
        if slot is None:
            log.warning(f"ЭКИПИРОВКА: у {item.name} нет slot")
            return False

        if item in self.items:
            self.items.remove(item)

        if slot in self.equipped:
            old = self.equipped[slot]
            self.items.append(old)
            log.info(f"ЭКИПИРОВКА: снят {old.name} с {slot.value}")

        self.equipped[slot] = item
        log.info(f"ЭКИПИРОВКА: надет {item.name} на {slot.value}")
        return True

    def unequip(self, slot: PaperDollSlot) -> Item | None:
        """Снимает предмет со слота в items."""
        if slot not in self.equipped:
            log.info(f"ЭКИПИРОВКА: слот {slot.value} пуст")
            return None
        item = self.equipped.pop(slot)
        self.items.append(item)
        log.info(f"ЭКИПИРОВКА: снят {item.name} с {slot.value} в инвентарь")
        return item

    def get_equipped(self, slot: PaperDollSlot) -> Item | None:
        return self.equipped.get(slot)

    def get_all_equipped(self) -> dict[PaperDollSlot, Item]:
        return self.equipped.copy()

    # =========================================================================
    # ЗАПРОСЫ
    # =========================================================================

    def has_item(self, item_id: str) -> bool:
        if any(item.id == item_id for item in self.items):
            return True
        return any(item.id == item_id for item in self.equipped.values())

    def get_item_by_id(self, item_id: str) -> Item | None:
        for item in self.items:
            if item.id == item_id:
                return item
        for item in self.equipped.values():
            if item.id == item_id:
                return item
        return None

    def get_items(self) -> list[Item]:
        return self.items.copy()

    def get_items_by_storage(self, storage_type) -> list:
        from objects.item import StorageType
        if isinstance(storage_type, str):
            try:
                storage_type = StorageType(storage_type)
            except ValueError:
                return []
        return [item for item in self.items if item.storage_type == storage_type]

    def get_total_weight(self) -> float:
        """Вес инвентаря + экипировки. Считается по факту, без правил."""
        inv = sum(item.weight * item.quantity for item in self.items)
        eq = sum(item.weight * item.quantity for item in self.equipped.values())
        return inv + eq

    def is_empty(self) -> bool:
        return len(self.items) == 0

    # =========================================================================
    # СЕРИАЛИЗАЦИЯ
    # =========================================================================

    def to_dict_list(self) -> list[dict]:
        return [item.to_dict() for item in self.items]

    def equipped_to_dict(self) -> dict:
        return {slot.value: item.to_dict() for slot, item in self.equipped.items()}

    def load_from_dict_list(self, data_list: list[dict]):
        self.items.clear()
        for item_dict in data_list:
            try:
                self.items.append(Item.from_dict(item_dict))
            except Exception as e:
                log.error(f"ИНВЕНТАРЬ: ошибка загрузки предмета: {e}")

    def load_equipped_from_dict(self, data_dict: dict):
        self.equipped.clear()
        for slot_name, item_dict in data_dict.items():
            try:
                slot = PaperDollSlot(slot_name)
                self.equipped[slot] = Item.from_dict(item_dict)
            except Exception as e:
                log.error(f"ИНВЕНТАРЬ: ошибка загрузки экипировки {slot_name}: {e}")