# game_engine.py
# =============================================================================
# ГЛАВНЫЙ ИГРОВОЙ ДВИЖОК
# Управляет циклом, событиями, обновлением и отрисовкой.
# =============================================================================

import random
import os
import pygame
import sys
from settings import *
from game_state import GameState
from world.map import Map
from systems.dialog_system import DialogSystem
from world.location_manager import LocationManager
from ui.renderer import Renderer
from input_handler import InputHandler
from logger import log
from systems.movement_system import MovementSystem
from objects.drop import ItemDrop


class GameEngine:
    """Главный игровой движок. Управляет циклом, событиями, обновлением и отрисовкой."""

    def __init__(self, location_id: str, game_state: GameState = None):
        self.temp_message = None
        self.temp_message_timer = 0

        if not pygame.get_init():
            pygame.init()

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Last Way — пре-альфа")
        self.clock = pygame.time.Clock()

        # Состояние и системы
        self.game_state = game_state if game_state else GameState()
        # FIX: актуализируем ID локации в GameState (раньше было хардкод "hospital")
        self.game_state.location = location_id

        self.location_manager = LocationManager()
        self.current_map = Map(location_id, self.game_state, self.location_manager)

        # Диалоги
        dialogs_path = os.path.join(
            self.location_manager.get_location_path(location_id),
            "dialogs"
        )
        self.dialog_system = DialogSystem(self.game_state, dialogs_path)

        # Позиция игрока — через атрибуты объекта Player
        player_x, player_y = self.current_map.player_start
        self.game_state.player.x = player_x
        self.game_state.player.y = player_y

        # FIX: убрана мёртвая проверка `if not player.player_class` —
        # Player.__init__ всегда ставит "Идальго" по умолчанию.

        # Синхронизируем лимит веса инвентаря с классом игрока
        self.game_state.inventory.max_weight = self.game_state.player.max_weight

        # Состояние движения
        self.move_queue = []
        self.player_target = None
        self.stuck_counter = 0
        self.last_move_time = 0
        # FIX: убран self.facing_direction — теперь единственный источник
        # направления — player.facing (строка, см. entities/actor.py).

        # Состояние игры
        self.running = True
        self.exit_code = None
        self.inventory_open = False

        # Ввод
        self.input_handler = InputHandler()

        # Сохранения
        from systems.save_system import SaveSystem
        self.save_system = SaveSystem(self)
        self.save_menu_open = False
        self.save_menu_mode = None          # "save" или "load"
        self.save_menu_selected = 0
        self.save_menu_items = []

        # Отложенное взаимодействие (подход к объекту по клику)
        self.pending_interaction = None     # (x, y) — куда взаимодействовать после прихода
        self.pending_target_cell = None     # (x, y) — куда идти
        self.pending_npc_id = None          # ID NPC, если догоняем движущегося

        # Системы
        self.renderer = Renderer(self)
        self.movement_system = MovementSystem(self)

    # -------------------------------------------------------------------------
    # ОСНОВНОЙ ЦИКЛ
    # -------------------------------------------------------------------------

    def run(self) -> str:
        while self.running:
            current_time = pygame.time.get_ticks()
            self.clock.tick(60)
            self.handle_events()
            self.update(current_time)
            self.render()
            pygame.display.flip()
        return self.exit_code or "exit"

    # -------------------------------------------------------------------------
    # СОБЫТИЯ
    # -------------------------------------------------------------------------
    def handle_events(self):
        """
        Обработка событий pygame.

        FIX (#3): когда открыт инвентарь или меню сохранений, ввод блокируется.
        Раньше события проваливались в input_handler и превращались в игровые
        команды (клик по окну инвентаря = клик по карте, E в меню сохранений
        открывал дверь и т.п.). Теперь при открытых панелях обрабатываются
        только строго их клавиши, всё остальное игнорируется.
        """
        for event in pygame.event.get():
            # Выход из игры — всегда, независимо от открытых панелей
            if event.type == pygame.QUIT:
                self.running = False
                self.exit_code = "exit"
                continue

            # --- МЕНЮ СОХРАНЕНИЙ ---
            # Пока меню открыто, слушаем только его клавиши.
            if self.save_menu_open:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.save_menu_open = False
                        continue
                    if event.key == pygame.K_UP:
                        self.save_menu_selected = max(0, self.save_menu_selected - 1)
                        continue
                    if event.key == pygame.K_DOWN:
                        self.save_menu_selected = min(
                            len(self.save_menu_items) - 1,
                            self.save_menu_selected + 1
                        )
                        continue
                    if event.key == pygame.K_RETURN:
                        if self.save_menu_mode == "save":
                            name = self.save_system.next_save_name()
                            if self.save_system.save(name):
                                self._show_message(f"Сохранено: {name}")
                                self.save_menu_open = False
                        elif self.save_menu_mode == "load":
                            if self.save_menu_items:
                                name = self.save_menu_items[self.save_menu_selected]
                                if self.save_system.load(name):
                                    self.current_map.reset_all_npcs_timer()
                                    self.pending_interaction = None
                                    self.pending_target_cell = None
                                    self.pending_npc_id = None
                                    self._show_message(f"Загружено: {name}")
                                self.save_menu_open = False
                        continue
                # Прочие события при открытом меню сохранений — игнорируем
                continue

            # --- ИНВЕНТАРЬ ---
            # Пока инвентарь открыт, слушаем только I и ESC.
            if self.inventory_open:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_i or event.key == pygame.K_ESCAPE:
                        self.inventory_open = False
                        continue
                # Прочие события при открытом инвентаре — игнорируем
                continue

            # --- ОБЫЧНЫЙ ВВОД (никакие панели не открыты) ---
            command = self.input_handler.handle_event(event, self.game_state, self.current_map)
            if command:
                self._process_command(command)

    def _process_command(self, command):
        log.info(f"Получена команда {command}")
        if isinstance(command, tuple):
            cmd_type = command[0]
            if cmd_type == "dialog_choice":
                self.dialog_system.choose_option(command[1])
            elif cmd_type == "interact":
                _, target_x, target_y = command
                # Сначала: если в радиусе — сразу взаимодействуем
                if self._is_in_range(target_x, target_y):
                    self.pending_npc_id = None
                    self.pending_interaction = None
                    self.pending_target_cell = None
                    self._handle_interaction(target_x, target_y)
                    return
                # Проверяем, есть ли в этой клетке NPC (движущийся или нет)
                npc = self.current_map.get_npc_at(target_x, target_y)
                if npc:
                    self.pending_npc_id = npc.id
                    self.pending_interaction = (npc.x, npc.y)
                else:
                    self.pending_npc_id = None
                    self.pending_interaction = (target_x, target_y)
                # Строим путь к текущей позиции цели
                approach = self.movement_system.find_approach_cell(
                    self.pending_interaction[0], self.pending_interaction[1]
                )
                if not approach:
                    self._show_message("Не подойти к объекту")
                    return
                from world.pathfinding import find_path
                path = find_path(
                    self.game_state.player.x,
                    self.game_state.player.y,
                    approach[0], approach[1],
                    self.current_map.is_walkable
                )
                if path:
                    self.move_queue = path
                    self.pending_target_cell = approach
                    log.info(f"АВТО-ПОДХОД: к {approach}")
                else:
                    self._show_message("Путь не найден")
            elif cmd_type == "move_to":
                _, target_x, target_y = command
                from world.pathfinding import find_path
                if not self.current_map.is_walkable(target_x, target_y):
                    return
                self.player_target = (target_x, target_y)
                path = find_path(
                    self.game_state.player.x,
                    self.game_state.player.y,
                    target_x, target_y,
                    self.current_map.is_walkable
                )
                if path:
                    self.move_queue = path
        else:
            if command == "interact":
                self._interact()
                
            # ФИКС #2: Обработка явного закрытия диалога (клавиши E, Space, Enter)
            elif command == "close_dialog":
                if self.game_state.dialog_active:
                    self.dialog_system.close_dialog()
                    
            elif command == "menu":
                # ESC тоже закрывает диалог, если он открыт, иначе выходит в меню/из игры
                if self.game_state.dialog_active:
                    self.dialog_system.close_dialog()
                else:
                    self.running = False

            elif command == "open_inventory":
                self.inventory_open = not self.inventory_open
                log.info(f"Инвентарь: {'открыт' if self.inventory_open else 'закрыт'}")
                
                # ДИАГНОСТИКА: при открытии печатаем весь инвентарь с типами объектов
                if self.inventory_open:
                    inv = self.game_state.inventory
                    log.info(f"=== ДАМП ИНВЕНТАРЯ ({len(inv.items)} предметов) ===")
                    for i, item in enumerate(inv.items):
                        log.info(
                            f"  [{i}] {item.name} (ID: {item.id}) — "
                            f"класс: {type(item).__name__}, "
                            f"категория: {item.category.value}, "
                            f"хранение: {item.storage_type.value}, "
                            f"объект: {id(item)}"
                        )
                    log.info(f"=== КОНЕЦ ДАМПА (вес: {inv.get_total_weight():.1f}/{inv.max_weight:.1f} кг) ===")


            elif command == "context_menu":
                pass
            elif command == "open_save_menu":
                self.save_menu_open = True
                self.save_menu_mode = "save"
                self.save_menu_items = self.save_system.list_saves()
                self.save_menu_selected = 0
            elif command == "open_load_menu":
                self.save_menu_open = True
                self.save_menu_mode = "load"
                self.save_menu_items = self.save_system.list_saves()
                self.save_menu_selected = 0

    def _interact(self):
        """
        Взаимодействие с клеткой перед игроком.
        FIX (#6): направление берём из player.facing (единый источник),
        а не из engine.facing_direction.
        """
        dx, dy = self.game_state.player.get_facing_delta()
        nx = self.game_state.player.x + dx
        ny = self.game_state.player.y + dy
        if not self._is_in_range(nx, ny):
            self._show_message("Слишком далеко")
            return
        self._handle_interaction(nx, ny)

    def _handle_interaction(self, x, y):
        if not self._is_in_range(x, y):
            self._show_message("Слишком далеко")
            return
        
        # 1. NPC
        npc = self.current_map.get_npc_at(x, y)
        if npc:
            self.dialog_system.load_dialog(npc.dialog_id)
            return
        
        # 2. Контейнер
        container = self.current_map.get_container_at(x, y)
        if container:
            if not container.can_interact_from(self.game_state.player.x, self.game_state.player.y):
                self._show_message("С этой стороны не подобраться")
                log.info(f"КОНТЕЙНЕР: {container.id} — неверная сторона доступа")
                return
            if container.locked:
                self._show_message("Контейнер заперт")
                log.info(f"КОНТЕЙНЕР: {container.id} заперт")
                return
            if not container.is_open:
                container.open()
                log.info(f"КОНТЕЙНЕР: {container.id} открыт")
            if not container.items:
                self._show_message(f"{container.name} пуст")
                return
            
            # ВАЖНО: работаем с объектами Item, не со строками ID
            items_taken = []
            items_left = []
            for item in container.items[:]:  # Копируем список для безопасного удаления
                if self.game_state.inventory.add_item(item):
                    container.remove_item(item)
                    items_taken.append(item.name)
                    log.info(f"ПЕРЕНОС: игрок забрал {item.name} из {container.name}")
                else:
                    items_left.append(item.name)
                    log.info(f"ПЕРЕНОС: {item.name} не влез (превышен вес)")
            
            if items_taken:
                self._show_message(f"Из {container.name} взято: {', '.join(items_taken)}")
            if items_left:
                self._show_message(f"Не влезло: {', '.join(items_left)}")
            return
        
        # 3. Дроп
        drop = self.current_map.get_drop_at(x, y)
        if drop:
            items_text = []
            items_not_taken = []
            for item in drop.items[:]:
                if self.game_state.inventory.add_item(item):
                    drop.take_item(item)
                    items_text.append(item.name)
                    log.info(f"ПОДБОР: игрок подобрал {item.name} из {drop.id}")
                else:
                    items_not_taken.append(item.name)
                    log.info(f"ПОДБОР: {item.name} не влез (превышен вес)")
            
            if items_text:
                self._show_message(f"Подобрано: {', '.join(items_text)}")
            if items_not_taken:
                self._show_message(f"Не влезло: {', '.join(items_not_taken)}")
            
            if drop.is_empty:
                if drop in self.current_map.drops:
                    self.current_map.drops.remove(drop)
                log.info(f"ДРОП: {drop.id} удален с карты")
            return
        
        # 4. Дверь
        tile_type = self.current_map.get_tile_type(x, y)
        if tile_type in (5, 6, 7, 9):
            self.current_map.open_door(x, y)
            self.current_map.reset_npcs_near_door(x, y)
        elif tile_type == 2:
            self.current_map.close_door(x, y)
            self.current_map.reset_npcs_near_door(x, y)

    def _is_in_range(self, target_x, target_y, radius=None):
        if radius is None:
            radius = INTERACT_RADIUS
        px, py = self.game_state.player.x, self.game_state.player.y
        return abs(px - target_x) + abs(py - target_y) <= radius

    # -------------------------------------------------------------------------
    # ОБНОВЛЕНИЕ
    # -------------------------------------------------------------------------
    def update(self, current_time: int):
        if self.game_state.dialog_active or self.inventory_open or self.save_menu_open:
            return

        # Движение игрока
        self.movement_system.update_player_movement(current_time)

        # Отложенное взаимодействие
        self.movement_system.update_pending_interaction()

        # Переход между локациями
        exit_point = self.current_map.get_exit_at(
            self.game_state.player.x, self.game_state.player.y
        )
        if exit_point:
            self.switch_location(exit_point["target_location"], exit_point["target_exit_id"])
            return

        # Движение NPC
        for npc in self.current_map.npcs:
            self.movement_system.update_npc_movement(npc, current_time)

        # Животные
        self.current_map.update_animals(current_time)

    # -------------------------------------------------------------------------
    # ПЕРЕХОД МЕЖДУ ЛОКАЦИЯМИ
    # -------------------------------------------------------------------------
    def switch_location(self, target_location_id, target_exit_id):
        # --- 1. СОХРАНЯЕМ СОСТОЯНИЕ ТЕКУЩЕЙ ЛОКАЦИИ ---
        current_location_id = self.current_map.location_id
        state_data = {
            "doors": dict(self.game_state.door_states),
            "npcs": [],
            "containers": [],
            "drops": [],
        }

        for npc in self.current_map.npcs:
            state_data["npcs"].append({
                "id": npc.id, "x": npc.x, "y": npc.y,
                "patrol_index": npc.patrol_index,
                "path": npc.path,
            })

        for container in self.current_map.containers:
            state_data["containers"].append({
                "id": container.id,
                "x": container.x,
                "y": container.y,
                "width": container.width,
                "height": container.height,
                "is_open": container.is_open,
                "items": container.items_to_dict_list(),  # Сериализуем предметы
                "access_side": container.access_side,
            })
            
        for drop in self.current_map.drops:
            state_data["drops"].append({
                "id": drop.id, "x": drop.x, "y": drop.y,
                "items": drop.items_to_dict_list()  # Сериализуем предметы
            })


        self.location_manager.save_location_state(current_location_id, state_data)
        log.info(f"ПЕРЕХОД: сохранено состояние {current_location_id}")

        # --- 2. ЗАГРУЖАЕМ НОВУЮ ЛОКАЦИЮ ---
        self.current_map = Map(target_location_id, self.game_state, self.location_manager)
        self.game_state.door_states = {}
        # FIX: обновляем ID локации в GameState
        self.game_state.location = target_location_id

        # Пересоздаём dialog_system под новую локацию
        dialogs_path = os.path.join(
            self.location_manager.get_location_path(target_location_id),
            "dialogs"
        )
        self.dialog_system = DialogSystem(self.game_state, dialogs_path)

        # --- 3. ПРИМЕНЯЕМ СОХРАНЁННОЕ СОСТОЯНИЕ ---
        saved_state = self.location_manager.get_location_state(target_location_id)
        if saved_state:
            log.info(f"ПЕРЕХОД: восстановлено состояние {target_location_id}")

            for coord, tile_type in saved_state["doors"].items():
                if "," in coord:
                    xs, ys = coord.split(",")
                    x, y = int(xs), int(ys)
                    if 0 <= x < self.current_map.width and 0 <= y < self.current_map.height:
                        self.current_map.tiles[y][x] = tile_type
                        self.game_state.door_states[coord] = tile_type

            for npc_save in saved_state["npcs"]:
                for npc in self.current_map.npcs:
                    if npc.id == npc_save["id"]:
                        npc.x = npc_save["x"]
                        npc.y = npc_save["y"]
                        npc.patrol_index = npc_save["patrol_index"]
                        npc.path = [tuple(p) for p in npc_save["path"]]
                        npc.wait_until = 0
                        break

            for cont_save in saved_state["containers"]:
                for container in self.current_map.containers:
                    if container.id == cont_save["id"]:
                        container.is_open = cont_save["is_open"]
                        container.load_items_from_dict_list(cont_save["items"])
                        break
            
            self.current_map.drops.clear()
            for drop_save in saved_state["drops"]:
                new_drop = ItemDrop(
                    drop_id=drop_save["id"], x=drop_save["x"], y=drop_save["y"],
                    items=[]
                )
                new_drop.load_items_from_dict_list(drop_save["items"])
                self.current_map.drops.append(new_drop)            

        # --- 4. СТАВИМ ИГРОКА НА ТОЧКУ ВЫХОДА ---
        for exit_data in self.current_map.exits:
            if exit_data.get("id") == target_exit_id:
                self.game_state.player.x = exit_data["spawn_x"]
                self.game_state.player.y = exit_data["spawn_y"]
                break

        self.last_move_time = pygame.time.get_ticks()
        self.move_queue = []

        # Сброс отложенного взаимодействия
        self.pending_interaction = None
        self.pending_target_cell = None
        self.pending_npc_id = None

    # -------------------------------------------------------------------------
    # ОТРИСОВКА
    # -------------------------------------------------------------------------
    def render(self):
        """
        Отрисовка кадра.
        После рефакторинга вся логика (и карта, и UI) теперь в Renderer.
        """
        self.screen.fill(BLACK)
        # Вся отрисовка делегируется Renderer'у — он сам знает порядок слоёв
        self.renderer.render(self.screen)


    def _show_message(self, text):
        self.temp_message = text
        self.temp_message_timer = pygame.time.get_ticks()