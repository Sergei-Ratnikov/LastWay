# entities/player.py

'''
ИГРОК (PLAYER)
Наследуется от Person. Имеет класс, инвентарь, максимальный вес.
ВАЖНО: humanity и days_left живут в GameState (единый источник истины)
'''

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
            класс игрока (влияет на лимит веса и доступы)
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

    # =========================================================================
    # СЕРИАЛИЗАЦИЯ
    # =========================================================================

    def to_dict(self) -> dict:
        '''Сериализация'''
        # humanity/days_left сюда НЕ входят — они в GameState
        data = super().to_dict()
        data.update({
            "player_class": self.player_class,
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
        player.skills = dict(data.get("skills", {}))
        player.faction = data.get("faction", "neutral")
        # Старые сейвы могут содержать "humanity"/"days_left" в player —
        # они игнорируются, GameState читает их из того же dict.
        return player