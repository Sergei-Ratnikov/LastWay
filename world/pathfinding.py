# world/pathfinding.py
from collections import deque


def find_path(start_x, start_y, target_x, target_y, walkable_func):
    """
    BFS-поиск пути от старта до цели с поддержкой диагоналей.
    
    Аргументы:
        start_x, start_y — начальная клетка
        target_x, target_y — целевая клетка
        walkable_func(x, y) — функция проверки проходимости (возвращает bool)
    
    Возвращает:
        Список клеток [(x1,y1), (x2,y2), ...] от старта до цели,
        или None, если путь не найден.
    """
    if (start_x, start_y) == (target_x, target_y):
        return []

    queue = deque()
    queue.append((start_x, start_y))
    visited = {(start_x, start_y): None}
    
    # 8 направлений: 4 ортогональных + 4 диагональных
    directions = [
        (1, 0), (-1, 0), (0, 1), (0, -1),
        (1, 1), (1, -1), (-1, 1), (-1, -1)
    ]

    while queue:
        x, y = queue.popleft()

        if (x, y) == (target_x, target_y):
            # Восстанавливаем путь
            path = []
            while (x, y) != (start_x, start_y):
                path.append((x, y))
                x, y = visited[(x, y)]
            path.reverse()
            return path

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if (nx, ny) in visited:
                continue
            if not walkable_func(nx, ny):
                continue
            
            # Проверка "срезания углов" (только для диагоналей)
            if dx != 0 and dy != 0:
                # Нельзя идти по диагонали, если обе смежные клетки непроходимы
                if not walkable_func(x + dx, y) or not walkable_func(x, y + dy):
                    continue
            
            visited[(nx, ny)] = (x, y)
            queue.append((nx, ny))

    return None