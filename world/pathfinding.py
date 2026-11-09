# world/pathfinding.py
from collections import deque


def find_path(start_x, start_y, target_x, target_y, walkable_func):
    """
    BFS-поиск пути от старта до цели.
    
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
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

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
            if (nx, ny) not in visited and walkable_func(nx, ny):
                visited[(nx, ny)] = (x, y)
                queue.append((nx, ny))

    return None