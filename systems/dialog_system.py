import json
import os
from settings import DIALOGS_DIR

class DialogSystem:
    def __init__(self, game_state):
        self.game_state = game_state
        self.current_dialog = None
        self.current_npc_id = None

    def load_dialog(self, dialog_id):
        filename = f"{dialog_id}_dia.json"
        path = os.path.join(DIALOGS_DIR, filename)
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

    def choose_option(self, option_index):
        if not self.current_dialog:
            return

        options = self.game_state.dialog_options
        if option_index >= len(options):
            return

        selected = options[option_index]
        next_node = selected.get("next")

        # Применяем эффекты
        if "effect" in selected:
            for key, value in selected["effect"].items():
                if key == "humanity":
                    self.game_state.humanity = max(0, min(100, self.game_state.humanity + value))
                else:
                    self.game_state.flags[key] = value

        # Если следующая нода — "close", показываем текст выбранного ответа и закрываем
        if next_node == "close":
            self.game_state.dialog_text = selected.get("response", "Диалог завершён.")
            self.game_state.dialog_options = []
            # Даём игроку увидеть текст, закрываем через кадр
            return

        # Если следующая нода существует — переходим в неё
        if next_node and next_node in self.current_dialog:
            node = self.current_dialog[next_node]
            self.game_state.dialog_text = node.get("text", "")
            self.game_state.dialog_options = node.get("options", [])
            self.game_state.dialog_current_node = next_node

            # Если после этого узла идёт close — закроем после отображения
            if node.get("next") == "close":
                # Оставляем активным, закроем в следующем обновлении отдельно
                pass

    def close_dialog(self):
        """Вызывается из main.py, когда игрок нажимает E или ESC в конце диалога"""
        self.game_state.dialog_active = False
        self.current_dialog = None
        self.current_npc_id = None