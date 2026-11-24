# entities/person.py
# =============================================================================
# БАЗОВЫЙ КЛАСС PERSON
# Общий предок для людей: Player, NPC, (позже) Companion, KeyCharacter.
# Содержит общие для людей свойства: переносимый вес, навыки, фракция.
# =============================================================================

from entities.actor import Actor

class Person(Actor):
    def __init__(self, actor_id: str, name: str, gender: str,
                 x: int = 0, y: int = 0, max_weight: float = 50.0):
        super().__init__(actor_id=actor_id, name=name, gender=gender, x=x, y=y)
        self.max_weight = max_weight
        self.skills: dict[str, int] = {}
        self.faction: str = "neutral"

    # =========================================================================
    # СЕРИАЛИЗАЦИЯ (расширяет Actor)
    # =========================================================================
    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "max_weight": self.max_weight,
            "skills": dict(self.skills),
            "faction": self.faction,
        })
        return data

    @classmethod
    def from_dict(cls, data: dict):
        person = cls(
            actor_id=data.get("id", "unknown"),
            name=data.get("name", "Безымянный"),
            gender=data.get("gender", "any"),
            x=data.get("x", 0),
            y=data.get("y", 0),
            max_weight=data.get("max_weight", 50.0),
        )
        person.facing = data.get("facing", "south")
        person.health = data.get("health", 100)
        person.max_health = data.get("max_health", 100)
        person.skills = dict(data.get("skills", {}))
        person.faction = data.get("faction", "neutral")
        return person