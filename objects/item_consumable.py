# objects/item_consumable.py

'''
ConsumableItem - Расходники (еда, вино, бинты). 
Применяют effects к существу/состоянию игры.
'''


from objects.item import Item, ItemCategory
from logger import log


class ConsumableItem(Item):
    """
    Расходник. Эффекты берутся из items.json -> effects:
        {"health": 20, "humanity": -5, "hunger": 30}
    health  > 0 — лечит, < 0 — наносит урон.
    humanity — пишется в GameState (единый источник истины).
    hunger  — пока поддерживается только у Animal (у Player поля нет),
              для Player молча игнорируется.
    """

    def __init__(self, item_id: str, quantity: int = 1):
        super().__init__(item_id, quantity)
        if self.category != ItemCategory.CONSUMABLE:
            log.warning(
                f"ConsumableItem: создан для '{item_id}' с категорией "
                f"{self.category.value}, ожидалось 'consumable'"
            )

    def use(self, actor, engine=None) -> bool:
        """
        Применяет эффекты. Уменьшает quantity на 1.
        Удаление из инвентаря при quantity<=0 — делает InventorySystem.
        Возвращает True, если эффекты применены.
        """
        if not self.effects:
            log.info(f"ConsumableItem: у '{self.name}' нет effects, использование пустое")
            return False

        log.info(f"ConsumableItem: {actor.name} использует '{self.name}', "
                 f"effects={self.effects}")

        for key, value in self.effects.items():
            if key == "health":
                if value >= 0:
                    actor.heal(value)
                else:
                    actor.take_damage(-value)
                log.info(f"  health {value:+d} -> {actor.health}/{actor.max_health}")
            elif key == "humanity" and engine is not None:
                gs = engine.game_state
                gs.humanity = max(0, min(100, gs.humanity + value))
                log.info(f"  humanity {value:+d} -> {gs.humanity}")
            elif key == "hunger" and hasattr(actor, "hunger"):
                actor.hunger = max(0, min(100, actor.hunger + value))
                log.info(f"  hunger {value:+d} -> {actor.hunger}")
            else:
                log.info(f"  эффект '{key}' не поддержан для этого актёра")

        self.quantity -= 1
        return True