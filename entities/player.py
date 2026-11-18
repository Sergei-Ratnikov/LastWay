# entities/player.py
# =============================================================================
# КЛАСС ИГРОКА (PLAYER)
# Описывает персонажа игрока. Наследуется от Person.
# Содержит систему классов персонажа и дополнительные механики.
# =============================================================================

from entities.person import Person


class Player(Person):
    """
    Класс игрока. Управляется пользователем.
    Наследует свойства Person (и Actor).
    """
    
    # Таблица максимального веса по классам
    # TODO: Перенести в JSON классов (data/classes.json)
    CLASS_MAX_WEIGHT = {
        "Идальго": 50.0,
        "Геркулес": 80.0,
        "Аббатисса": 30.0
    }
    
    def __init__(self, player_class="Идальго", gender="male"):
        """
        Инициализация игрока.
        
        Аргументы:
            player_class (str): Класс персонажа ("Идальго", "Геркулес", "Аббатисса").
            gender (str): Пол персонажа.
        """
        # Вызываем конструктор Person
        # ID и координаты будут установлены позже (при загрузке карты/сохранения)
        super().__init__(
            person_id="player",
            name="Герой",
            x=0,
            y=0,
            gender=gender
        )
        
        # Класс персонажа
        # ВАЖНО: используем player_class, т.к. "class" — зарезервированное слово в Python
        self.player_class = player_class
        
        # Максимальный вес — вычисляется из класса
        self.max_weight = self.CLASS_MAX_WEIGHT.get(player_class, 50.0)
        
        # TODO: Добавить в будущем
        # - humanity (человечность) — пока в GameState
        # - days_left (дней до восстания) — пока в GameState
        # - inventory (ссылка на Inventory) — пока в GameState
        # - skills (навыки: взлом, убеждение и т.д.)
    
    # -------------------------------------------------------------------------
    # СЕРИАЛИЗАЦИЯ ДЛЯ СОХРАНЕНИЙ
    # -------------------------------------------------------------------------
    
    def to_dict(self):
        """
        Сериализует игрока в словарь для сохранения в JSON.
        
        Возвращает:
            dict: Словарь с данными игрока.
        """
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "facing": self.facing,
            "gender": self.gender,
            "player_class": self.player_class,
            "max_weight": self.max_weight,
            "health": self.health,
            "max_health": self.max_health,
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Десериализует игрока из словаря (загруженного из JSON).
        
        Аргументы:
            data (dict): Словарь с данными игрока.
        
        Возвращает:
            Player: Новый экземпляр игрока с восстановленными данными.
        """
        player = cls(
            player_class=data.get("player_class", data.get("class", "Идальго")),
            gender=data.get("gender", "male")
        )
        player.id = data.get("id", "player")
        player.name = data.get("name", "Герой")
        player.x = data.get("x", 0)
        player.y = data.get("y", 0)
        player.facing = data.get("facing", "south")
        player.max_weight = data.get("max_weight", cls.CLASS_MAX_WEIGHT.get(player.player_class, 50.0))
        player.health = data.get("health", 100)
        player.max_health = data.get("max_health", 100)
        return player
    
    # -------------------------------------------------------------------------
    # МЕТОДЫ-ЗАГОТОВКИ (БУДУТ РЕАЛИЗОВАНЫ ПОЗЖЕ)
    # -------------------------------------------------------------------------
    
    # def move(self, dx, dy, current_map):
    #     """Движение игрока."""
    #     pass
    
    # def interact(self, current_map):
    #     """Взаимодействие с объектом перед игроком."""
    #     pass
    
    # def attack(self, target):
    #     """Атака цели."""
    #     pass
    
    # def use_item(self, item):
    #     """Использование предмета."""
    #     pass
    
    # def rest(self):
    #     """Отдых (проходит время)."""
    #     pass