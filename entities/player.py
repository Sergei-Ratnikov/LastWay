# entities/player.py
# =============================================================================
# ИГРОК (PLAYER)
# Наследуется от Actor. Имеет класс, инвентарь, максимальный вес.
# =============================================================================

from entities.actor import Actor
from logger import log


class Player(Actor):
    """
    Игрок. Наследуется от Actor.
    Содержит player_class, max_weight и связанные с классом атрибуты.
    """
    
    def __init__(self, x: int = 0, y: int = 0, player_class: str = "Идальго",
                 name: str = "Герой", gender: str = "male"):
        """
        Создаёт игрока.
        
        Аргументы:
            x, y (int): Начальная позиция.
            player_class (str): Класс персонажа ("Идальго", "Священник" и т.д.).
            name (str): Имя (по умолчанию "Герой").
            gender (str): Пол ("male", "female").
        """
        # FIX: name и gender передаём в базовый класс
        super().__init__(actor_id="player", name=name, gender=gender, x=x, y=y)
        
        self.player_class = player_class
        
        # Максимальный переносимый вес (зависит от класса)
        self.max_weight = 50.0
        
        # Социальные характеристики (задел на будущее)
        self.humanity = 50
        self.days_left = 14
    
    # =========================================================================
    # СЕРИАЛИЗАЦИЯ
    # =========================================================================
    
    def to_dict(self) -> dict:
        """Расширяем базовую сериализацию полями игрока."""
        data = super().to_dict()
        data.update({
            "player_class": self.player_class,
            "max_weight": self.max_weight,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        """Создаёт игрока из словаря (для загрузок)."""
        player = cls(
            x=data.get("x", 0),
            y=data.get("y", 0),
            player_class=data.get("player_class", "Идальго"),
            name=data.get("name", "Герой"),
            gender=data.get("gender", "male"),
        )
        player.facing = data.get("facing", "south")
        player.health = data.get("health", 100)
        player.max_health = data.get("max_health", 100)
        player.max_weight = data.get("max_weight", 50.0)
        return player