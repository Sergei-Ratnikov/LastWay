# objects/item_weapon.py
# =============================================================================
# ОРУЖИЕ (WeaponItem)
# Кинжалы, шпаги, арбалеты. Наносит урон.
# =============================================================================

from objects.item import Item, ItemCategory, PaperDollSlot
from world.item_data import ItemData
from logger import log


class WeaponItem(Item):
    """
    Оружие (кинжал, шпага, арбалет, посох).
    Наносит урон в зависимости от многих факторов (тип, прочность, навык).
    Хранится в Поклаже, надевается на слот WEAPON.
    
    Специфичные атрибуты:
        requires_ammo (bool): Требует ли оружие боеприпасов.
        slot (PaperDollSlot): Слот экипировки (WEAPON).
    """
    
    def __init__(self, item_id: str, quantity: int = 1, requires_ammo: bool = False, slot: str = "weapon"):
        """
        Создаёт экземпляр оружия.
        
        Аргументы:
            item_id (str): ID предмета из items.json.
            quantity (int): Количество в стаке.
            requires_ammo (bool): Требует ли оружие боеприпасов.
            slot (str): Слот экипировки ("weapon").
                        Параметр нужен для ItemCreator.
        """
        super().__init__(item_id, quantity)
        
        if self.category != ItemCategory.WEAPON:
            log.warning(
                f"WeaponItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'weapon'"
            )
        
        # Читаем специфичные поля из items.json
        item_data = ItemData()
        props = item_data.get(item_id) or {}
        self.requires_ammo = bool(props.get("requires_ammo", requires_ammo))
        
        # Слот
        slot_str = props.get("slot", slot)
        try:
            self.slot = PaperDollSlot(slot_str)
        except ValueError:
            log.warning(f"WeaponItem: неизвестный слот '{slot_str}' для {item_id}, использую WEAPON")
            self.slot = PaperDollSlot.WEAPON
    
    def use(self, actor, target=None):
        """Использование оружия = экипировать или атаковать."""
        log.info(f"WeaponItem: {actor.name} берёт в руки '{self.name}'")
        pass