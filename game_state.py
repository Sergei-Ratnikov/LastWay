# game_state.py
# =============================================================================
# СОСТОЯНИЕ ИГРЫ
# Единый контейнер для всех данных, которые должны сохраняться:
# - прогресс игрока (объект Player)
# - флаги квестов и сюжетные состояния
# - состояние диалога (активен, текст, варианты)
# - состояния дверей (открыты/закрыты)
# - время (оставшиеся дни, время суток)
# =============================================================================

from objects.inventory import Inventory
from entities.player import Player


class GameState:
    """
    Класс, хранящий всё состояние игры.
    Может быть сохранён в JSON и загружен обратно.
    """

    def __init__(self):
        # --- ОБЩИЕ ПАРАМЕТРЫ ---
        # FIX: раньше здесь был хардкод "hospital", который не совпадает
        # с реальным ID локации ("001_hospital"). Теперь значение
        # устанавливается движком (GameEngine.__init__, switch_location).
        self.location = ""

        # --- ДАННЫЕ ИГРОКА ---
        self.player = Player(player_class="Идальго", gender="male")

        # Инвентарь — отдельный объект (не часть Player, пока)
        self.inventory = Inventory()

        # --- СЮЖЕТНЫЕ ФЛАГИ ---
        self.flags = {}

        # --- ДИАЛОГОВАЯ СИСТЕМА ---
        self.dialog_active = False
        self.dialog_text = ""
        self.dialog_options = []
        self.dialog_current_node = "start"

        # --- СОСТОЯНИЕ ИГРЫ ---
        self.game_over = False

        # --- ХАРАКТЕРИСТИКИ ПЕРСОНАЖА ---
        self.humanity = 50

        # --- ВРЕМЯ ---
        self.time_of_day = "night"
        self.days_left = 14

        # --- СОСТОЯНИЕ ОБЪЕКТОВ ---
        self.door_states = {}

    # -------------------------------------------------------------------------
    # РАБОТА С ДВЕРЯМИ
    # -------------------------------------------------------------------------

    def set_door_state(self, x, y, tile_type):
        """Сохраняет состояние двери в клетке (x, y)."""
        self.door_states[f"{x},{y}"] = tile_type

    def get_door_state(self, x, y):
        """Возвращает сохранённое состояние двери или None."""
        return self.door_states.get(f"{x},{y}", None)