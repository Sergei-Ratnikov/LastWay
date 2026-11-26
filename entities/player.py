# entities/player.py
# =============================================================================
# ИГРОК (PLAYER)
# Наследуется от Person. Имеет класс, инвентарь, максимальный вес.
# =============================================================================

from entities.person import Person
from logger import log


class Player(Person):
    """
    Персонаж игрока
    """

    def __init__(self, x: int = 0, y: int = 0, player_class: str = "Идальго",
                 name: str = "Герой", gender: str = "male"):
        """
        Создаёт персонажа.
        Аргументы:
            человечность
            число прожитых дней
        """
        super().__init__(
            actor_id="player",
            name=name,
            gender=gender,
            x=x,
            y=y,
            max_weight=50.0,
        )
        self.player_class = player_class
        self.humanity = 50
        self.days_left = 14

    # =========================================================================
    # СЕРИАЛИЗАЦИЯ
    # =========================================================================

    def to_dict(self) -> dict:
        '''Сериализация'''
        data = super().to_dict()
        data.update({
            "player_class": self.player_class,
            # Humanity и days_left теперь живут в Player (единый источник истины
            # для сохранений). GameState.humanity остаётся как зеркало для
            # удобства UI/диалогов — синхронизируется при загрузке.
            "humanity": self.humanity,
            "days_left": self.days_left,
        })
        return data

    @classmethod
    def from_dict(cls, data: dict):
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
        player.humanity = data.get("humanity", 50)
        player.days_left = data.get("days_left", 14)
        player.skills = dict(data.get("skills", {}))
        player.faction = data.get("faction", "neutral")
        return player