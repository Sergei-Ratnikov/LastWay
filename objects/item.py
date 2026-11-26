# objects/item.py

'''
БАЗОВЫЙ КЛАСС ПРЕДМЕТА
Экземпляр предмета. Данные-шаблон читаются из items.json по item_id.
Правила (можно ли надеть, сколько влезет, что делает use) — НЕ здесь,
а в systems/inventory_system.py и в наследниках use().
'''


from enum import Enum
from world.item_data import ItemData
from logger import log

# =============================================================================
# ПЕРЕЧИСЛЕНИЯ
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
    """Категория хранения (фиксируется в items.json, игрок не выбирает)."""
    ARCHIVE = "archive"
    CASKET = "casket"
    BURDEN = "burden"


class GenderRestriction(Enum):
    """Ограничение использования по полу."""
    ANY = "any"
    MALE = "male"
    FEMALE = "female"


class PaperDollSlot(Enum):
    """Слоты бумажной куклы (Paper Doll)."""
    CLOTHING = "clothing"
    PATCH = "patch"
    WEAPON = "weapon"
    TOOL = "tool"
    RING = "ring"
    AMULET = "amulet"


# =============================================================================
# БАЗОВЫЙ КЛАСС ПРЕДМЕТА
# =============================================================================

class Item:
    """
    Базовый класс для всех предметов (экземпляр / instance).
    Обязательные поля (name, category, storage_type) — fail-fast.
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
            log.error(f"Item: у предмета '{item_id}' ОТСУТСТВУЕТ 'name'!")
            raise ValueError(f"Missing required field 'name' for item '{item_id}'")

        category_str = props.get("category")
        if not category_str:
            log.error(f"Item: у предмета '{item_id}' ОТСУТСТВУЕТ 'category'!")
            raise ValueError(f"Missing required field 'category' for item '{item_id}'")
        try:
            self.category = ItemCategory(category_str)
        except ValueError:
            log.error(f"Item: неизвестная категория '{category_str}' у '{item_id}'!")
            raise ValueError(f"Unknown category '{category_str}' for item '{item_id}'")

        storage_str = props.get("storage_type")
        if not storage_str:
            log.error(f"Item: у предмета '{item_id}' ОТСУТСТВУЕТ 'storage_type'!")
            raise ValueError(f"Missing required field 'storage_type' for item '{item_id}'")
        try:
            self.storage_type = StorageType(storage_str)
        except ValueError:
            log.error(f"Item: неизвестный storage_type '{storage_str}' у '{item_id}'!")
            raise ValueError(f"Unknown storage_type '{storage_str}' for item '{item_id}'")

        # --- 2. ЧИСЛОВЫЕ И ЛОГИЧЕСКИЕ ХАРАКТЕРИСТИКИ ---
        self.weight = float(props.get("weight", 0.0))
        self.volume = int(props.get("volume", 1))
        self.equippable = bool(props.get("equippable", False))
        self.cost = int(props.get("cost", 0))

        # Максимальный размер стака. 1 = предметы не стекутся (дефолт).
        # Для стрел/зелий/ингредиентов в items.json можно указать, например, 20.
        self.max_stack = max(1, int(props.get("max_stack", 1)))

        # Требования для экипировки (опционально):
        # {"strength": 10, "class": ["Идальго"]}
        self.requirements: dict = dict(props.get("requirements", {}))

        # Эффекты расходника (опционально):
        # {"health": 20, "humanity": -5, "hunger": 30}
        self.effects: dict = dict(props.get("effects", {}))

        gender_str = props.get("gender_restrict", "any")
        try:
            self.gender_restrict = GenderRestriction(gender_str)
        except ValueError:
            log.error(f"Item: неизвестный gender_restrict '{gender_str}' для {item_id}")
            raise ValueError(f"Unknown gender_restrict '{gender_str}' for item '{item_id}'")

        # --- 3. ДИНАМИЧЕСКИЕ ХАРАКТЕРИСТИКИ ---
        self.durability = int(props.get("durability", 100))
        self.is_stolen = False
        self.custom_name = None

        log.info(f"Item: создан экземпляр '{self.name}' (ID: {item_id}, x{quantity})")

    # =========================================================================
    # ИСПОЛЬЗОВАНИЕ (переопределяется в наследниках)
    # =========================================================================

    def use(self, actor, engine=None) -> bool:
        """
        Базовое использование. Наследники переопределяют.
        Возвращает True, если предмет был применён (и, возможно, израсходован).
        Удаление из инвентаря при quantity<=0 — ответственность InventorySystem.
        """
        log.info(f"Item: {actor.name} использует {self.name}")
        return False

    # =========================================================================
    # СЕРИАЛИЗАЦИЯ
    # =========================================================================

    def to_dict(self):
        """Сериализует экземпляр предмета в словарь для JSON."""
        return {
            "id": self.id,
            "quantity": self.quantity,
            "durability": self.durability,
            "is_stolen": self.is_stolen,
            "custom_name": self.custom_name,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Десериализует предмет через фабрику create_item."""
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
    Фабрика предметов. Читает category из items.json и создаёт экземпляр
    соответствующего класса-наследника. Локальные импорты — против циклов.
    """
    item_data = ItemData()
    props = item_data.get(item_id)

    if not props:
        log.error(f"create_item: '{item_id}' не найден, возвращаю базовый Item")
        return Item(item_id, quantity)

    category_str = props.get("category")

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