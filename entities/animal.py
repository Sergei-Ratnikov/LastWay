# entities/animal.py
# =============================================================================
# БАЗОВЫЙ КЛАСС ANIMAL
# Описывает общие свойства всех животных в игре.
# Наследуется от Actor.
# Параметризуется через species (вид) и behavior_type (тип поведения).
# =============================================================================

import random
from entities.actor import Actor
from world.pathfinding import find_path

class Animal(Actor):
    """
    Базовый класс для всех животных в игре.
    Использует параметризацию через species и behavior_type,
    чтобы не создавать отдельные классы для каждого вида.
    
    Примеры:
        - Кошка: species="cat", behavior_type="emergent_needs"
        - Крыса: species="rat", behavior_type="flee"
        - Собака: species="dog", behavior_type="patrol_aggressive" (добавим позже)
        - Волк: species="wolf", behavior_type="pack_hunt" (добавим позже)
    """
    
    def __init__(self, animal_id, name, x, y, species="unknown", behavior_type="emergent_needs"):
        """
        Инициализация Animal.
        
        Аргументы:
            animal_id (str): Уникальный идентификатор.
            name (str): Отображаемое имя.
            x (int): Начальная координата X.
            y (int): Начальная координата Y.
            species (str): Вид животного ("cat", "dog", "wolf", "rat" и т.д.).
            behavior_type (str): Тип поведения.
                - "emergent_needs": Эмерджентное поведение на основе потребностей (как кошка)
                - "flee": Убегает от игрока (как крыса)
                - "patrol_aggressive": Патрулирует и атакует (добавим позже для собак)
                - "pack_hunt": Стайная охота (добавим позже для волков)
                - "wander": Случайное блуждание (добавим позже)
                - "stationary": Стоит на месте (добавим позже)
        """
        # Вызываем конструктор базового класса Actor
        super().__init__(animal_id, name, x, y)
        
        # -------------------------------------------------------------------------
        # ВИД И ПОВЕДЕНИЕ
        # -------------------------------------------------------------------------
        # Вид животного (используется для отрисовки, звуков, специфичной логики)
        self.species = species
        
        # Тип поведения (определяет, как животное принимает решения)
        self.behavior_type = behavior_type
        
        # -------------------------------------------------------------------------
        # ПОТРЕБНОСТИ (0–100)
        # Общие для всех животных, но интерпретируются по-разному в зависимости от behavior_type
        # -------------------------------------------------------------------------
        # Голод (падает со временем, растёт при активности)
        self.hunger = 50
        
        # Энергия (падает со временем, восстанавливается сном/едой)
        self.energy = 80
        
        # Страх (растёт при угрозе, падает в безопасности)
        self.fear = 0
        
        # Агрессия (растёт при голоде/боли, используется для атаки)
        self.aggression = 0
        
        # Скука (растёт со временем, падает при игре)
        self.boredom = 30
        
        # Стремление выйти (растёт со временем, падает у двери)
        self.wanderlust = 0
        
        # -------------------------------------------------------------------------
        # ТОЧКИ ИНТЕРЕСА
        # Словарь {название: (x, y)} — места, куда животное может пойти
        # Например: {"food": (3, 3), "home": (8, 4), "toy": (6, 7)}
        # -------------------------------------------------------------------------
        self.points_of_interest = {}
        
        # -------------------------------------------------------------------------
        # ТЕКУЩЕЕ СОСТОЯНИЕ
        # -------------------------------------------------------------------------
        # Текущее действие (строка: "idle", "move", "eat", "sleep", "play", "flee", "meow" и т.д.)
        self.action = "idle"
        
        # Цель движения (кортеж (x, y) или None)
        self.target = None
        
        # Таймер действия (сколько тиков длится текущее действие)
        self.action_timer = 0
        
        # Время последнего обновления потребностей (в миллисекундах)
        self.last_need_update = 0
        
        # Задержка движения (переопределяет speed из Actor для животных)
        # По умолчанию 300 мс (быстрее, чем у NPC)
        self.move_delay_ms = 300
    
    # -------------------------------------------------------------------------
    # ПОТРЕБНОСТИ
    # -------------------------------------------------------------------------
    
    def update_needs(self, current_time):
        """
        Постепенно меняет потребности со временем (раз в секунду).
        Вызывается из Map.update_animals().
        """
        if current_time - self.last_need_update < 1000:
            return
        self.last_need_update = current_time
        
        # Голод и энергия падают
        self.hunger = max(0, self.hunger - 1)
        self.energy = max(0, self.energy - 1)
        
        # Скука растёт
        self.boredom = min(100, self.boredom + 1)
        
        # Стремление выйти растёт
        self.wanderlust = min(100, self.wanderlust + 2)
    
    # -------------------------------------------------------------------------
    # ВЫБОР ДЕЙСТВИЯ
    # -------------------------------------------------------------------------
    
    def decide_action(self, current_map):
        """
        Выбирает действие по приоритету потребностей.
        Работает только для behavior_type == "emergent_needs".
        """
        if self.behavior_type != "emergent_needs":
            return
        
        # Если уже что-то делаем — не меняем
        if self.action in ("eat", "sleep", "play", "meow") and self.action_timer > 0:
            self.action_timer -= 1
            return
        
        # Если уже есть путь — не пересчитываем
        if self.path:
            return
        
        # Приоритет 0: стремление выйти
        if self.wanderlust > 60:
            door = self._find_nearest_door(current_map)
            if door:
                path = find_path(self.x, self.y, door[0], door[1], current_map.is_walkable_for_animal)
                if path:
                    self.path = path
                    self.target = door
                    return
        
        # Приоритет 1: голод
        food_pos = self.points_of_interest.get("food")
        if self.hunger < 30 and food_pos:
            path = find_path(self.x, self.y, food_pos[0], food_pos[1], current_map.is_walkable_for_animal)
            if path is not None:
                self.path = path
                self.target = tuple(food_pos)
                return
        
        # Приоритет 2: сон
        home_pos = self.points_of_interest.get("home")
        if self.energy < 30 and home_pos:
            path = find_path(self.x, self.y, home_pos[0], home_pos[1], current_map.is_walkable_for_animal)
            if path is not None:
                self.path = path
                self.target = tuple(home_pos)
                return
        
        # Приоритет 3: скука
        toy_pos = self.points_of_interest.get("toy")
        if self.boredom > 70 and toy_pos:
            path = find_path(self.x, self.y, toy_pos[0], toy_pos[1], current_map.is_walkable_for_animal)
            if path is not None:
                self.path = path
                self.target = tuple(toy_pos)
                return
        
        # Иначе — случайное блуждание
        if self.action == "idle":
            self.action = "wander"
            self.target = (
                self.x + random.choice([-1, 0, 1]),
                self.y + random.choice([-1, 0, 1])
            )
    
    # -------------------------------------------------------------------------
    # ПОИСК БЛИЖАЙШЕЙ ДВЕРИ
    # -------------------------------------------------------------------------
    
    def _find_nearest_door(self, current_map):
        """Ищет ближайшую дверь на карте."""
        best = None
        best_dist = 9999
        for y in range(current_map.height):
            for x in range(current_map.width):
                if current_map.is_door(x, y):
                    dist = abs(x - self.x) + abs(y - self.y)
                    if dist < best_dist:
                        best_dist = dist
                        best = (x, y)
        return best
    
    # -------------------------------------------------------------------------
    # ДВИЖЕНИЕ К ЦЕЛИ
    # -------------------------------------------------------------------------
    
    def move_towards_target(self, current_map, current_time):
        """Делает шаг по пути к цели."""
        # Задержка движения
        if current_time - self.last_move_time < self.move_delay_ms:
            return
        
        # Если есть путь — идём по нему
        if self.path:
            next_x, next_y = self.path[0]
            self.x = next_x
            self.y = next_y
            self.path.pop(0)
            self.last_move_time = current_time
            
            # Если путь закончился — выполняем действие
            if not self.path:
                self._on_reached_target(current_map, current_time)
            return
        
        # Если пути нет — сбрасываем
        self.action = "idle"
        self.target = None
    
    def _on_reached_target(self, current_map, current_time):
        """Вызывается, когда животное дошло до цели."""
        if not self.target:
            self.action = "idle"
            return
        
        tx, ty = self.target
        
        # Если это дверь — мяукаем (или другое действие)
        if current_map.is_door(tx, ty):
            self.action = "meow"
            self.action_timer = 5
            self.wanderlust = max(0, self.wanderlust - 30)
            print(f"{self.species.capitalize()} {self.id}: Мяу! (у двери {tx},{ty})")
            self.target = None
            self.last_move_time = current_time
            return
        
        # Действия по потребностям
        if self.hunger < 30:
            self.action = "eat"
            self.action_timer = 3
            self.hunger = min(100, self.hunger + 40)
            print(f"{self.species.capitalize()} {self.id} ест. Сытость: {self.hunger}")
        elif self.energy < 30:
            self.action = "sleep"
            self.action_timer = 5
            self.energy = min(100, self.energy + 60)
            print(f"{self.species.capitalize()} {self.id} спит. Энергия: {self.energy}")
        elif self.boredom > 70:
            self.action = "play"
            self.action_timer = 3
            self.boredom = max(0, self.boredom - 50)
            print(f"{self.species.capitalize()} {self.id} играет. Скука: {self.boredom}")
        else:
            self.action = "idle"
        
        self.target = None
        self.last_move_time = current_time