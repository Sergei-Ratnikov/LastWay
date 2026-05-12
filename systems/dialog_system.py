# systems/dialog_system.py
# =============================================================================
# СИСТЕМА ДИАЛОГОВ
# Отвечает за загрузку диалогов из JSON-файлов, управление ветвлением,
# применение эффектов (изменение человечности, установка флагов) и закрытие диалога.
# =============================================================================

import json
import os
from settings import DIALOGS_DIR


class DialogSystem:
    """
    Класс для управления диалогами.
    Загружает диалог по ID, обрабатывает выбор игрока, применяет эффекты,
    переключает узлы диалога и закрывает его.
    """

    def __init__(self, game_state):
        """
        Инициализация системы диалогов.

        Аргументы:
            game_state (GameState): Ссылка на глобальное состояние игры.
        """
        self.game_state = game_state
        self.current_dialog = None      # Текущий загруженный JSON-диалог
        self.current_npc_id = None      # ID NPC, с которым идёт диалог

    # -------------------------------------------------------------------------
    # ЗАГРУЗКА ДИАЛОГА
    # -------------------------------------------------------------------------
    def load_dialog(self, dialog_id):
        """
        Загружает диалог из JSON-файла по его ID.

        Аргументы:
            dialog_id (str): ID диалога (например, "001_001").

        Возвращает:
            bool: True, если загрузка успешна, иначе False.

        Примечание:
            Имя файла формируется как {dialog_id}_dia.json.
            Файл должен лежать в папке DIALOGS_DIR (см. settings.py).
        """
        filename = f"{dialog_id}_dia.json"
        path = os.path.join(DIALOGS_DIR, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.current_dialog = json.load(f)
                self.current_npc_id = dialog_id

                # Активируем режим диалога в глобальном состоянии
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
        """
        Обрабатывает выбор игрока (нажатие цифры 1-4).

        Аргументы:
            option_index (int): Индекс выбранного варианта (0, 1, 2, 3).
        """
        if not self.current_dialog:
            return

        options = self.game_state.dialog_options
        if option_index >= len(options):
            return

        selected = options[option_index]
        next_node = selected.get("next")

        # ---------------------------------------------------------------------
        # ПРИМЕНЕНИЕ ЭФФЕКТОВ
        # Эффекты могут быть двух типов:
        #   - "humanity": изменение человечности (может быть отрицательным)
        #   - любые другие ключи: устанавливают флаги в game_state.flags
        # ---------------------------------------------------------------------
        if "effect" in selected:
            for key, value in selected["effect"].items():
                if key == "humanity":
                    # Человечность ограничена диапазоном 0–100
                    self.game_state.humanity = max(0, min(100, self.game_state.humanity + value))
                else:
                    self.game_state.flags[key] = value

        # ---------------------------------------------------------------------
        # ОБРАБОТКА НОДЫ "close"
        # Если следующая нода — "close", диалог завершается после показа текста.
        # ---------------------------------------------------------------------
        if next_node == "close":
            # Показываем текст выбранного ответа (если есть поле response)
            self.game_state.dialog_text = selected.get("response", "Диалог завершён.")
            self.game_state.dialog_options = []
            # Диалог остаётся активным, игрок закроет его по E или ESC
            return

        # ---------------------------------------------------------------------
        # ПЕРЕХОД К СЛЕДУЮЩЕЙ НОДЕ
        # ---------------------------------------------------------------------
        if next_node and next_node in self.current_dialog:
            node = self.current_dialog[next_node]
            self.game_state.dialog_text = node.get("text", "")
            self.game_state.dialog_options = node.get("options", [])
            self.game_state.dialog_current_node = next_node

            # Если в этой ноде указано next = "close" — диалог завершится после её отображения
            if node.get("next") == "close":
                # Диалог не закрываем автоматически — ждём нажатия E/ESC
                pass

    # -------------------------------------------------------------------------
    # ЗАКРЫТИЕ ДИАЛОГА
    # -------------------------------------------------------------------------
    def close_dialog(self):
        """
        Завершает диалог. Вызывается из main.py при нажатии E или ESC,
        когда варианты ответов закончились.
        """
        self.game_state.dialog_active = False
        self.current_dialog = None
        self.current_npc_id = None