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
from logger import log

class DialogSystem:
    """
    Класс для управления диалогами.
    Отвечает за загрузку JSON, смену узлов и применение эффектов.
    """
    def __init__(self, game_state, dialogs_dir: str):
        self.game_state = game_state
        self.dialogs_dir = dialogs_dir
        self.current_dialog = None
        self.current_npc_id = None

    # -------------------------------------------------------------------------
    # ПРИМЕНЕНИЕ ЭФФЕКТОВ (ХАРАКТЕРИСТИКИ И ФЛАГИ)
    # -------------------------------------------------------------------------
    def _apply_effects(self, effects_dict):
        """
        Универсальный метод применения эффектов из JSON.
        Модифицирует человечность (с ограничением 0-100) и записывает сюжетные флаги.
        """
        if not effects_dict:
            return
            
        for key, value in effects_dict.items():
            if key == "humanity":
                # Математически прибавляем/вычитаем, жестко ограничивая рамками 0–100
                self.game_state.humanity = max(0, min(100, self.game_state.humanity + value))
                log.info(f"ДИАЛОГ: человечность изменена на {value}, теперь {self.game_state.humanity}")
            else:
                # Всё остальное (например, guard_encountered) идет в глобальные флаги
                self.game_state.flags[key] = value
                log.info(f"ДИАЛОГ: установлен флаг {key} = {value}")

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
                
                start_node = self.current_dialog["start"]
                self.game_state.dialog_text = start_node.get("text", "")
                self.game_state.dialog_options = start_node.get("options", [])
                self.game_state.dialog_current_node = "start"
                
                # ФИКС: применяем эффекты стартового узла (если вдруг они там есть)
                if "effect" in start_node:
                    self._apply_effects(start_node["effect"])
                    
                return True
        except Exception as e:
            log.error(f"Ошибка загрузки диалога {dialog_id}: {e}")
            return False

    # -------------------------------------------------------------------------
    # ОБРАБОТКА ВЫБОРА ИГРОКА
    # -------------------------------------------------------------------------
    def choose_option(self, option_index):
        """Обрабатывает выбор игрока (клик по опции или нажатие 1-4)."""
        if not self.current_dialog:
            return
            
        options = self.game_state.dialog_options
        if option_index >= len(options):
            return
            
        selected = options[option_index]
        next_node = selected.get("next")
        
        # 1. Применяем эффект самой ОПЦИИ (например, -5 к человечности за попытку блефа)
        if "effect" in selected:
            self._apply_effects(selected["effect"])

        # Обработка конца диалога
        if next_node == "close":
            self.game_state.dialog_text = selected.get("response", "Диалог завершён.")
            self.game_state.dialog_options = []
            return

        # Переход на следующую ноду
        if next_node and next_node in self.current_dialog:
            node = self.current_dialog[next_node]
            self.game_state.dialog_text = node.get("text", "")
            self.game_state.dialog_options = node.get("options", [])
            self.game_state.dialog_current_node = next_node
            
            # 2. ФИКС: Применяем эффект самой НОДЫ (например, guard_encountered: true)
            # Раньше этот блок игнорировался, и флаги не сохранялись.
            if "effect" in node:
                self._apply_effects(node["effect"])

            # Если следующая нода не имеет опций, диалог просто покажет текст 
            # и будет ждать нажатия E/ESC (которое мы починили в InputHandler).
            if node.get("next") == "close":
                pass

    # -------------------------------------------------------------------------
    # ЗАКРЫТИЕ ДИАЛОГА
    # -------------------------------------------------------------------------
    def close_dialog(self):
        """Завершает диалог и очищает состояние."""
        self.game_state.dialog_active = False
        self.game_state.dialog_text = ""
        self.game_state.dialog_options = []
        self.game_state.dialog_current_node = "start"
        self.current_dialog = None
        self.current_npc_id = None