# entities/actor.py
# =============================================================================
# БАЗОВЫЙ КЛАСС ACTOR
# Общий предок для Player, NPC, Animal.
# Содержит общие атрибуты: позиция, здоровье, направление взгляда.
# =============================================================================

from logger import log


class Actor:
    """
    Базовый класс для всех живых существ в игре.
    Содержит общие поля: ID, имя, пол, позиция, здоровье, направление.
    """
    
    def __init__(self, actor_id: str, name: str, gender: str, x: int = 0, y: int = 0):
        """
        Создаёт базового актёра.
        
        Аргументы:
            actor_id (str): Уникальный идентификатор.
            name (str): Имя/название (отображается над головой).
            gender (str): Пол ("male", "female", "any").
            x, y (int): Координаты на карте.
        """
        self.id = actor_id
        self.name = name
        self.gender = gender
        self.x = x
        self.y = y
        
        # Здоровье
        self.health = 100
        self.max_health = 100
        
        # Направление взгляда (для линии взгляда в renderer)
        self.facing = "south"
        
        # Параметры движения
        self.move_delay_ms = 500
        self.last_move_time = 0
        self.last_door_pos = None
    
    # =========================================================================
    # НАПРАВЛЕНИЕ ВЗГЛЯДА
    # =========================================================================
    
    def get_facing_delta(self) -> tuple[int, int]:
        """
        Возвращает смещение (dx, dy) в направлении взгляда.
        
        Возвращает:
            tuple[int, int]: (dx, dy) — 0, ±1.
        """
        deltas = {
            "north": (0, -1),
            "south": (0, 1),
            "east":  (1, 0),
            "west":  (-1, 0),
        }
        return deltas.get(self.facing, (0, 1))
    
    def set_facing(self, direction: str):
        """
        Устанавливает направление взгляда.
        
        Аргументы:
            direction (str): "north", "south", "east", "west".
        """
        if direction in ("north", "south", "east", "west"):
            self.facing = direction

    def set_facing_from_delta(self, dx: int, dy: int):
        """
        Устанавливает направление взгляда на основе вектора движения.
        Используется при движении NPC и игрока.
        
        Аргументы:
            dx, dy (int): Смещение по X и Y (обычно -1, 0 или 1).
        """
        if abs(dx) > abs(dy):
            # Горизонтальное движение доминирует
            direction = "east" if dx > 0 else "west"
        elif abs(dy) > abs(dx):
            # Вертикальное движение доминирует
            direction = "south" if dy > 0 else "north"
        else:
            # Движения нет или диагональное — не меняем направление
            return
        
        self.set_facing(direction)

    # =========================================================================
    # ЗДОРОВЬЕ
    # =========================================================================
    def take_damage(self, amount: int) -> bool:
        """
        Наносит урон. Возвращает True, если существо погибло.
        """
        self.health = max(0, self.health - amount)
        return self.health <= 0
    
    def heal(self, amount: int):
        """Лечит на указанное количество (не выше max_health)."""
        self.health = min(self.max_health, self.health + amount)
    
    def is_dead(self) -> bool:
        """Проверяет, живо ли существо."""
        return self.health <= 0
    
    # =========================================================================
    # СЕРИАЛИЗАЦИЯ (базовая)
    # =========================================================================
    def to_dict(self) -> dict:
        """
        Базовая сериализация для сохранений.
        Наследники дополняют этот словарь своими полями.
        """
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "facing": self.facing,
            "gender": self.gender,
            "health": self.health,
            "max_health": self.max_health,
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """
        Базовая десериализация.
        Наследники должны переопределить этот метод и вызвать super().
        """
        actor = cls(
            actor_id=data.get("id", "unknown"),
            name=data.get("name", "Безымянный"),
            gender=data.get("gender", "any"),
            x=data.get("x", 0),
            y=data.get("y", 0),
        )
        actor.facing = data.get("facing", "south")
        actor.health = data.get("health", 100)
        actor.max_health = data.get("max_health", 100)
        return actor