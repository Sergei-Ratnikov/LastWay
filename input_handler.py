# input_handler.py
import pygame
from settings import TILE_SIZE

class InputHandler:
    """Преобразует события клавиатуры и мыши в игровые команды."""

    def handle_event(self, event, game_state, current_map):
        if event.type == pygame.KEYDOWN:
            return self._handle_key(event, game_state)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            return self._handle_mouse(event, game_state, current_map)
        return None

    def _handle_key(self, event, game_state):
        """Обработка клавиатуры."""
        
        # --- РЕЖИМ ДИАЛОГА (ИЗОЛИРОВАННЫЙ) ---
        # ФИКС #2: Если диалог активен, мы полностью перехватываем управление.
        if game_state.dialog_active:
            # Если есть варианты ответов — обрабатываем цифры 1-4
            if game_state.dialog_options:
                if event.key == pygame.K_1: return ("dialog_choice", 0)
                if event.key == pygame.K_2: return ("dialog_choice", 1)
                if event.key == pygame.K_3: return ("dialog_choice", 2)
                if event.key == pygame.K_4: return ("dialog_choice", 3)
            
            # Клавиши подтверждения/закрытия работают ВСЕГДА, 
            # даже если опций нет (узел с next: "close").
            if event.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                return "close_dialog"
                
            # Любые другие клавиши (WASD, I, F5) в режиме диалога блокируются,
            # чтобы игрок не мог уйти или открыть инвентарь, пока читает текст.
            return None

        # --- ОБЫЧНЫЙ РЕЖИМ (диалог закрыт) ---
        if event.key == pygame.K_e:
            return "interact"
        elif event.key == pygame.K_i:
            return "open_inventory"
        elif event.key == pygame.K_ESCAPE:
            return "menu"
        elif event.key == pygame.K_F5:
            return "open_save_menu"
        elif event.key == pygame.K_F9:
            return "open_load_menu"
            
        return None

    def _handle_mouse(self, event, game_state, current_map):
        """Обработка мыши."""
        # Во время диалога клики мышью по карте игнорируются
        if game_state.dialog_active:
            return None

        if event.button == 1:  # ЛКМ
            mouse_x, mouse_y = pygame.mouse.get_pos()
            target_x = mouse_x // TILE_SIZE
            target_y = mouse_y // TILE_SIZE
            if (current_map.get_npc_at(target_x, target_y) is not None or
                current_map.get_container_at(target_x, target_y) is not None or
                current_map.get_drop_at(target_x, target_y) is not None or
                current_map.is_door(target_x, target_y)):
                return ("interact", target_x, target_y)
            return ("move_to", target_x, target_y)
        elif event.button == 3:  # ПКМ
            return "context_menu"
        return None