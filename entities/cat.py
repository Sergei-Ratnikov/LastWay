# entities/cat.py
import random


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

        print(f"DEBUG кошка: голод={self.hunger} энергия={self.energy} скука={self.boredom} действие={self.action} цель={self.target}")

        # Если уже что-то делаем — не меняем
        if self.action in ("eat", "sleep", "play", "meow") and self.action_timer > 0:
            self.action_timer -= 1
            return

        # Приоритет 0: стремление выйти
        if self.wanderlust > 60:
            door = self._find_nearest_door(current_map)
            if door:
                self.action = "move"
                self.target = door
                return

        # Приоритет 1: голод
        if self.hunger < 30 and self.food_pos:
            self.action = "move"
            self.target = tuple(self.food_pos)
            return

        # Приоритет 2: сон
        if self.energy < 30 and self.bed_pos:
            self.action = "move"
            self.target = tuple(self.bed_pos)
            return

        # Приоритет 3: скука
        if self.boredom > 70 and self.toy_pos:
            self.action = "move"
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
        """Делает шаг к цели, если возможно."""

        
        if not self.target:
            return

        # Задержка движфения
        if current_time - self.last_move_time < self.move_delay_ms:
            return

        tx, ty = self.target

        # Если достигли цели
        if (self.x, self.y) == (tx, ty):
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
            elif self.energy < 30:
                self.action = "sleep"
                self.action_timer = 5
                self.energy = min(100, self.energy + 60)
            elif self.boredom > 70:
                self.action = "play"
                self.action_timer = 3
                self.boredom = max(0, self.boredom - 50)
            else:
                self.action = "idle"
            self.target = None
            self.last_move_time = current_time
            return

        # Двигаемся по одной оси
        dx = 0
        dy = 0
        if self.x < tx:
            dx = 1
        elif self.x > tx:
            dx = -1
        elif self.y < ty:
            dy = 1
        elif self.y > ty:
            dy = -1

        new_x = self.x + dx
        new_y = self.y + dy

        print(f"DEBUG move: кошка ({self.x},{self.y}) цель ({tx},{ty}) шаг в ({new_x},{new_y}) проходимо={current_map.is_walkable_for_cat(new_x, new_y)}")

        if current_map.is_walkable_for_cat(new_x, new_y):
            self.x = new_x
            self.y = new_y
            self.last_move_time = current_time
        else:
            # Заблокировано — сбрасываем цель
            self.target = None
            self.action = "idle"