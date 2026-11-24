# objects/item.py

# базовый класс предмета

from enum import Enum
from world.item_data import ItemData
from logger import log

# =============================================================================
# ПЕРЕЧИСЛЕНИЯ (ENUM) ДЛЯ ТИПИЗАЦИИ
# =============================================================================

class ItemCategory(Enum):
    """Категория предмета (определяет наследника класса)."""
    DOCUMENT = "document"
    KEY = "key"
    QUEST = "quest"
    CLOTHING = "clothing"
    WEAPON = "weapon"
    CONSUMABLE = "consumable"
    TOOL = "tool"
    VALUABLE = "valuable"
    INGREDIENT = "ingredient"
    JEWELRY = "jewelry"
    AMMO = "ammo"


class StorageType(Enum):
    """Категория хранения (Архив, Ларец, Поклажа)."""
    ARCHIVE = "archive"
    CASKET = "casket"
    BURDEN = "burden"


class GenderRestriction(Enum):
    """Ограничение использования по полу."""
    ANY = "any"
    MALE = "male"
    FEMALE = "female"


class PaperDollSlot(Enum):
    """
    Слоты бумажной куклы (Paper Doll) для экипировки.
    Используется одеждой, оружием, инструментами и украшениями.
    """
    CLOTHING = "clothing"    # Одежда (ряса, бригантина, платье)
    PATCH = "patch"          # Нашивка (знак инквизиции, цеховой символ)
    WEAPON = "weapon"        # Оружие (основная рука)
    TOOL = "tool"            # Инструмент (отмычки, фонарь)
    RING = "ring"            # Кольцо / перстень
    AMULET = "amulet"        # Подвеска / амулет / крест


# =============================================================================
# БАЗОВЫЙ КЛАСС ПРЕДМЕТА
# =============================================================================

class Item:
    """
    Базовый класс для всех предметов в игре (Экземпляр / Instance).
    Обязательные поля (name, category, storage_type) не имеют значений по умолчанию.
    При их отсутствии выбрасывается ValueError (Fail-fast подход).
    """
    
    def __init__(self, item_id: str, quantity: int = 1):
        self.id = item_id
        self.quantity = quantity
        
        item_data = ItemData()
        props = item_data.get(item_id)
        
        if not props:
            log.error(f"Item: предмет '{item_id}' не найден в items.json")
            raise ValueError(f"Item '{item_id}' not found in items.json")
        
        # --- 1. ОБЯЗАТЕЛЬНЫЕ ПОЛЯ (FAIL-FAST) ---
        
        self.name = props.get("name")
        if not self.name:
            log.error(f"Item: у предмета '{item_id}' ОТСУТСТВУЕТ обязательное поле 'name'!")
            raise ValueError(f"Missing required field 'name' for item '{item_id}'")
        
        category_str = props.get("category")
        if not category_str:
            log.error(f"Item: у предмета '{item_id}' ОТСУТСТВУЕТ обязательное поле 'category'!")
            raise ValueError(f"Missing required field 'category' for item '{item_id}'")
        try:
            self.category = ItemCategory(category_str)
        except ValueError:
            log.error(f"Item: у предмета '{item_id}' неизвестная категория '{category_str}'!")
            raise ValueError(f"Unknown category '{category_str}' for item '{item_id}'")
            
        storage_str = props.get("storage_type")
        if not storage_str:
            log.error(f"Item: у предмета '{item_id}' ОТСУТСТВУЕТ обязательное поле 'storage_type'!")
            raise ValueError(f"Missing required field 'storage_type' for item '{item_id}'")
        try:
            self.storage_type = StorageType(storage_str)
        except ValueError:
            log.error(f"Item: у предмета '{item_id}' неизвестный storage_type '{storage_str}'!")
            raise ValueError(f"Unknown storage_type '{storage_str}' for item '{item_id}'")

        # --- 2. ЧИСЛОВЫЕ И ЛОГИЧЕСКИЕ ХАРАКТЕРИСТИКИ ---
        self.weight = float(props.get("weight", 0.0))
        self.volume = int(props.get("volume", 1))
        self.equippable = bool(props.get("equippable", False))
        self.cost = int(props.get("cost", 0))
        
        gender_str = props.get("gender_restrict", "any")
        try:
            self.gender_restrict = GenderRestriction(gender_str)
        except ValueError:
            log.error(f"Item: неизвестный gender_restrict '{gender_str}' для {item_id}")
            raise ValueError(f"Unknown gender_restrict '{gender_str}' for item '{item_id}'")
            
        # --- 3. ДИНАМИЧЕСКИЕ ХАРАКТЕРИСТИКИ (меняются в процессе игры) ---
        self.durability = int(props.get("durability", 100))
        self.is_stolen = False
        self.custom_name = None
        
        log.info(f"Item: создан экземпляр '{self.name}' (ID: {item_id}, x{quantity})")

    # =========================================================================
    # МЕТОДЫ-ЗАГЛУШКИ (БУДУТ ПЕРЕОПРЕДЕЛЕНЫ В НАСЛЕДНИКАХ)
    # =========================================================================
    
    def pick_up(self, actor):
        """Логика подбора предмета актёром."""
        log.info(f"Item: {actor.name} подбирает {self.name}")
        if hasattr(actor, 'inventory'):
            current_weight = actor.inventory.get_total_weight()
            if current_weight + (self.weight * self.quantity) > actor.max_weight:
                log.info(f"Item: {self.name} не влез (превышен вес)")
                return False
        return True
    
    # def drop(self, actor, current_map, x: int, y: int):
    #     """Логика выбрасывания предмета на землю."""
    #     log.info(f"Item: {actor.name} бросает {self.name} на ({x},{y})")
    #     from objects.drop import ItemDrop
    #     drop = ItemDrop(
    #         drop_id=f"drop_{id(self)}",
    #         x=x, y=y,
    #         items=[self.id] * self.quantity
    #     )
    #     current_map.drops.append(drop)
    #     return True

    # Item.drop() удалён: был сломан (создавал ItemDrop со строками вместо
    # объектов Item) и не использовался. Выброс предмета реализован в
    # InventoryMenu._on_drop → Map.add_or_update_drop.


    
    def use(self, actor, target=None):
        """Базовое использование предмета."""
        log.info(f"Item: {actor.name} использует {self.name}")
        pass
    
    def transfer(self, from_inventory, to_inventory):
        """Передача предмета между инвентарями."""
        log.info(f"Item: передача {self.name} между инвентарями")
        if to_inventory.get_total_weight() + (self.weight * self.quantity) > to_inventory.max_weight:
            log.info(f"Item: {self.name} не влез в целевой инвентарь")
            return False
        return True
    
    # =========================================================================
    # СЕРИАЛИЗАЦИЯ ДЛЯ СОХРАНЕНИЙ
    # =========================================================================
    
    def to_dict(self):
        """Сериализует экземпляр предмета в словарь для JSON."""
        return {
            "id": self.id,
            "quantity": self.quantity,
            "durability": self.durability,
            "is_stolen": self.is_stolen,
            "custom_name": self.custom_name
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """
        Десериализует предмет из словаря.
        Использует фабрику create_item для создания правильного класса-наследника.
        """
        item = create_item(
            item_id=data.get("id"),
            quantity=data.get("quantity", 1)
        )
        item.durability = data.get("durability", 100)
        item.is_stolen = data.get("is_stolen", False)
        item.custom_name = data.get("custom_name", None)
        return item
    
    def __repr__(self):
        return f"<Item: {self.name} (ID: {self.id}, x{self.quantity})>"


# =============================================================================
# ФАБРИКА ПРЕДМЕТОВ
# =============================================================================

def create_item(item_id: str, quantity: int = 1) -> Item:
    """
    Фабрика предметов.
    Читает category из items.json и создаёт экземпляр соответствующего класса-наследника.
    
    Локальные импорты нужны, чтобы избежать циклических зависимостей:
    наследники импортируют Item из этого файла, а мы импортируем их только здесь.
    
    Аргументы:
        item_id (str): ID предмета из items.json.
        quantity (int): Количество в стаке.
        
    Возвращает:
        Item: Экземпляр нужного класса-наследника (или базового Item при ошибке).
    """
    # Загружаем данные предмета для определения категории
    item_data = ItemData()
    props = item_data.get(item_id)
    
    if not props:
        log.error(f"create_item: '{item_id}' не найден в items.json, возвращаю базовый Item")
        return Item(item_id, quantity)
    
    category_str = props.get("category")
    
    # Локальные импорты наследников (избегаем циклических зависимостей)
    from objects.item_document import DocumentItem
    from objects.item_key import KeyItem
    from objects.item_quest import QuestItem
    from objects.item_clothing import ClothingItem
    from objects.item_weapon import WeaponItem
    from objects.item_consumable import ConsumableItem
    from objects.item_tool import ToolItem
    from objects.item_valuable import ValuableItem
    from objects.item_ingredient import IngredientItem
    from objects.item_jewelry import JewelryItem
    
    # Маппинг категории -> класс
    category_to_class = {
        "document": DocumentItem,
        "key": KeyItem,
        "quest": QuestItem,
        "clothing": ClothingItem,
        "weapon": WeaponItem,
        "consumable": ConsumableItem,
        "tool": ToolItem,
        "valuable": ValuableItem,
        "ingredient": IngredientItem,
        "jewelry": JewelryItem,
    }
    
    item_class = category_to_class.get(category_str, Item)
    
    try:
        return item_class(item_id, quantity)
    except Exception as e:
        log.error(f"create_item: ошибка создания {category_str} для '{item_id}': {e}")
        return Item(item_id, quantity)