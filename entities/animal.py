# entities/animal.py
# =============================================================================
# ЖИВОТНОЕ (ANIMAL)
# Наследуется от Actor. Имеет потребности (еда, сон, игры).
# =============================================================================

from entities.actor import Actor
from logger import log


class Animal(Actor):
    """
    Животное: кошка, собака, крыса.
    Имеет emergent-потребности и точки интереса.
    """
    
    def __init__(self, animal_id: str, name: str, x: int, y: int, 
                 species: str = "cat", behavior_type: str = "emergent_needs",
                 gender: str = "male"):
        """
        Создаёт животное.
        
        Аргументы:
            animal_id (str): Уникальный идентификатор.
            name (str): Имя/кличка (например, "Мурка").
            x, y (int): Начальная позиция.
            species (str): Вид ("cat", "dog", "rat").
            behavior_type (str): Тип поведения ("emergent_needs").
            gender (str): Пол.
        """
        # FIX: name и gender передаём в базовый класс
        super().__init__(actor_id=animal_id, name=name, gender=gender, x=x, y=y)
        
        self.species = species
        self.behavior_type = behavior_type
        
        # Потребности (0-100)
        self.hunger = 50
        self.energy = 80
        self.boredom = 30
        self.wanderlust = 0
        
        # Эмоции
        self.fear = 0
        self.aggression = 0
        
        # Точки интереса: {"food": (x,y), "home": (x,y), "toy": (x,y)}
        self.points_of_interest: dict[str, tuple | None] = {
            "food": None,
            "home": None,
            "toy": None,
        }
        
        # Текущее действие
        self.action = "idle"  # "idle", "moving", "eating", "sleeping", "playing"
        self.target: tuple | None = None
        self.action_timer = 0
        self.path: list[tuple[int, int]] = []
    
    def update_needs(self, current_time: int):
        """
        Обновляет потребности животного с течением времени.
        Вызывается каждый кадр из Map.update_animals().
        """
        # Простая модель: каждые 5 секунд меняем потребности
        if current_time - self.last_move_time < 5000:
            return
        self.last_move_time = current_time
        
        # Голод растёт, энергия падает, скука растёт
        self.hunger = min(100, self.hunger + 1)
        self.energy = max(0, self.energy - 1)
        self.boredom = min(100, self.boredom + 1)
    
    def decide_action(self, current_map):
        """Принимает решение о следующем действии (упрощённо)."""
        # Определяем приоритетную потребность
        if self.hunger > 70 and self.points_of_interest["food"]:
            self.target = self.points_of_interest["food"]
            self.action = "moving"
        elif self.energy < 30 and self.points_of_interest["home"]:
            self.target = self.points_of_interest["home"]
            self.action = "moving"
        elif self.boredom > 60 and self.points_of_interest["toy"]:
            self.target = self.points_of_interest["toy"]
            self.action = "moving"
        else:
            self.action = "idle"
    
    def move_towards_target(self, current_map, current_time: int):
        """Двигается к цели, если есть путь."""
        if self.action != "moving" or self.target is None:
            return
        
        if not self.path and self.target != (self.x, self.y):
            # TODO: построить путь через pathfinding
            pass
    
    # =========================================================================
    # СЕРИАЛИЗАЦИЯ
    # =========================================================================
    
    def to_dict(self) -> dict:
        """Расширяем базовую сериализацию полями животного."""
        data = super().to_dict()
        # Преобразуем tuple в list для JSON
        poi_serializable = {}
        for key, value in self.points_of_interest.items():
            poi_serializable[key] = list(value) if value else None
        
        data.update({
            "species": self.species,
            "behavior_type": self.behavior_type,
            "hunger": self.hunger,
            "energy": self.energy,
            "boredom": self.boredom,
            "wanderlust": self.wanderlust,
            "fear": self.fear,
            "aggression": self.aggression,
            "points_of_interest": poi_serializable,
            "action": self.action,
            "target": list(self.target) if self.target else None,
            "action_timer": self.action_timer,
            "path": list(self.path),
        })
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        """Создаёт животное из словаря."""
        animal = cls(
            animal_id=data.get("id", "unknown"),
            name=data.get("name", "Животное"),
            x=data.get("x", 0),
            y=data.get("y", 0),
            species=data.get("species", "cat"),
            behavior_type=data.get("behavior_type", "emergent_needs"),
            gender=data.get("gender", "male"),
        )
        animal.facing = data.get("facing", "south")
        animal.hunger = data.get("hunger", 50)
        animal.energy = data.get("energy", 80)
        animal.boredom = data.get("boredom", 30)
        animal.wanderlust = data.get("wanderlust", 0)
        animal.fear = data.get("fear", 0)
        animal.aggression = data.get("aggression", 0)
        # Восстанавливаем points_of_interest с tuple
        for key, value in data.get("points_of_interest", {}).items():
            if isinstance(value, list):
                animal.points_of_interest[key] = tuple(value)
        animal.action = data.get("action", "idle")
        if data.get("target") and isinstance(data["target"], list):
            animal.target = tuple(data["target"])
        animal.path = [tuple(p) for p in data.get("path", [])]
        return animal