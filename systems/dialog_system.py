# systems/dialog_system.py
# =============================================================================
# СИСТЕМА ДИАЛОГОВ
# =============================================================================
# TODO (#1, #2 из анализа): переделать диалоговую систему — это тестовый
# вариант. Известные проблемы, которые будут исправлены позже:
#   #1. Эффекты (effect) в узлах (`bluff`, `intimidate` и т.п.) не применяются —
#       применяются только эффекты у опций. Сюжетные флаги из узлов теряются.
#   #2. Клавиша E не закрывает диалог, когда опций нет (нужно нажимать ESC).
# =============================================================================

import json
import os
# FIX: убран неиспользуемый импорт DIALOGS_DIR


class DialogSystem:
    """
    Класс для управления диалогами.
    """

    def __init__(self, game_state, dialogs_dir: str):
        self.game_state = game_state
        self.dialogs_dir = dialogs_dir
        self.current_dialog = None
        self.current_npc_id = None

    # -------------------------------------------------------------------------
    # ЗАГРУЗКА ДИАЛОГА
    # -------------------------------------------------------------------------

    def load_dialog(self, dialog_id):
        """Загружает диалог из JSON-файла по его ID."""
        filename = f"{dialog_id}.json"
        path = os.path.join(self.dialogs_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.current_dialog = json.load(f)
                self.current_npc_id = dialog_id

                self.game_state.dialog_active = True
                self.game_state.dialog_text = self.current_dialog["start"]["text"]
                self.game_state.dialog_options = self.current_dialog["start"].get("options", [])
                self.game_state.dialog_current_node = "start"
                return True
        except Exception as e:
            print(f"Ошибка загрузки диалога {dialog_id}:", e)
            return False

    # -------------------------------------------------------------------------
    # ОБРАБОТКА ВЫБОРА ИГРОКА
    # -------------------------------------------------------------------------

    def choose_option(self, option_index):
        """Обрабатывает выбор игрока."""
        if not self.current_dialog:
            return

        options = self.game_state.dialog_options
        if option_index >= len(options):
            return

        selected = options[option_index]
        next_node = selected.get("next")

        # Применение эффектов опции
        if "effect" in selected:
            for key, value in selected["effect"].items():
                if key == "humanity":
                    self.game_state.humanity = max(0, min(100, self.game_state.humanity + value))
                else:
                    self.game_state.flags[key] = value

        if next_node == "close":
            self.game_state.dialog_text = selected.get("response", "Диалог завершён.")
            self.game_state.dialog_options = []
            return

        if next_node and next_node in self.current_dialog:
            node = self.current_dialog[next_node]
            self.game_state.dialog_text = node.get("text", "")
            self.game_state.dialog_options = node.get("options", [])
            self.game_state.dialog_current_node = next_node

            if node.get("next") == "close":
                pass

    # -------------------------------------------------------------------------
    # ЗАКРЫТИЕ ДИАЛОГА
    # -------------------------------------------------------------------------

    def close_dialog(self):
        """Завершает диалог."""
        self.game_state.dialog_active = False
        # FIX: сбрасываем поля диалога, чтобы состояние было чистым
        self.game_state.dialog_text = ""
        self.game_state.dialog_options = []
        self.game_state.dialog_current_node = "start"
        self.current_dialog = None
        self.current_npc_id = None