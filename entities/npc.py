# entities/npc.py
# =============================================================================
# NPC (НЕИГРОВОЙ ПЕРСОНАЖ)
# Наследуется от Person. Содержит диалог и логику движения.
# =============================================================================

from entities.person import Person
from world.actor_data import ActorData
from logger import log


class NPC(Person):
    """
    NPC: стражник, крестьянин, торговец.
    """

    def __init__(self, npc_id: str, name: str, x: int, y: int,
                 dialog_id: str, gender: str = "male",
                 movement: str = "stationary", patrol_points: list = None,
                 move_delay_ms: int = 500):
        """
        Создаёт базового NPC
        Аргументы:
            id диалога
            движение и точки патрулирования
        """    
        super().__init__(
            actor_id=npc_id,
            name=name,
            gender=gender,
            x=x,
            y=y,
            max_weight=50.0,
        )

        self.dialog_id = dialog_id
        self.movement = movement
        self.patrol_points = patrol_points or []
        self.patrol_index = 0
        self.move_delay_ms = move_delay_ms

        self.path = []
        self.wait_until = 0
        self.follow_target = None

    @classmethod
    def from_actor_data(cls, npc_id: str, x: int, y: int):
        """Создаёт NPC из шаблона по npc_id в actors.json."""
        actor_data = ActorData()
        data = actor_data.get(npc_id)

        if not data:
            log.error(f"NPC.from_actor_data: данные для '{npc_id}' не найдены")
            return None

        npc = cls(
            npc_id=npc_id,
            name=data.get("name", "Безымянный"),
            x=x, y=y,
            dialog_id=data.get("dialog_id", ""),
            gender=data.get("gender", "male"),
        )

        npc.movement = data.get("movement", "stationary")
        npc.patrol_points = data.get("patrol_points", [])
        npc.move_delay_ms = data.get("move_delay_ms", 500)
        npc.follow_target = data.get("follow_target", None)

        return npc

    # =========================================================================
    # СЕРИАЛИЗАЦИЯ
    # =========================================================================

    def to_dict(self) -> dict:
        '''Сериализация'''
        data = super().to_dict()
        data.update({
            "dialog_id": self.dialog_id,
            "movement": self.movement,
            "patrol_points": self.patrol_points,
            "patrol_index": self.patrol_index,
            "path": list(self.path),
            "wait_until": self.wait_until,
            "follow_target": self.follow_target,
            "move_delay_ms": self.move_delay_ms,
        })
        return data

    @classmethod
    def from_dict(cls, data: dict):
        npc = cls(
            npc_id=data.get("id", "unknown"),
            name=data.get("name", "Безымянный"),
            x=data.get("x", 0),
            y=data.get("y", 0),
            dialog_id=data.get("dialog_id", ""),
            gender=data.get("gender", "male"),
        )
        npc.facing = data.get("facing", "south")
        npc.health = data.get("health", 100)
        npc.max_health = data.get("max_health", 100)
        npc.max_weight = data.get("max_weight", 50.0)
        npc.skills = dict(data.get("skills", {}))
        npc.faction = data.get("faction", "neutral")

        npc.movement = data.get("movement", "stationary")
        npc.patrol_points = data.get("patrol_points", [])
        npc.patrol_index = data.get("patrol_index", 0)
        npc.path = [tuple(p) for p in data.get("path", [])]
        npc.wait_until = data.get("wait_until", 0)
        npc.follow_target = data.get("follow_target", None)
        npc.move_delay_ms = data.get("move_delay_ms", 500)
        return npc