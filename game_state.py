# локация (текущая карта)
# позиция игрока (x, y)
# инвентарь (список предметов)
# схроны по локациям (словарь: локация → список предметов)
# флаги (какие двери открыты, с кем говорил, квесты)
# человечность (0–100)
# оставшееся время на квест (дни, часы)
# текущий бой (активен/нет)
# game_state.py
class GameState:
    def __init__(self):
        self.location = "hospital"
        self.player = {
            "x": 0,
            "y": 0,
            "class": "",
            "inventory": [],
            "found_notes": 0
        }
        self.flags = {}
        self.dialog_active = False
        self.dialog_text = ""
        self.dialog_options = []
        self.dialog_current_node = "start"
        self.game_over = False
        self.humanity = 50
        self.time_of_day = "night"
        self.days_left = 14
        self.door_states = {}

    def set_door_state(self, x, y, tile_type):
        self.door_states[f"{x},{y}"] = tile_type

    def get_door_state(self, x, y):
        return self.door_states.get(f"{x},{y}", None)