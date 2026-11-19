# objects/item_ingredient.py

from objects.item import Item, ItemCategory
from logger import log


class IngredientItem(Item):
    """
    Ингредиенты (травы, краски, пергамент, порох).
    Собираются в целое (крафт/алхимия) и исчезают.
    Хранятся в Поклаже.
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ АТРИБУТЫ:
    ----------------------------------------------------------------------
    - properties (list[str]): ["healing", "poison", "flammable", "dye_red"].
    - freshness (int): Свежесть (для трав, влияет на силу эффекта).
    - rarity (str): "common", "rare", "exotic".
    - alchemy_category (str): "herb", "mineral", "animal", "chemical".
    
    ----------------------------------------------------------------------
    БУДУЩИЕ СПЕЦИФИЧНЫЕ МЕТОДЫ:
    ----------------------------------------------------------------------
    - combine_with(other_ingredient, tool) -> Item: Крафт/алхимия.
    - grind(actor, tool) -> IngredientItem: Измельчить (ступа).
    - distill(actor, tool) -> IngredientItem: Дистиллировать.
    - get_compatible_recipes() -> list: С чем сочетается.
    """
    
    def __init__(self, item_id: str, quantity: int = 1):
        super().__init__(item_id, quantity)
        
        if self.category != ItemCategory.INGREDIENT:
            log.warning(
                f"IngredientItem: создан для '{item_id}' с категорией {self.category.value}, "
                f"ожидалось 'ingredient'"
            )
    
    def use(self, actor, target=None):
        """Ингредиент требует сочетания с другим предметом."""
        log.info(f"IngredientItem: {actor.name} перебирает '{self.name}'")
        # Будущая логика: открыть окно крафта/алхимии.
        pass