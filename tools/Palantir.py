# tools/palantir.py

"""
Утилита для анализа состава и взаимосвязей проекта
"""


import os
import ast
import math
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path

# Импорты сторонних библиотек
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Pillow для рисования блок-схемы
from PIL import Image, ImageDraw, ImageFont


# ==============================================================================
# Класс для построения визуального дерева файлов
# ==============================================================================
class TreeBuilder:
    """
    Вспомогательный класс для рекурсивного обхода директории 
    и построения строкового представления дерева файлов.
    """
    def __init__(self, root_path, allowed_extensions=None):
        self.root_path = Path(root_path)
        self.tree_lines = []
        self.py_files = []
        self.json_files = []
        
        # Нормализуем расширения: приводим к нижнему регистру, добавляем точку если нужно
        self.allowed_extensions = set()
        if allowed_extensions:
            for ext in allowed_extensions:
                ext = ext.strip().lower()
                if ext and not ext.startswith('.'):
                    ext = '.' + ext
                if ext:
                    self.allowed_extensions.add(ext)

    def _is_allowed(self, file_path):
        """Проверяет, разрешено ли расширение файла."""
        if not self.allowed_extensions:
            return True  # Если фильтр пустой — показываем всё
        return file_path.suffix.lower() in self.allowed_extensions

    def build(self):
        """Запускает процесс построения дерева."""
        self.tree_lines.append(f"📁 {self.root_path.name}/")
        sub_lines = self._walk(self.root_path)
        # Добавляем префикс для содержимого корневой папки
        for line in sub_lines:
            self.tree_lines.append(f"    {line}")
        return "\n".join(self.tree_lines), self.py_files, self.json_files

    def _walk(self, current_dir):
        """
        Рекурсивная функция для обхода вложенных папок.
        Возвращает список строк БЕЗ префикса родителя.
        Если в папке нет подходящих файлов — возвращает пустой список.
        """
        lines = []
        try:
            entries = sorted(current_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return ["⚠️ [Ошибка доступа к папке]"]

        visible_entries = []
        for entry in entries:
            if entry.is_dir():
                sub_lines = self._walk(entry)
                if sub_lines:
                    visible_entries.append((entry, True, sub_lines))
            else:
                if self._is_allowed(entry):
                    visible_entries.append((entry, False, None))

        if not visible_entries:
            return []

        count = len(visible_entries)
        for index, (entry, is_dir, sub_lines) in enumerate(visible_entries):
            connector = "└── " if index == count - 1 else "├── "
            extension = "    " if index == count - 1 else "│   "

            if is_dir:
                lines.append(f"{connector}📁 {entry.name}/")
                for sub_line in sub_lines:
                    lines.append(f"{extension}{sub_line}")
            else:
                if entry.suffix.lower() == '.py':
                    icon = "🐍"
                    self.py_files.append(entry)
                elif entry.suffix.lower() == '.json':
                    icon = "📋"
                    self.json_files.append(entry)
                else:
                    icon = "📄"

                size_str = ""
                if entry.suffix.lower() == '.json':
                    size_kb = entry.stat().st_size / 1024
                    size_str = f" ({size_kb:.1f} KB)"

                lines.append(f"{connector}{icon} {entry.name}{size_str}")

        return lines


# ==============================================================================
# Класс для статического анализа Python-кода с помощью AST
# ==============================================================================
class ASTAnalyzer:
    """
    Анализатор кода. Использует ТОЛЬКО модуль ast.
    Никаких регулярных выражений!
    """
    def __init__(self, root_path, py_files, log_callback):
        self.root_path = Path(root_path)
        self.py_files = py_files
        self.log = log_callback
        self.script_numbers = {}
        self.global_index = {} 

    def assign_numbers(self):
        """Пронумеровываем все найденные .py файлы."""
        for idx, file_path in enumerate(self.py_files, start=1):
            self.script_numbers[file_path] = idx

    def _get_module_name(self, file_path):
        """Преобразует путь к файлу в имя модуля."""
        rel_path = file_path.relative_to(self.root_path)
        module_name = str(rel_path.with_suffix('')).replace(os.sep, '.')
        return module_name

    def build_global_index(self):
        """Первый проход: собираем все глобальные определения."""
        self.log("🔍 Этап 1: Построение глобального индекса сущностей...")
        for file_path, num in self.script_numbers.items():
            try:
                source = file_path.read_text(encoding='utf-8')
                tree = ast.parse(source, filename=str(file_path))
            except (SyntaxError, UnicodeDecodeError) as e:
                self.log(f"⚠️ Пропуск {file_path.name} при построении индекса: {e}")
                continue

            module_name = self._get_module_name(file_path)
            
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.global_index.setdefault(node.name, []).append(num)
                    self.global_index.setdefault(f"{module_name}.{node.name}", []).append(num)
                elif isinstance(node, ast.ClassDef):
                    self.global_index.setdefault(node.name, []).append(num)
                    self.global_index.setdefault(f"{module_name}.{node.name}", []).append(num)
                elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        if isinstance(target, ast.Name):
                            self.global_index.setdefault(target.id, []).append(num)

    def analyze_file(self, file_path):
        """Второй проход: детальный анализ конкретного файла."""
        num = self.script_numbers[file_path]
        result = {
            'number': num,
            'name': file_path.name,
            'path': str(file_path.relative_to(self.root_path)),
            'module_docstring': None,
            'functions': [],
            'classes': [],
            'global_vars': [],
            'imports': [],
            'cross_refs': []  # Теперь список кортежей: (entity, ref_num, link_type)
        }

        try:
            source = file_path.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as e:
            result['error'] = f"Синтаксическая ошибка: {e}"
            return result
        except UnicodeDecodeError as e:
            result['error'] = f"Ошибка кодировки: {e}"
            return result

        result['module_docstring'] = ast.get_docstring(tree)

        # Множество для отслеживания уже добавленных связей (чтобы не дублировать)
        added_refs = set()

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result['imports'].append(f"import {alias.name}")
                    if alias.name in self.global_index:
                        for ref_num in self.global_index[alias.name]:
                            if ref_num != num:
                                ref_key = (alias.name, ref_num, "import")
                                if ref_key not in added_refs:
                                    result['cross_refs'].append(ref_key)
                                    added_refs.add(ref_key)
                                    
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imp_str = f"from {module} import {alias.name}"
                    result['imports'].append(imp_str)
                    full_imp_name = f"{module}.{alias.name}" if module else alias.name
                    if full_imp_name in self.global_index:
                        for ref_num in self.global_index[full_imp_name]:
                            if ref_num != num:
                                ref_key = (alias.name, ref_num, "import")
                                if ref_key not in added_refs:
                                    result['cross_refs'].append(ref_key)
                                    added_refs.add(ref_key)
                    elif alias.name in self.global_index:
                        for ref_num in self.global_index[alias.name]:
                            if ref_num != num:
                                ref_key = (alias.name, ref_num, "import")
                                if ref_key not in added_refs:
                                    result['cross_refs'].append(ref_key)
                                    added_refs.add(ref_key)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_data = {
                    'name': node.name,
                    'docstring': ast.get_docstring(node),
                    'args': [arg.arg for arg in node.args.args]
                }
                result['functions'].append(func_data)

            elif isinstance(node, ast.ClassDef):
                class_data = {
                    'name': node.name,
                    'docstring': ast.get_docstring(node),
                    'methods': []
                }
                
                # Проверяем наследование
                for base in node.bases:
                    base_name = None
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr
                    
                    # ===  ЛОГ  ===
                    if base_name:
                        if base_name in self.global_index:
                            self.log(f"✅ {file_path.name}: класс '{node.name}' наследует от '{base_name}' (найден в проекте)")
                            for ref_num in self.global_index[base_name]:
                                if ref_num != num:
                                    ref_key = (base_name, ref_num, "inheritance")
                                    if ref_key not in added_refs:
                                        result['cross_refs'].append(ref_key)
                                        added_refs.add(ref_key)
                        else:
                            self.log(f"⚠️ {file_path.name}: класс '{node.name}' наследует от '{base_name}' (НЕ найден в проекте)")
                    # === КОНЕЦ ЛОГА ===

                    if base_name and base_name in self.global_index:
                        for ref_num in self.global_index[base_name]:
                            if ref_num != num:
                                ref_key = (base_name, ref_num, "inheritance")
                                if ref_key not in added_refs:
                                    result['cross_refs'].append(ref_key)
                                    added_refs.add(ref_key)
                
                for sub_node in ast.iter_child_nodes(node):
                    if isinstance(sub_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_data = {
                            'name': sub_node.name,
                            'docstring': ast.get_docstring(sub_node),
                            'args': [arg.arg for arg in sub_node.args.args]
                        }
                        class_data['methods'].append(method_data)
                result['classes'].append(class_data)

            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        result['global_vars'].append(target.id)

        # Поиск используемых сущностей (вызовы функций, обращения к переменным)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id in self.global_index:
                    for ref_num in self.global_index[node.id]:
                        if ref_num != num:
                            ref_key = (node.id, ref_num, "usage")
                            if ref_key not in added_refs:
                                result['cross_refs'].append(ref_key)
                                added_refs.add(ref_key)
            elif isinstance(node, ast.Attribute):
                if node.attr in self.global_index:
                    for ref_num in self.global_index[node.attr]:
                        if ref_num != num:
                            ref_key = (node.attr, ref_num, "usage")
                            if ref_key not in added_refs:
                                result['cross_refs'].append(ref_key)
                                added_refs.add(ref_key)

        return result


# ==============================================================================
# Класс для генерации ВЕРТИКАЛЬНОЙ блок-схемы с пучками параллельных стрелок
# ==============================================================================
class FlowchartGenerator:
    """
    Строит иерархическую вертикальную диаграмму архитектуры проекта.

    Особенности:
    - Между парой модулей рисуется НЕ БОЛЕЕ ОДНОЙ стрелки каждого типа.
    - Если между модулями есть несколько типов связей, они рисуются пучком
      параллельных линий с просветом в 1 пиксель.
    - Горизонтальные стрелки (между блоками одного слоя) проходят ПОД блоками.
    - Наследование учитывается в обе стороны при построении слоёв.
    """

    # --- Цвета блоков ---
    COLOR_MAIN = "#FFD700"
    COLOR_MODULE = "#B3D4FF"
    COLOR_ORPHAN = "#E0C8E0"
    COLOR_OUTLINE = "#333333"
    COLOR_TEXT = "#000000"
    COLOR_LABEL_BG = "#FFFFFF"

    # --- Цвета типов связей ---
    COLOR_IMPORT = "#0066CC"
    COLOR_INHERITANCE = "#00AA00"
    COLOR_USAGE = "#888888"

    LINK_ORDER = ("import", "inheritance", "usage")

    # --- Геометрия блоков ---
    BOX_W = 300
    BOX_H = 200
    H_GAP = 100
    V_GAP = 350
    MARGIN = 60
    LAYER_LABEL_W = 80
    EDGE_PADDING = 25

    # --- Геометрия стрелок ---
    LINE_WIDTH = 2
    PARALLEL_GAP = 2
    BUNDLE_STEP = LINE_WIDTH + PARALLEL_GAP
    HEAD_SIZE = 10
    HEAD_SIZE_BUNDLE = 9
    
    # --- Параметры для горизонтальных стрелок ---
    HORIZ_BASE_OFFSET = 30      # Отступ от нижнего края блоков
    HORIZ_SPREAD = 100          # Диапазон распределения горизонтальных стрелок

    @staticmethod
    def _load_font(size):
        candidates = [
            "arial.ttf", "Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except (IOError, OSError):
                continue
        return ImageFont.load_default()

    @staticmethod
    def _find_main_module(results):
        priority_names = ['main.py', '__main__.py', 'app.py', 'application.py']
        lower_map = {r['name'].lower(): r['number'] for r in results}

        for name in priority_names:
            if name in lower_map:
                return lower_map[name]

        sorted_results = sorted(results, key=lambda r: r['name'].lower())
        return sorted_results[0]['number'] if sorted_results else None

    @staticmethod
    def _build_dependency_graph(results):
        graph = {}
        for res in results:
            num = res['number']
            graph[num] = []
            for ref in res.get('cross_refs', []):
                if len(ref) == 3:
                    entity, ref_num, link_type = ref
                else:
                    entity, ref_num = ref
                    link_type = "usage"
                if ref_num != num:
                    graph[num].append((ref_num, link_type))
        return graph

    @staticmethod
    def _compute_layers(graph, main_num, all_nums):
        """
        Определяет уровень каждого модуля через BFS от main.
        Для наследования учитываются ОБА направления: если Child наследует от Parent,
        BFS идёт и от Child к Parent, и от Parent к Child.
        """
        levels = {}
        
        # Строим обратный граф для наследования
        reverse_inheritance = {}
        for from_num, connections in graph.items():
            for to_num, link_type in connections:
                if link_type == "inheritance":
                    reverse_inheritance.setdefault(to_num, []).append(from_num)

        if main_num is not None:
            queue = [(main_num, 0)]
            visited = {main_num}
            while queue:
                node, level = queue.pop(0)
                levels[node] = level
                
                # Идём по исходящим связям (все типы)
                for neighbor, _ in graph.get(node, []):
                    if neighbor not in visited and neighbor in all_nums:
                        visited.add(neighbor)
                        queue.append((neighbor, level + 1))
                
                # Идём по обратным связям наследования (от родителя к наследникам)
                for child in reverse_inheritance.get(node, []):
                    if child not in visited and child in all_nums:
                        visited.add(child)
                        queue.append((child, level + 1))

        max_level = max(levels.values()) if levels else -1
        orphans = [n for n in all_nums if n not in levels]
        if orphans:
            max_level += 1
            for num in orphans:
                levels[num] = max_level

        return levels

    @staticmethod
    def _layout_modules(levels, results_dict):
        layers = {}
        for num, level in levels.items():
            layers.setdefault(level, []).append(num)

        for level in layers:
            layers[level].sort(key=lambda n: results_dict[n]['name'].lower())

        max_in_layer = max(len(m) for m in layers.values()) if layers else 1
        content_width = max_in_layer * FlowchartGenerator.BOX_W + \
                        (max_in_layer - 1) * FlowchartGenerator.H_GAP

        img_width = FlowchartGenerator.MARGIN * 2 + FlowchartGenerator.LAYER_LABEL_W + content_width
        # Увеличиваем высоту для горизонтальных стрелок под блоками
        img_height = FlowchartGenerator.MARGIN * 2 + \
                     len(layers) * FlowchartGenerator.BOX_H + \
                     (len(layers) - 1) * FlowchartGenerator.V_GAP + \
                     FlowchartGenerator.HORIZ_BASE_OFFSET + \
                     FlowchartGenerator.HORIZ_SPREAD + \
                     50  # Запас для легенды
        if not layers:
            img_height = 400

        img_width = max(int(img_width), 800)
        img_height = max(int(img_height), 400)

        boxes = {}
        layer_y = {}

        content_start_x = FlowchartGenerator.MARGIN + FlowchartGenerator.LAYER_LABEL_W
        available_width = img_width - content_start_x - FlowchartGenerator.MARGIN

        for level in sorted(layers.keys()):
            y_top = FlowchartGenerator.MARGIN + level * (FlowchartGenerator.BOX_H + FlowchartGenerator.V_GAP)
            layer_y[level] = y_top

            modules = layers[level]
            layer_width = len(modules) * FlowchartGenerator.BOX_W + \
                          (len(modules) - 1) * FlowchartGenerator.H_GAP
            start_x = content_start_x + (available_width - layer_width) // 2

            for i, num in enumerate(modules):
                x1 = start_x + i * (FlowchartGenerator.BOX_W + FlowchartGenerator.H_GAP)
                boxes[num] = (int(x1), int(y_top),
                              int(x1 + FlowchartGenerator.BOX_W),
                              int(y_top + FlowchartGenerator.BOX_H))

        return boxes, layer_y, (img_width, img_height), layers

    @staticmethod
    def _draw_module_box(draw, xy, module_info, font, font_small, is_main=False, is_orphan=False):
        x1, y1, x2, y2 = xy

        if is_main:
            fill = FlowchartGenerator.COLOR_MAIN
        elif is_orphan:
            fill = FlowchartGenerator.COLOR_ORPHAN
        else:
            fill = FlowchartGenerator.COLOR_MODULE

        draw.rectangle(xy, fill=fill, outline=FlowchartGenerator.COLOR_OUTLINE,
                       width=3 if is_main else 2)

        title = f"№{module_info['number']}: {module_info['name']}"
        bbox = draw.textbbox((0, 0), title, font=font)
        tw = bbox[2] - bbox[0]
        tx = x1 + (x2 - x1 - tw) // 2
        ty = y1 + 12
        draw.text((tx, ty), title, font=font, fill=FlowchartGenerator.COLOR_TEXT)

        draw.line([(x1 + 10, ty + 28), (x2 - 10, ty + 28)],
                  fill=FlowchartGenerator.COLOR_OUTLINE, width=1)

        items = []
        for func in module_info.get('functions', [])[:3]:
            items.append(f"• {func['name']}()")
        for cls in module_info.get('classes', [])[:2]:
            items.append(f"• class {cls['name']}")

        total_items = len(module_info.get('functions', [])) + len(module_info.get('classes', []))
        if total_items > min(len(items), 4):
            items = items[:3] + ["• ..."]
        if not items:
            items = ["(нет функций/классов)"]

        item_y = ty + 38
        for item in items[:4]:
            draw.text((x1 + 15, item_y), item, font=font_small, fill=FlowchartGenerator.COLOR_TEXT)
            item_y += 20

    @staticmethod
    def _draw_arrowhead_down(draw, tip, color, size=10, base_width=None):
        x, y = int(tip[0]), int(tip[1])
        size = int(size)
        half = max(1, int((base_width if base_width is not None else size) // 2))
        draw.polygon([(x, y), (x - half, y - size), (x + half, y - size)], fill=color)

    @staticmethod
    def _draw_arrowhead_side(draw, tip, color, direction, size=10, base_width=None):
        x, y = int(tip[0]), int(tip[1])
        size = int(size)
        half = max(1, int((base_width if base_width is not None else size) // 2))
        if direction == 'right':
            draw.polygon([(x, y), (x - size, y - half), (x - size, y + half)], fill=color)
        else:
            draw.polygon([(x, y), (x + size, y - half), (x + size, y + half)], fill=color)

    @staticmethod
    def _get_color_for_link_type(link_type):
        if link_type == "import":
            return FlowchartGenerator.COLOR_IMPORT
        elif link_type == "inheritance":
            return FlowchartGenerator.COLOR_INHERITANCE
        return FlowchartGenerator.COLOR_USAGE

    @staticmethod
    def _draw_orthogonal_arrow(draw, from_x, from_bottom, to_x, to_top, mid_y,
                               color, head_size=10, head_base=None):
        fx, fy = int(from_x), int(from_bottom)
        tx, ty = int(to_x), int(to_top)
        my = int(mid_y)

        if fx == tx:
            draw.line([(fx, fy), (tx, ty)], fill=color, width=FlowchartGenerator.LINE_WIDTH)
        else:
            draw.line([(fx, fy), (fx, my)], fill=color, width=FlowchartGenerator.LINE_WIDTH)
            draw.line([(fx, my), (tx, my)], fill=color, width=FlowchartGenerator.LINE_WIDTH)
            draw.line([(tx, my), (tx, ty)], fill=color, width=FlowchartGenerator.LINE_WIDTH)

        FlowchartGenerator._draw_arrowhead_down(draw, (tx, ty), color,
                                                size=head_size, base_width=head_base)

    @staticmethod
    def _draw_horizontal_arrow(draw, from_box, to_box, y, color, head_size=10, head_base=None):
        """Горизонтальная стрелка на абсолютной высоте y (под блоками)."""
        y = int(y)

        if from_box[2] <= to_box[0]:
            start = (int(from_box[2]), y)
            end = (int(to_box[0]), y)
            direction = 'right'
        elif to_box[2] <= from_box[0]:
            start = (int(from_box[0]), y)
            end = (int(to_box[2]), y)
            direction = 'left'
        else:
            return

        draw.line([start, end], fill=color, width=FlowchartGenerator.LINE_WIDTH)
        FlowchartGenerator._draw_arrowhead_side(draw, end, color, direction,
                                                size=head_size, base_width=head_base)

    @staticmethod
    def _route_arrows(graph, levels, boxes, font_height):
        # Уникальные типы связей для каждой пары модулей
        pair_types = {}
        for from_num, connections in graph.items():
            for to_num, link_type in connections:
                if from_num not in levels or to_num not in levels:
                    continue
                if from_num not in boxes or to_num not in boxes:
                    continue
                if from_num == to_num:
                    continue
                pair_types.setdefault((from_num, to_num), set()).add(link_type)

        pairs = []
        for (from_num, to_num), types in pair_types.items():
            ordered = [t for t in FlowchartGenerator.LINK_ORDER if t in types]
            ordered += [t for t in sorted(types) if t not in FlowchartGenerator.LINK_ORDER]
            pairs.append({'from': from_num, 'to': to_num, 'types': ordered})

        corridors = {}
        horizontal_pairs = []

        for pair in pairs:
            fl = levels[pair['from']]
            tl = levels[pair['to']]
            if tl > fl:
                corridors.setdefault((fl, tl), []).append(pair)
            elif tl == fl:
                horizontal_pairs.append(pair)

        # Вертикальные коридоры
        min_step = 2 * font_height
        for (fl, tl), corridor_pairs in corridors.items():
            y_top = FlowchartGenerator.MARGIN + fl * (FlowchartGenerator.BOX_H + FlowchartGenerator.V_GAP) \
                    + FlowchartGenerator.BOX_H
            y_bottom = FlowchartGenerator.MARGIN + tl * (FlowchartGenerator.BOX_H + FlowchartGenerator.V_GAP)
            gap = max(y_bottom - y_top, 20)

            n = len(corridor_pairs)
            step = min_step if (n + 1) * min_step <= gap else gap / (n + 1)
            total = step * (n - 1)
            first_y = y_top + (gap - total) / 2

            corridor_pairs.sort(key=lambda p: (p['from'], p['to']))
            for i, pair in enumerate(corridor_pairs):
                pair['mid_y'] = first_y + step * i

        # Горизонтальные пары — распределяем Y ПОД блоками
        if horizontal_pairs:
            max_y_bottom = max(boxes[num][3] for num in boxes)
            base_y = max_y_bottom + FlowchartGenerator.HORIZ_BASE_OFFSET
            
            n = len(horizontal_pairs)
            step = FlowchartGenerator.HORIZ_SPREAD / max(n - 1, 1) if n > 1 else 0
            horizontal_pairs.sort(key=lambda p: (p['from'], p['to']))
            for i, pair in enumerate(horizontal_pairs):
                pair['horiz_y'] = base_y + step * i

        # Распределяем пучки по рёбрам блоков (только для вертикальных)
        outgoing = {}
        incoming = {}

        for pair in pairs:
            if 'mid_y' not in pair:
                continue
            f, t = pair['from'], pair['to']
            f_cx = (boxes[f][0] + boxes[f][2]) // 2
            t_cx = (boxes[t][0] + boxes[t][2]) // 2
            outgoing.setdefault(f, []).append((t_cx, pair))
            incoming.setdefault(t, []).append((f_cx, pair))

        def spread(items, num, field):
            items.sort(key=lambda x: x[0])
            x1, x2 = boxes[num][0], boxes[num][2]
            n = len(items)
            usable = (x2 - x1) - 2 * FlowchartGenerator.EDGE_PADDING
            for i, (_, pair) in enumerate(items):
                if n == 1:
                    pair[field] = (x1 + x2) // 2
                else:
                    pair[field] = int(x1 + FlowchartGenerator.EDGE_PADDING + usable * i / (n - 1))

        for num, items in outgoing.items():
            spread(items, num, 'base_from_x')
        for num, items in incoming.items():
            spread(items, num, 'base_to_x')

        # Разворачиваем вертикальные пары в пучки
        vertical_arrows = []
        for pair in pairs:
            if 'mid_y' not in pair:
                continue

            f_box, t_box = boxes[pair['from']], boxes[pair['to']]
            base_fx = pair.get('base_from_x', (f_box[0] + f_box[2]) // 2)
            base_tx = pair.get('base_to_x', (t_box[0] + t_box[2]) // 2)
            k = len(pair['types'])

            for i, link_type in enumerate(pair['types']):
                offset = (i - (k - 1) / 2) * FlowchartGenerator.BUNDLE_STEP
                vertical_arrows.append({
                    'from_num': pair['from'],
                    'to_num': pair['to'],
                    'link_type': link_type,
                    'from_x': int(round(base_fx + offset)),
                    'to_x': int(round(base_tx + offset)),
                    'mid_y': int(round(pair['mid_y'] + offset)),
                    'head_size': FlowchartGenerator.HEAD_SIZE_BUNDLE if k > 1 else FlowchartGenerator.HEAD_SIZE,
                    'head_base': FlowchartGenerator.BUNDLE_STEP if k > 1 else None,
                })

        # Разворачиваем горизонтальные пары в пучки
        horizontal_arrows = []
        for pair in horizontal_pairs:
            if 'horiz_y' not in pair:
                continue
            k = len(pair['types'])
            for i, link_type in enumerate(pair['types']):
                offset = (i - (k - 1) / 2) * FlowchartGenerator.BUNDLE_STEP
                horizontal_arrows.append({
                    'from_num': pair['from'],
                    'to_num': pair['to'],
                    'link_type': link_type,
                    'y': int(round(pair['horiz_y'] + offset)),
                    'head_size': FlowchartGenerator.HEAD_SIZE_BUNDLE if k > 1 else FlowchartGenerator.HEAD_SIZE,
                    'head_base': FlowchartGenerator.BUNDLE_STEP if k > 1 else None,
                })

        return vertical_arrows, horizontal_arrows

    @staticmethod
    def _draw_layer_labels(draw, layer_y, layers, font_label):
        for level in sorted(layers.keys()):
            y_center = layer_y[level] + FlowchartGenerator.BOX_H // 2
            label = "Точка входа" if level == 0 else f"Слой {level}"

            bbox = draw.textbbox((0, 0), label, font=font_label)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x, y = 15, int(y_center - th // 2)

            draw.rectangle([x - 5, y - 3, x + tw + 5, y + th + 3],
                           fill=FlowchartGenerator.COLOR_LABEL_BG,
                           outline=FlowchartGenerator.COLOR_OUTLINE, width=1)
            draw.text((x, y), label, font=font_label, fill=FlowchartGenerator.COLOR_TEXT)

    @staticmethod
    def _draw_legend(draw, y, img_width, font_small):
        legend_y = int(y + 25)

        block_items = [
            (FlowchartGenerator.COLOR_MAIN, "Точка входа"),
            (FlowchartGenerator.COLOR_MODULE, "Обычный модуль"),
            (FlowchartGenerator.COLOR_ORPHAN, "Изолированный"),
        ]
        link_items = [
            (FlowchartGenerator.COLOR_IMPORT, "Импорт"),
            (FlowchartGenerator.COLOR_INHERITANCE, "Наследование"),
            (FlowchartGenerator.COLOR_USAGE, "Использование"),
        ]

        item_w = 160
        start_x = max(20, (img_width - len(block_items) * item_w) // 2)
        for i, (color, label) in enumerate(block_items):
            x = start_x + i * item_w
            draw.rectangle([x, legend_y, x + 20, legend_y + 20],
                           fill=color, outline=FlowchartGenerator.COLOR_OUTLINE, width=1)
            draw.text((x + 28, legend_y + 2), label, font=font_small,
                      fill=FlowchartGenerator.COLOR_TEXT)

        line_y = legend_y + 35
        start_x = max(20, (img_width - len(link_items) * item_w) // 2)
        for i, (color, label) in enumerate(link_items):
            x = start_x + i * item_w
            draw.line([(x, line_y + 10), (x + 22, line_y + 10)],
                      fill=color, width=FlowchartGenerator.LINE_WIDTH)
            FlowchartGenerator._draw_arrowhead_side(draw, (x + 28, line_y + 10), color, 'right')
            draw.text((x + 34, line_y + 2), label, font=font_small,
                      fill=FlowchartGenerator.COLOR_TEXT)

    @staticmethod
    def generate(analysis_results):
        if not analysis_results:
            img = Image.new("RGB", (800, 200), "white")
            draw = ImageDraw.Draw(img)
            font = FlowchartGenerator._load_font(18)
            draw.text((50, 80), "Нет данных для построения диаграммы", font=font, fill="gray")
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            path = tmp.name
            tmp.close()
            img.save(path, "PNG")
            return path

        main_num = FlowchartGenerator._find_main_module(analysis_results)
        graph = FlowchartGenerator._build_dependency_graph(analysis_results)
        results_dict = {res['number']: res for res in analysis_results}
        levels = FlowchartGenerator._compute_layers(graph, main_num, set(results_dict))
        boxes, layer_y, img_size, layers = FlowchartGenerator._layout_modules(levels, results_dict)

        font_title = FlowchartGenerator._load_font(16)
        font_small = FlowchartGenerator._load_font(13)
        font_label = FlowchartGenerator._load_font(12)
        font_height = 13

        vertical_arrows, horizontal_arrows = FlowchartGenerator._route_arrows(
            graph, levels, boxes, font_height
        )

        max_level = max(levels.values()) if levels else 0
        orphan_nums = set()
        if max_level > 0 and main_num is not None:
            for num, lvl in levels.items():
                if lvl != max_level or num == main_num:
                    continue
                imported_from_above = any(
                    to_num == num
                    for other_num, other_lvl in levels.items() if other_lvl < max_level
                    for to_num, _ in graph.get(other_num, [])
                )
                if not imported_from_above:
                    orphan_nums.add(num)

        img = Image.new("RGB", img_size, "white")
        draw = ImageDraw.Draw(img)

        FlowchartGenerator._draw_layer_labels(draw, layer_y, layers, font_label)

        # Вертикальные стрелки
        for a in vertical_arrows:
            f_box, t_box = boxes[a['from_num']], boxes[a['to_num']]
            FlowchartGenerator._draw_orthogonal_arrow(
                draw,
                a['from_x'], f_box[3],
                a['to_x'], t_box[1],
                a['mid_y'],
                FlowchartGenerator._get_color_for_link_type(a['link_type']),
                head_size=a['head_size'], head_base=a['head_base']
            )

        # Горизонтальные стрелки (ПОД блоками)
        for a in horizontal_arrows:
            FlowchartGenerator._draw_horizontal_arrow(
                draw, boxes[a['from_num']], boxes[a['to_num']], a['y'],
                FlowchartGenerator._get_color_for_link_type(a['link_type']),
                head_size=a['head_size'], head_base=a['head_base']
            )

        for res in analysis_results:
            num = res['number']
            FlowchartGenerator._draw_module_box(
                draw, boxes[num], res, font_title, font_small,
                is_main=(num == main_num), is_orphan=(num in orphan_nums)
            )

        last_y = max(layer_y.values()) if layer_y else 0
        FlowchartGenerator._draw_legend(draw, last_y + FlowchartGenerator.BOX_H,
                                        img_size[0], font_small)

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        path = tmp.name
        tmp.close()
        img.save(path, "PNG")
        return path

# ==============================================================================
# Класс для генерации отчета в формате .docx
# ==============================================================================
class ReportGenerator:
    """Формирует красивый Word-документ на основе собранных данных."""
    
    # Шрифт для отображения эмодзи в Word
    EMOJI_FONT = 'Segoe UI Emoji'
    
    def __init__(self, output_path, tree_str, analysis_results, json_files):
        self.doc = Document()
        self.output_path = output_path
        self.tree_str = tree_str
        self.results = analysis_results
        self.json_files = json_files

    def _add_styled_paragraph(self, text, style='Normal', bold=False):
        """Вспомогательный метод для добавления стилизованного абзаца."""
        p = self.doc.add_paragraph(style=style)
        run = p.add_run(text)
        run.bold = bold
        return p

    def generate(self):
        """Основной метод генерации документа."""
        # Заголовок документа
        title = self.doc.add_heading('Отчет по статическому анализу проекта', level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 1. Дерево файлов
        self.doc.add_heading('1. Структура проекта', level=1)
        self.doc.add_paragraph('Ниже представлено текстовое дерево файлов анализируемой директории:')
        
        tree_para = self.doc.add_paragraph()
        tree_run = tree_para.add_run(self.tree_str)
        tree_run.font.name = self.EMOJI_FONT
        tree_run.font.size = Pt(10)

        # 2. Информация о JSON файлах
        if self.json_files:
            self.doc.add_heading('2. JSON конфигурации и данные', level=1)
            p = self.doc.add_paragraph('В проекте обнаружены следующие JSON файлы:')
            for jf in self.json_files:
                self.doc.add_paragraph(jf.name, style='List Bullet')

        # 3. Детальный анализ скриптов
        self.doc.add_heading('3. Анализ Python скриптов', level=1)
        
        for res in self.results:
            num = res['number']
            self.doc.add_heading(f"Скрипт №{num}: {res['name']}", level=2)
            self.doc.add_paragraph(f"Путь: {res['path']}", style='Intense Quote')

            if 'error' in res:
                err_para = self.doc.add_paragraph(style='Normal')
                err_run = err_para.add_run(f"⚠️ ОШИБКА АНАЛИЗА: {res['error']}")
                err_run.font.name = self.EMOJI_FONT
                err_run.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
                continue

            if res['module_docstring']:
                self.doc.add_heading('Описание модуля', level=3)
                self.doc.add_paragraph(res['module_docstring'])

            if res['global_vars']:
                self.doc.add_heading('Глобальные переменные', level=3)
                for var in res['global_vars']:
                    self.doc.add_paragraph(var, style='List Bullet')

            if res['functions']:
                self.doc.add_heading('Функции', level=3)
                for func in res['functions']:
                    args_str = ", ".join(func['args'])
                    self.doc.add_paragraph(f"{func['name']}({args_str})", style='List Bullet')
                    if func['docstring']:
                        p = self.doc.add_paragraph()
                        p.paragraph_format.left_indent = Inches(0.5)
                        p.add_run(f"Документация: {func['docstring']}").italic = True

            if res['classes']:
                self.doc.add_heading('Классы', level=3)
                for cls in res['classes']:
                    self.doc.add_paragraph(f"Класс: {cls['name']}", style='List Bullet')
                    if cls['docstring']:
                        p = self.doc.add_paragraph()
                        p.paragraph_format.left_indent = Inches(0.5)
                        p.add_run(f"Документация: {cls['docstring']}").italic = True
                    
                    for method in cls['methods']:
                        args_str = ", ".join(method['args'])
                        p = self.doc.add_paragraph()
                        p.paragraph_format.left_indent = Inches(0.5)
                        
                        p.add_run("└─ ")
                        run_keyword = p.add_run("def ")
                        run_keyword.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
                        run_keyword.bold = True
                        p.add_run(f"{method['name']}({args_str})")
                        
                        if method['docstring']:
                            p.add_run(f"\n   {method['docstring']}").italic = True

            if res['imports'] or res['cross_refs']:
                self.doc.add_heading('Зависимости и связи', level=3)
                
                if res['imports']:
                    self.doc.add_paragraph('Импорты:', style='List Bullet')
                    for imp in res['imports']:
                        p = self.doc.add_paragraph()
                        p.paragraph_format.left_indent = Inches(0.5)
                        p.add_run(imp)

                if res['cross_refs']:
                    self.doc.add_paragraph('Перекрестные ссылки на сущности проекта:', style='List Bullet')
                    table = self.doc.add_table(rows=1, cols=3)
                    table.style = 'Light List Accent 1'
                    hdr_cells = table.rows[0].cells
                    hdr_cells[0].text = 'Используемая сущность'
                    hdr_cells[1].text = 'Тип связи'
                    hdr_cells[2].text = 'Находится в скрипте №'
                    
                    # Сортируем по имени сущности и типу связи
                    sorted_refs = sorted(res['cross_refs'], key=lambda x: (x[0], x[2]))
                    
                    for entity, ref_num, link_type in sorted_refs:
                        row_cells = table.add_row().cells
                        row_cells[0].text = entity
                        
                        # Отображаем тип связи с цветовой маркировкой
                        type_cell = row_cells[1]
                        if link_type == "import":
                            type_cell.text = "Импорт"
                            type_cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0x00, 0x66, 0xCC)
                        elif link_type == "inheritance":
                            type_cell.text = "Наследование"
                            type_cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0x00, 0xAA, 0x00)
                        else:  # usage
                            type_cell.text = "Использование"
                            type_cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)
                        
                        row_cells[2].text = f"См. скрипт №{ref_num}"


        # 4. Блок-схема архитектуры анализируемого проекта
        self.doc.add_heading('4. Архитектура анализируемого проекта', level=1)
        self.doc.add_paragraph(
            'Ниже представлена диаграмма модулей проекта и связей между ними. '
            'Золотым цветом выделен главный модуль (точка входа). '
            'Стрелки показывают зависимости (импорты) между модулями:'
        )

        # Генерируем PNG с диаграммой
        flowchart_path = None
        try:
            # Передаём результаты анализа в генератор блок-схемы
            flowchart_path = FlowchartGenerator.generate(self.results)
            self.doc.add_picture(flowchart_path, width=Inches(6.5))
            last_paragraph = self.doc.paragraphs[-1]
            last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        except Exception as e:
            self.doc.add_paragraph(f"⚠️ Не удалось сгенерировать диаграмму: {e}")
        finally:
            if flowchart_path and os.path.exists(flowchart_path):
                try:
                    os.remove(flowchart_path)
                except OSError:
                    pass




        # Сохраняем документ
        self.doc.save(self.output_path)


# ==============================================================================
# Графический интерфейс (GUI) на Tkinter
# ==============================================================================
class AnalyzerApp:
    """Главное окно приложения с графическим интерфейсом."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Python Project Analyzer by Мэл")
        self.root.geometry("700x650")
        self.root.resizable(True, True)
        self._setup_ui()

    def _setup_ui(self):
        """Инициализация и размещение виджетов интерфейса."""
        tk.Label(self.root, text="Путь к анализируемому проекту:").pack(anchor='w', padx=10, pady=(10, 0))
        frame_folder = tk.Frame(self.root)
        frame_folder.pack(fill='x', padx=10)
        
        self.entry_folder = tk.Entry(frame_folder)
        self.entry_folder.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        btn_browse_folder = tk.Button(frame_folder, text="Обзор", command=self.browse_folder, width=10)
        btn_browse_folder.pack(side='right')

        tk.Label(self.root, text="Путь для сохранения отчета (.docx):").pack(anchor='w', padx=10, pady=(10, 0))
        frame_file = tk.Frame(self.root)
        frame_file.pack(fill='x', padx=10)
        
        self.entry_file = tk.Entry(frame_file)
        self.entry_file.insert(0, "report.docx")
        self.entry_file.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        btn_browse_file = tk.Button(frame_file, text="Обзор", command=self.browse_file, width=10)
        btn_browse_file.pack(side='right')

        tk.Label(self.root, text="Фильтр расширений (по одному в строке, оставьте пустым для всех файлов):").pack(anchor='w', padx=10, pady=(10, 0))
        frame_filter = tk.Frame(self.root, height=80)
        frame_filter.pack(fill='x', padx=10)
        
        self.text_extensions = scrolledtext.ScrolledText(frame_filter, height=4, wrap='word')
        self.text_extensions.pack(fill='x', expand=True)
        self.text_extensions.insert('1.0', ".py\n.json")

        self.btn_start = tk.Button(self.root, text="🚀 Выполнить анализ", command=self.start_analysis, 
                                   bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), height=2)
        self.btn_start.pack(pady=15, padx=10, fill='x')

        tk.Label(self.root, text="Статус выполнения и логи:").pack(anchor='w', padx=10)
        self.log_text = scrolledtext.ScrolledText(self.root, height=12, state='disabled', wrap='word')
        self.log_text.pack(fill='both', expand=True, padx=10, pady=(0, 10))

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с проектом")
        if folder:
            self.entry_folder.delete(0, tk.END)
            self.entry_folder.insert(0, folder)

    def browse_file(self):
        file = filedialog.asksaveasfilename(
            title="Сохранить отчет как",
            defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")]
        )
        if file:
            self.entry_file.delete(0, tk.END)
            self.entry_file.insert(0, file)

    def _parse_extensions(self):
        text = self.text_extensions.get('1.0', tk.END).strip()
        if not text:
            return None
        extensions = []
        for line in text.split('\n'):
            ext = line.strip()
            if ext:
                extensions.append(ext)
        return extensions if extensions else None

    def log(self, message):
        def _update():
            self.log_text.configure(state='normal')
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state='disabled')
        self.root.after(0, _update)

    def start_analysis(self):
        folder = self.entry_folder.get()
        file_out = self.entry_file.get()
        extensions = self._parse_extensions()

        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Ошибка", "Укажите корректный путь к папке с проектом!")
            return
        
        if not file_out.endswith('.docx'):
            messagebox.showerror("Ошибка", "Файл отчета должен иметь расширение .docx")
            return

        self.btn_start.configure(state='disabled', text="Анализ выполняется...")
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')

        thread = threading.Thread(target=self.run_analysis_thread, args=(folder, file_out, extensions))
        thread.daemon = True
        thread.start()

    def run_analysis_thread(self, folder, file_out, extensions):
        try:
            self.log("🟢 Начало анализа...")
            
            if extensions:
                self.log(f"🔍 Применён фильтр расширений: {', '.join(extensions)}")
            else:
                self.log("🔍 Фильтр не применён — показываются все файлы")
            
            self.log("📂 Сканирование директории и построение дерева...")
            builder = TreeBuilder(folder, allowed_extensions=extensions)
            tree_str, py_files, json_files = builder.build()
            self.log(f"✅ Найдено Python файлов: {len(py_files)}, JSON файлов: {len(json_files)}")

            if not py_files and not json_files:
                self.log("⚠️ В указанной папке не найдено файлов с указанными расширениями.")
                self._finish_analysis()
                return

            if py_files:
                analyzer = ASTAnalyzer(folder, py_files, self.log)
                analyzer.assign_numbers()
                analyzer.build_global_index()
                self.log(f"✅ Глобальный индекс построен. Уникальных сущностей: {len(analyzer.global_index)}")

                self.log("🔬 Детальный анализ содержимого скриптов...")
                results = []
                for i, file_path in enumerate(py_files, 1):
                    self.log(f"   -> Обработка [{i}/{len(py_files)}]: {file_path.name}")
                    res = analyzer.analyze_file(file_path)
                    results.append(res)
            else:
                results = []
                self.log("ℹ️ Python файлы не найдены — анализ кода пропущен")

            self.log("📝 Формирование отчета в формате .docx...")
            generator = ReportGenerator(file_out, tree_str, results, json_files)
            generator.generate()

            self.log(f"🎉 Готово! Отчет успешно сохранен:\n{file_out}")
            messagebox.showinfo("Успех", f"Анализ завершен!\nОтчет сохранен в:\n{file_out}")

        except Exception as e:
            self.log(f"❌ Критическая ошибка при выполнении: {e}")
            messagebox.showerror("Критическая ошибка", str(e))
            
        finally:
            self._finish_analysis()

    def _finish_analysis(self):
        def _update():
            self.btn_start.configure(state='normal', text="🚀 Выполнить анализ")
        self.root.after(0, _update)


# ==============================================================================
# Точка входа в программу
# ==============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = AnalyzerApp(root)
    root.mainloop()