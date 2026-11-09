# entities/cat.py
import random
from world.pathfinding import find_path


class Cat:
    """Эмерджентная кошка: ходит сама, исходя из потребностей."""

    def __init__(self, cat_id, x, y, food_pos=None, bed_pos=None, toy_pos=None):
        self.id = cat_id
        self.x = x
        self.y = y
        self.name = "Кошка"

        # Потребности (0–100)
        self.hunger = 50        # сытость (падает)
        self.energy = 80        # энергия (падает)
        self.boredom = 30       # скука (растёт)
        self.wanderlust = 0     # стремление выйти (растёт)

        # Точки интереса
        self.food_pos = food_pos
        self.bed_pos = bed_pos
        self.toy_pos = toy_pos

        # Текущее действие
        self.action = "idle"        # idle / move / eat / sleep / play / meow
        self.target = None          # (x, y) куда идти
        self.action_timer = 0       # сколько тиков длится действие
        self.last_need_update = 0   # время последнего обновления потребностей

        # Задержка движения
        self.last_move_time = 0
        self.move_delay_ms = 300

        self.path = []  # очередь клеток для прохождения

    # -------------------------------------------------------------------------
    # ПОТРЕБНОСТИ
    # -------------------------------------------------------------------------
    def update_needs(self, current_time):
        """Постепенно меняет потребности со временем (раз в секунду)."""
        if current_time - self.last_need_update < 1000:
            return
        self.last_need_update = current_time

        self.hunger = max(0, self.hunger - 1)
        self.energy = max(0, self.energy - 1)
        self.boredom = min(100, self.boredom + 1)
        self.wanderlust = min(100, self.wanderlust + 2)

    # -------------------------------------------------------------------------
    # ВЫБОР ДЕЙСТВИЯ
    # -------------------------------------------------------------------------

    def decide_action(self, current_map):
        """Выбирает действие по приоритету потребностей."""
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
                path = find_path(self.x, self.y, door[0], door[1], current_map.is_walkable_for_cat)
                if path:
                    self.path = path
                    self.target = door
                    return

        # Приоритет 1: голод
        if self.hunger < 30 and self.food_pos:
            path = find_path(self.x, self.y, self.food_pos[0], self.food_pos[1], current_map.is_walkable_for_cat)
            if path is not None:
                self.path = path
                self.target = tuple(self.food_pos)
                return

        # Приоритет 2: сон
        if self.energy < 30 and self.bed_pos:
            path = find_path(self.x, self.y, self.bed_pos[0], self.bed_pos[1], current_map.is_walkable_for_cat)
            if path is not None:
                self.path = path
                self.target = tuple(self.bed_pos)
                return

        # Приоритет 3: скука
        if self.boredom > 70 and self.toy_pos:
            path = find_path(self.x, self.y, self.toy_pos[0], self.toy_pos[1], current_map.is_walkable_for_cat)
            if path is not None:
                self.path = path
                self.target = tuple(self.toy_pos)
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
        """Вызывается, когда кошка дошла до цели."""
        if not self.target:
            self.action = "idle"
            return

        tx, ty = self.target

        # Если это дверь — мяукаем
        if current_map.is_door(tx, ty):
            self.action = "meow"
            self.action_timer = 5
            self.wanderlust = max(0, self.wanderlust - 30)
            print(f"Кошка {self.id}: Мяу! (у двери {tx},{ty})")
            self.target = None
            self.last_move_time = current_time
            return

        # Действия по потребностям
        if self.hunger < 30:
            self.action = "eat"
            self.action_timer = 3
            self.hunger = min(100, self.hunger + 40)
            print(f"Кошка {self.id} ест. Сытость: {self.hunger}")
        elif self.energy < 30:
            self.action = "sleep"
            self.action_timer = 5
            self.energy = min(100, self.energy + 60)
            print(f"Кошка {self.id} спит. Энергия: {self.energy}")
        elif self.boredom > 70:
            self.action = "play"
            self.action_timer = 3
            self.boredom = max(0, self.boredom - 50)
            print(f"Кошка {self.id} играет. Скука: {self.boredom}")
        else:
            self.action = "idle"
        self.target = None
        self.last_move_time = current_time