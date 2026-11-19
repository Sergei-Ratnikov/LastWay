# item_weapon.py

from objects.item import Item, ItemCategory, PaperDollSlot
from world.item_data import ItemData
from logger import log


class WeaponItem(Item):
    """
    Оружие (кинжал, шпага, арбалет, посох).
    Наносит урон в зависимости от многих факторов (тип, прочность, навык).
    Хранится в Поклаже, надевается на слот WEAPON.
    
    ----------------------------------------------------------------------
    СПЕЦИФИЧНЫЕ АТРИБУТЫ (материализованы в конструкторе):
    ----------------------------------------------------------------------
    - requires_ammo (bool): Требует ли оружие боеприпасов (арбалет → болты).
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ АТРИБУТЫ (идеи на потом):
    ----------------------------------------------------------------------
    - damage (int): Базовый урон.
    - reach (int): Досягаемость в клетках (1 = ближний бой, 2 = копьё).
    - attack_type (str): "piercing", "slashing", "blunt" (влияет на броню).
    - weapon_class (str): "dagger", "sword", "crossbow", "staff".
    - ammo_type (str): Тип боеприпаса ("bolt", "arrow").
    - two_handed (bool): Двуручное (блокирует слот OFF_HAND).
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ МЕТОДЫ:
    ----------------------------------------------------------------------
    - attack(actor, target): Рассчитать и применить урон.
    - repair(actor, tool): Починить (кузнец или инструмент).
    - poison(actor, ingredient): Отравить лезвие.
    - get_effective_damage(actor) -> int: Урон с учётом навыков.
    - has_ammo(actor) -> bool: Проверка наличия боеприпасов в инвентаре.
    - consume_ammo(actor): Потратить 1 боеприпас при выстреле.
    """
    
    def __init__(self, item_id: str, quantity: int = 1, requires_ammo: bool = False):
        """
        Создаёт экземпляр оружия.
        
        Параметр requires_ammo нужен не только для логики, но и для ItemCreator:
        утилита сканирует сигнатуру __init__ и автоматически генерирует
        чекбокс в форме редактирования предметов категории 'weapon'.
        
        Аргументы:
            item_id (str): ID предмета из items.json.
            quantity (int): Количество в стаке.
            requires_ammo (bool): Требует ли оружие боеприпасов.
                                  Дефолт = False, реальное значение
                                  читается из items.json ниже.
        """
        super().__init__(item_id, quantity)
        
        # Защита от дурака: проверяем, что категория правильная
        if self.category != ItemCategory.WEAPON:
            log.warning(
                f"WeaponItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'weapon'"
            )
        
        # Читаем специфичное поле из items.json.
        # Если его там нет (предмет создан давно) — используем дефолт.
        # Это позволяет добавлять новые поля в классы без миграции JSON.
        item_data = ItemData()
        props = item_data.get(item_id) or {}
        self.requires_ammo = bool(props.get("requires_ammo", requires_ammo))
    
    def use(self, actor, target=None):
        """
        Использование оружия = экипировать или атаковать.
        
        TODO (будущая логика):
        - Если оружие ещё не экипировано → экипировать в слот WEAPON.
        - Если уже экипировано и есть цель → начать атаку.
        - Если requires_ammo == True → проверить наличие боеприпасов.
        """
        log.info(f"WeaponItem: {actor.name} берёт в руки '{self.name}'")
        
        # Задел на будущее: проверка боеприпасов
        if self.requires_ammo:
            log.info(f"WeaponItem: '{self.name}' требует боеприпасов")
            # Здесь будет: self._check_ammo(actor)