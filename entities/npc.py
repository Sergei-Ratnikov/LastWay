# entities/npc.py
# =============================================================================
# NPC (НЕИГРОВОЙ ПЕРСОНАЖ)
# =============================================================================

from entities.actor import Actor
from world.actor_data import ActorData
from logger import log


class NPC(Actor):
    """
    НПС: стражник, крестьянин, монах, торговец.
    Имеет диалог, может патрулировать маршрут.
    """
    
    def __init__(self, npc_id: str, name: str, x: int, y: int, 
                 dialog_id: str, gender: str = "male",
                 movement: str = "stationary", patrol_points: list = None,
                 move_delay_ms: int = 500):
        """
        Создаёт NPC.
        
        Аргументы:
            npc_id (str): Уникальный идентификатор NPC.
            name (str): Имя.
            x, y (int): Начальная позиция.
            dialog_id (str): ID диалога.
            gender (str): Пол.
            movement (str): Тип поведения ("stationary" или "patrol").
            patrol_points (list): Список точек патруля [[x, y], ...].
            move_delay_ms (int): Задержка между шагами.
        """
        super().__init__(actor_id=npc_id, name=name, gender=gender, x=x, y=y)
        
        self.dialog_id = dialog_id
        self.movement = movement
        self.patrol_points = patrol_points or []
        self.patrol_index = 0
        self.move_delay_ms = move_delay_ms
        
        # Путь к следующей точке патруля
        self.path = []
        self.wait_until = 0

        # следование за целью
        self.follow_target = None

    @classmethod
    def from_actor_data(cls, npc_id: str, x: int, y: int):
        """
        Создаёт NPC из данных actors.json.
        
        Аргументы:
            npc_id (str): ID персонажа из actors.json.
            x, y (int): Начальная позиция (из location.json).
            
        Возвращает:
            NPC: Созданный экземпляр или None, если данные не найдены.
        """
        from world.actor_data import ActorData
        actor_data = ActorData()
        data = actor_data.get(npc_id)
        
        if not data:
            log.error(f"NPC.from_actor_data: данные для '{npc_id}' не найдены в actors.json")
            return None
        
        npc = cls(
            npc_id=npc_id,
            name=data.get("name", "Безымянный"),
            x=x,
            y=y,
            dialog_id=data.get("dialog_id", ""),
            gender=data.get("gender", "male"),
        )
        
        # Дополнительные параметры поведения
        npc.movement = data.get("movement", "stationary")
        npc.patrol_points = data.get("patrol_points", [])
        npc.move_delay_ms = data.get("move_delay_ms", 500)
        npc.follow_target = data.get("follow_target", None)
        
        return npc

    # =========================================================================
    # СЕРИАЛИЗАЦИЯ
    # =========================================================================
    def to_dict(self) -> dict:
        """Расширяем базовую сериализацию полями NPC."""
        data = super().to_dict()
        data.update({
            "dialog_id": self.dialog_id,
            "movement": self.movement,
            "patrol_points": self.patrol_points,
            "patrol_index": self.patrol_index,
            "path": list(self.path),
        })
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        """Создаёт NPC из словаря (для сохранений)."""
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
        npc.movement = data.get("movement", "stationary")
        npc.patrol_points = data.get("patrol_points", [])
        npc.patrol_index = data.get("patrol_index", 0)
        npc.path = [tuple(p) for p in data.get("path", [])]
        return npc