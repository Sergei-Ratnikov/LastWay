# entities/animal.py
# =============================================================================
# БАЗОВЫЙ КЛАСС ANIMAL
# # TODO (#4): поведение животных не закончено — способы перемещения
# (wander, move_towards_target, decide_action) будут доделаны позже.
# =============================================================================

import random
from entities.actor import Actor
from world.pathfinding import find_path


class Animal(Actor):
    """Базовый класс для всех животных в игре."""

    def __init__(self, animal_id, name, x, y, species="unknown", behavior_type="emergent_needs"):
        super().__init__(animal_id, name, x, y)

        self.species = species
        self.behavior_type = behavior_type

        # Потребности (0–100)
        self.hunger = 50
        self.energy = 80
        self.fear = 0
        self.aggression = 0
        self.boredom = 30
        self.wanderlust = 0

        # Точки интереса {название: (x, y)}
        self.points_of_interest = {}

        # Текущее состояние
        self.action = "idle"
        self.target = None
        self.action_timer = 0
        self.last_need_update = 0

        self.move_delay_ms = 300

    # -------------------------------------------------------------------------
    # ПОТРЕБНОСТИ
    # -------------------------------------------------------------------------

    def update_needs(self, current_time):
        """Постепенно меняет потребности со временем (раз в секунду)."""
        if current_time - self.last_need_update < 1000:
            return
        self.last_need_update = current_time

        self.hunger = max(0, self.hunger - 1)

        # TODO (баланс): энергия не должна падать во сне (action == "sleep").
        # Сейчас падает всегда, а восстановление происходит разово при достижении цели.
        self.energy = max(0, self.energy - 1)

        self.boredom = min(100, self.boredom + 1)
        self.wanderlust = min(100, self.wanderlust + 2)

    # -------------------------------------------------------------------------
    # ВЫБОР ДЕЙСТВИЯ
    # -------------------------------------------------------------------------

    def decide_action(self, current_map):
        """
        Выбирает действие по приоритету потребностей.
        # TODO (#4): логика не завершена — см. ниже ветку "wander", где
        # не строится путь (self.path остаётся пустым → животное стоит).
        """
        if self.behavior_type != "emergent_needs":
            return

        if self.action in ("eat", "sleep", "play", "meow") and self.action_timer > 0:
            self.action_timer -= 1
            return

        if self.path:
            return

        if self.wanderlust > 60:
            door = self._find_nearest_door(current_map)
            if door:
                path = find_path(self.x, self.y, door[0], door[1], current_map.is_walkable_for_animal)
                if path:
                    self.path = path
                    self.target = door
                    return

        food_pos = self.points_of_interest.get("food")
        if self.hunger < 30 and food_pos:
            path = find_path(self.x, self.y, food_pos[0], food_pos[1], current_map.is_walkable_for_animal)
            if path is not None:
                self.path = path
                self.target = tuple(food_pos)
                return

        home_pos = self.points_of_interest.get("home")
        if self.energy < 30 and home_pos:
            path = find_path(self.x, self.y, home_pos[0], home_pos[1], current_map.is_walkable_for_animal)
            if path is not None:
                self.path = path
                self.target = tuple(home_pos)
                return

        toy_pos = self.points_of_interest.get("toy")
        if self.boredom > 70 and toy_pos:
            path = find_path(self.x, self.y, toy_pos[0], toy_pos[1], current_map.is_walkable_for_animal)
            if path is not None:
                self.path = path
                self.target = tuple(toy_pos)
                return

        # TODO (#4): wander сломан — self.path не строится, животное стоит.
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
        if current_time - self.last_move_time < self.move_delay_ms:
            return

        if self.path:
            next_x, next_y = self.path[0]
            self.x = next_x
            self.y = next_y
            self.path.pop(0)
            self.last_move_time = current_time

            if not self.path:
                self._on_reached_target(current_map, current_time)
            return

        self.action = "idle"
        self.target = None

    def _on_reached_target(self, current_map, current_time):
        """Вызывается, когда животное дошло до цели."""
        if not self.target:
            self.action = "idle"
            return

        tx, ty = self.target

        if current_map.is_door(tx, ty):
            self.action = "meow"
            self.action_timer = 5
            self.wanderlust = max(0, self.wanderlust - 30)
            print(f"{self.species.capitalize()} {self.id}: Мяу! (у двери {tx},{ty})")
            self.target = None
            self.last_move_time = current_time
            return

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