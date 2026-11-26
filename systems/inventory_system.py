# systems/inventory_system.py
# =============================================================================
# СИСТЕМА ИНВЕНТАРЯ
# Единая точка правил и действий: взять, выбросить, надеть, снять,
# использовать, переложить в источник.
# UI и GameEngine зовут только методы этого класса.
# =============================================================================

from objects.item import Item, ItemCategory, PaperDollSlot, GenderRestriction
from logger import log


class InventorySystem:
    """Механика инвентаря. Живёт в GameEngine всё время."""

    def __init__(self, engine):
        self.engine = engine

    # -------------------------------------------------------------------------
    # ВНУТРЕННИЕ ХЕЛПЕРЫ
    # -------------------------------------------------------------------------

    def _inv(self):
        return self.engine.game_state.inventory

    def _actor(self):
        return self.engine.game_state.player

    def _fits_weight(self, item: Item, quantity: int | None = None) -> bool:
        qty = item.quantity if quantity is None else quantity
        return self._inv().get_total_weight() + item.weight * qty <= self._inv().max_weight

    # -------------------------------------------------------------------------
    # ВЗЯТЬ ИЗ ИСТОЧНИКА (контейнер / дроп)
    # -------------------------------------------------------------------------

    def pick_up_from_source(self, item: Item, source, source_type: str, actor) -> tuple[int, str]:
        """Берёт предмет из контейнера/дропа целиком. Возвращает (сколько, сообщение)."""
        inv = self._inv()
        if not self._fits_weight(item):
            return 0, f"{item.name} не влез (превышен вес)"

        remaining = inv.try_stack(item)
        if remaining > 0:
            item.quantity = remaining
            inv.add_item(item)

        if source_type == "container":
            source.remove_item(item)
        else:
            source.take_item(item)

        log.info(f"ИНВЕНТАРЬ: взято {item.name} из {source_type}")
        return item.quantity, f"Взято: {item.name}" + (f" (x{item.quantity})" if item.quantity > 1 else "")

    # -------------------------------------------------------------------------
    # ПЕРЕЛОЖИТЬ В ИСТОЧНИК (инвентарь -> контейнер/дроп)
    # -------------------------------------------------------------------------

    def transfer_to_source(self, item: Item, source, source_type: str, actor) -> tuple[bool, str]:
        inv = self._inv()
        removed = inv.remove_item(item)
        if not removed:
            return False, "Предмет не найден в инвентаре"
        source.add_item(item)
        return True, f"Положено: {item.name}"

    # -------------------------------------------------------------------------
    # ВЫБРОСИТЬ
    # -------------------------------------------------------------------------

    def drop_item(self, item: Item, actor) -> tuple[bool, str]:
        inv = self._inv()
        if item.category == ItemCategory.QUEST:
            log.info(f"ИНВЕНТАРЬ: отказ в выбросе квестового {item.name}")
            return False, "Этот предмет слишком важен"

        for slot, eq in list(inv.equipped.items()):
            if eq is item:
                inv.unequip(slot)
                break

        if item not in inv.items:
            return False, "Предмет не найден"
        inv.remove_item(item)

        self.engine.current_map.add_or_update_drop(actor.x, actor.y, item)
        log.info(f"ИНВЕНТАРЬ: выброшено {item.name} на ({actor.x},{actor.y})")
        return True, f"Выброшено: {item.name}"

    # -------------------------------------------------------------------------
    # ЭКИПИРОВКА
    # -------------------------------------------------------------------------

    def can_equip(self, item: Item, actor) -> tuple[bool, str]:
        if not item.equippable:
            return False, "Этот предмет нельзя надеть"
        if getattr(item, 'slot', None) is None:
            return False, "У предмета не указан слот"

        if item.gender_restrict != GenderRestriction.ANY:
            if getattr(actor, 'gender', 'any') != item.gender_restrict.value:
                return False, "Не подходит по полу"

        req = getattr(item, 'requirements', {}) or {}
        if "class" in req:
            allowed = req["class"]
            if isinstance(allowed, str):
                allowed = [allowed]
            if getattr(actor, 'player_class', None) not in allowed:
                return False, "Не подходит по классу"

        return True, ""

    def equip_item(self, item: Item, actor) -> tuple[bool, str]:
        ok, reason = self.can_equip(item, actor)
        if not ok:
            return False, reason
        if self._inv().equip(item):
            return True, f"Надето: {item.name}"
        return False, "Не удалось надеть"

    def unequip_item(self, slot: PaperDollSlot, actor) -> tuple[bool, str]:
        inv = self._inv()
        item = inv.get_equipped(slot)
        if item is None:
            return False, "Слот пуст"
        inv.unequip(slot)
        return True, f"Снято: {item.name}"

    # -------------------------------------------------------------------------
    # ИСПОЛЬЗОВАТЬ
    # -------------------------------------------------------------------------

    def use_item(self, item: Item, actor) -> tuple[bool, str]:
        inv = self._inv()

        if item.category == ItemCategory.DOCUMENT:
            ok = item.use(actor, self.engine)
            return ok, ""

        if item.category == ItemCategory.CONSUMABLE:
            ok = item.use(actor, self.engine)
            if ok and item.quantity <= 0:
                inv.remove_item(item)
            return ok, f"Использовано: {item.name}"

        item.use(actor, self.engine)
        return True, f"Использование {item.name} (скоро)"