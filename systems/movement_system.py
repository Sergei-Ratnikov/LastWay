# systems/movement_system.py

'''
СИСТЕМА ДВИЖЕНИЯ
Отвечает за:
- движение игрока (по клавишам и по move_queue)
- движение NPC (патрулирование, следование)
- обновление отложенного взаимодействия (pending_interaction)
- шаг сущности (обход препятствий, расхождение NPC)
- поиск подходной клетки для взаимодействия
'''

import pygame
from settings import MOVE_DELAY_MS
from logger import log


class MovementSystem:
    """
    Система движения.
    Получает ссылку на GameEngine, чтобы иметь доступ ко всем нужным данным.
    """

    def __init__(self, game_engine):
        self.engine = game_engine

    def _get_patrol_target(self, npc) -> tuple[int, int]:
        """
        Возвращает (x, y) текущей точки патруля.
        Поддерживает оба формата из actors.json:
            [x, y]            — старый
            {"pos": [x, y]}   — новый (как в renderer._render_npcs)
        """
        target = npc.patrol_points[npc.patrol_index]
        if isinstance(target, dict):
            pos = target.get("pos", [npc.x, npc.y])
            return pos[0], pos[1]
        return target[0], target[1]

    # -------------------------------------------------------------------------
    # ОБНОВЛЕНИЕ ДВИЖЕНИЯ ИГРОКА
    # -------------------------------------------------------------------------

    def update_player_movement(self, current_time):
        """
        Обновляет движение игрока.
        FIX (#6): направление взгляда хранится в player.facing (Actor),
        а не в engine.facing_direction.
        """
        engine = self.engine

        # Если есть очередь движения — идём по ней
        if engine.move_queue:
            self.step(engine.game_state.player, is_player=True)
        else:
            # Иначе — проверяем клавиши
            keys = pygame.key.get_pressed()
            dx = dy = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1

            if dx != 0 or dy != 0:
                # FIX: обновляем направление через player.set_facing_from_delta.
                # Для диагоналей метод сохраняет последнее ортогональное направление.
                engine.game_state.player.set_facing_from_delta(dx, dy)
                # Сбрасываем отложенное взаимодействие (игрок сам управляет движением)
                engine.pending_interaction = None
                engine.pending_target_cell = None
                engine.pending_npc_id = None

            if (dx != 0 or dy != 0) and current_time - engine.last_move_time >= MOVE_DELAY_MS:
                nx = engine.game_state.player.x + dx
                ny = engine.game_state.player.y + dy
                if engine.current_map.is_walkable(nx, ny):
                    engine.game_state.player.x = nx
                    engine.game_state.player.y = ny
                    engine.last_move_time = current_time

    # -------------------------------------------------------------------------
    # ОБНОВЛЕНИЕ ДВИЖЕНИЯ NPC
    # -------------------------------------------------------------------------

    def update_npc_movement(self, npc, current_time):
        """Обновляет движение одного NPC."""
        engine = self.engine

        if npc.movement == "stationary":
            return
        if npc.wait_until > current_time:
            return

        # --- СЛЕДОВАНИЕ ЗА ДРУГИМ NPC ---
        if npc.movement == "follow" and npc.follow_target:
            target_npc = None
            for other in engine.current_map.npcs:
                if other.id == npc.follow_target:
                    target_npc = other
                    break

            if target_npc:
                if abs(npc.x - target_npc.x) + abs(npc.y - target_npc.y) <= 1:
                    npc.path = []
                    npc.last_move_time = current_time
                    return

                if not npc.path:
                    from world.pathfinding import find_path
                    path = find_path(
                        npc.x, npc.y,
                        target_npc.x, target_npc.y,
                        engine.current_map.is_walkable_static
                    )
                    if path:
                        npc.path = path
                    else:
                        npc.last_move_time = current_time

                self.step(npc, is_player=False)
                return

        # --- ПАТРУЛИРОВАНИЕ ---
        if npc.patrol_points:
            tx, ty = self._get_patrol_target(npc)
            if (npc.x, npc.y) == (tx, ty):
                npc.patrol_index = (npc.patrol_index + 1) % len(npc.patrol_points)
                npc.last_move_time = current_time
                return
            
        if not npc.path and npc.patrol_points:
            if npc.wait_until > current_time:
                return

            tx, ty = self._get_patrol_target(npc)

            from world.pathfinding import find_path
            path = find_path(npc.x, npc.y, tx, ty, engine.current_map.is_walkable_static)
            if path:
                npc.path = path

        self.step(npc, is_player=False)

    # -------------------------------------------------------------------------
    # ОБНОВЛЕНИЕ ОТЛОЖЕННОГО ВЗАИМОДЕЙСТВИЯ
    # -------------------------------------------------------------------------

    def update_pending_interaction(self):
        """Обновляет отложенное взаимодействие (подход к объекту по клику)."""
        engine = self.engine
        if not engine.pending_interaction:
            return

        px, py = engine.game_state.player.x, engine.game_state.player.y

        if engine.pending_npc_id:
            npc = None
            for other in engine.current_map.npcs:
                if other.id == engine.pending_npc_id:
                    npc = other
                    break

            if npc:
                engine.pending_interaction = (npc.x, npc.y)
            else:
                engine.pending_interaction = None
                engine.pending_target_cell = None
                engine.pending_npc_id = None
                return

        tx, ty = engine.pending_interaction

        if engine._is_in_range(tx, ty):
            engine._handle_interaction(tx, ty)
            log.info(f"АВТО-ВЗАИМОДЕЙСТВИЕ: с ({tx},{ty})")
            engine.pending_interaction = None
            engine.pending_target_cell = None
            engine.pending_npc_id = None
        elif not engine.move_queue:
            approach = self.find_approach_cell(tx, ty)
            if approach:
                from world.pathfinding import find_path
                new_path = find_path(
                    px, py,
                    approach[0], approach[1],
                    engine.current_map.is_walkable
                )
                if new_path:
                    engine.move_queue = new_path
                    engine.pending_target_cell = approach
                    log.info(f"ПЕРЕСЧЁТ: новый подход к {approach}")
                else:
                    engine.pending_interaction = None
                    engine.pending_target_cell = None
                    engine.pending_npc_id = None
            else:
                engine.pending_interaction = None
                engine.pending_target_cell = None
                engine.pending_npc_id = None

    # -------------------------------------------------------------------------
    # ШАГ СУЩНОСТИ (игрок или NPC)
    # -------------------------------------------------------------------------

    def step(self, entity, is_player=False):
        """Делает один шаг сущности (игрок или NPC)."""
        engine = self.engine
        current_time = pygame.time.get_ticks()

        delay = MOVE_DELAY_MS if is_player else entity.move_delay_ms
        last_move = engine.last_move_time if is_player else entity.last_move_time

        if current_time - last_move < delay:
            return
        if not is_player and entity.wait_until > current_time:
            return

        path = engine.move_queue if is_player else entity.path
        if not path:
            return

        next_x, next_y = path[0]
        curr_x = engine.game_state.player.x if is_player else entity.x
        curr_y = engine.game_state.player.y if is_player else entity.y

        # --- ДВЕРИ ---
        tile_ahead = engine.current_map.get_tile_type(next_x, next_y)
        if tile_ahead in (5, 6, 7, 9):
            if engine.current_map.open_door(next_x, next_y):
                engine.current_map.reset_npcs_near_door(next_x, next_y)
                if not is_player:
                    entity.last_door_pos = (next_x, next_y)
                if is_player:
                    engine.last_move_time = current_time
                else:
                    entity.last_move_time = current_time
                return

        # --- ПРОВЕРКА ПРОХОДИМОСТИ ---
        def check_walkable(tx, ty):
            if is_player:
                return engine.current_map.is_walkable(tx, ty)
            return engine.current_map.is_walkable_for_npc(tx, ty, entity)

        # --- ПРЕВЕНТИВНОЕ РАСХОЖДЕНИЕ ---
        if not is_player:
            other_npc = engine.current_map.get_npc_at(next_x, next_y)
            if other_npc and other_npc.id < entity.id:
                if other_npc.path and other_npc.path[0] == (curr_x, curr_y):
                    log.info(f"ПРЕВЕНТИВ: {entity.name} уступает {other_npc.name}")
                    entity.wait_until = current_time + 400
                    return

        blocked = not check_walkable(next_x, next_y)

        # --- ВСТРЕЧНОЕ ДВИЖЕНИЕ ---
        if not is_player and blocked:
            other_npc = engine.current_map.get_npc_at(next_x, next_y)
            if other_npc and other_npc.path and other_npc.path[0] == (curr_x, curr_y):
                if entity.id > other_npc.id:
                    log.info(f"ВСТРЕЧА: {entity.name} уступает {other_npc.name}")
                    entity.wait_until = current_time + 500
                    return

        # --- ОБХОД ПРЕПЯТСТВИЙ ---
        if blocked:
            log.info(f"БЛОК: {entity.name if not is_player else 'Игрок'} на ({curr_x},{curr_y})")

            if is_player:
                engine.stuck_counter += 1
            else:
                entity.stuck_counter += 1

            current_stuck = engine.stuck_counter if is_player else entity.stuck_counter

            if current_stuck > 2:
                log.info(f"ТУПИК: {entity.name if not is_player else 'Игрок'}")
                if is_player:
                    engine.move_queue = []
                    engine.player_target = None
                    engine.stuck_counter = 0
                else:
                    entity.path = []
                    entity.wait_until = current_time + 500
                    entity.stuck_counter = 0
                return

            dx = next_x - curr_x
            dy = next_y - curr_y

            right_x, right_y = curr_x - dy, curr_y + dx
            left_x, left_y = curr_x + dy, curr_y - dx
            back_x, back_y = curr_x - dx, curr_y - dy

            if check_walkable(right_x, right_y):
                next_x, next_y = right_x, right_y
                log.info(f"ОБХОД: {entity.name if not is_player else 'Игрок'} ВПРАВО")
            elif check_walkable(left_x, left_y):
                next_x, next_y = left_x, left_y
                log.info(f"ОБХОД: {entity.name if not is_player else 'Игрок'} ВЛЕВО")
            elif check_walkable(back_x, back_y):
                next_x, next_y = back_x, back_y
                log.info(f"ОБХОД: {entity.name if not is_player else 'Игрок'} НАЗАД")
            else:
                log.info(f"ТУПИК: {entity.name if not is_player else 'Игрок'} не может обойти")
                if is_player:
                    engine.move_queue = []
                    engine.player_target = None
                    engine.stuck_counter = 0
                else:
                    entity.path = []
                    entity.wait_until = current_time + 500
                    entity.stuck_counter = 0
                return

            if is_player:
                engine.move_queue = []
                if engine.player_target:
                    from world.pathfinding import find_path
                    new_path = find_path(
                        next_x, next_y,
                        engine.player_target[0], engine.player_target[1],
                        engine.current_map.is_walkable
                    )
                    if new_path:
                        engine.move_queue = new_path
                    else:
                        engine.player_target = None
                        engine.stuck_counter = 0
            else:
                entity.path = []
                entity.last_move_time = current_time

        # --- ДВИЖЕНИЕ ---
        if check_walkable(next_x, next_y):
            # FIX: обновляем направление взгляда сущности (player или NPC)
            # через единый интерфейс Actor.set_facing_from_delta.
            entity.set_facing_from_delta(next_x - curr_x, next_y - curr_y)

            if is_player:
                engine.game_state.player.x = next_x
                engine.game_state.player.y = next_y
                if engine.move_queue:
                    engine.move_queue.pop(0)
                engine.last_move_time = current_time
                engine.stuck_counter = 0
            else:
                log.info(f"ШАГ: NPC {entity.name} ({entity.x},{entity.y}) -> ({next_x},{next_y})")
                entity.x = next_x
                entity.y = next_y
                if path and (next_x, next_y) == path[0]:
                    path.pop(0)
                    entity.stuck_counter = 0
                entity.last_move_time = current_time
                if entity.last_door_pos:
                    ldx, ldy = entity.last_door_pos
                    if abs(entity.x - ldx) + abs(entity.y - ldy) >= 1:
                        engine.current_map.close_door(ldx, ldy)
                        engine.current_map.reset_npcs_near_door(ldx, ldy)
                        entity.last_door_pos = None

    # -------------------------------------------------------------------------
    # ПОИСК ПОДХОДНОЙ КЛЕТКИ
    # -------------------------------------------------------------------------

    def find_approach_cell(self, obj_x, obj_y):
        """Находит клетку для подхода к объекту с учётом access_side контейнеров."""
        engine = self.engine

        container = engine.current_map.get_container_at(obj_x, obj_y)
        if container and container.access_side != "all":
            side = container.access_side
            candidates = []
            if side == "north":
                for dx in range(container.width):
                    candidates.append((container.x + dx, container.y - 1))
            elif side == "south":
                for dx in range(container.width):
                    candidates.append((container.x + dx, container.y + container.height))
            elif side == "west":
                for dy in range(container.height):
                    candidates.append((container.x - 1, container.y + dy))
            elif side == "east":
                for dy in range(container.height):
                    candidates.append((container.x + container.width, container.y + dy))

            for cx, cy in candidates:
                if engine.current_map.is_walkable(cx, cy):
                    return (cx, cy)
            return None

        px, py = engine.game_state.player.x, engine.game_state.player.y
        best = None
        best_dist = 9999

        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            cx, cy = obj_x + dx, obj_y + dy
            if engine.current_map.is_walkable(cx, cy):
                dist = abs(px - cx) + abs(py - cy)
                if dist < best_dist:
                    best_dist = dist
                    best = (cx, cy)
        return best