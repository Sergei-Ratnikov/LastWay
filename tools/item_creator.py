"""
=============================================================================
ITEM CREATOR — Утилита для создания и редактирования предметов в игре Last Way
=============================================================================
Графический интерфейс на tkinter для работы с data/items.json.
Автоматически читает структуру полей из классов-наследников Item в objects/.

Запуск: python tools/item_creator.py (из корня проекта)
"""

import sys
import os
import json
import inspect
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path


# ---------------------------------------------------------------------------
# НАСТРОЙКА ПУТЕЙ (ДОЛЖНА БЫТЬ ПЕРЕД ИМПОРТАМИ ИЗ ПРОЕКТА!)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# ---------------------------------------------------------------------------
# ИМПОРТЫ ИЗ ПРОЕКТА (теперь Python знает, где искать папку objects)
# ---------------------------------------------------------------------------
from objects.item import PaperDollSlot


# ---------------------------------------------------------------------------
# НАСТРОЙКА ПУТЕЙ
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

ITEMS_JSON_PATH = os.path.join(PROJECT_ROOT, "data", "items.json")
OBJECTS_DIR = os.path.join(PROJECT_ROOT, "objects")

# ---------------------------------------------------------------------------
# ПОЛЯ С ОГРАНИЧЕННЫМ НАБОРОМ ЗНАЧЕНИЙ (ВЫПАДАЮЩИЕ СПИСКИ)
# ---------------------------------------------------------------------------
# Маппинг: имя поля → список допустимых значений.
# Для таких полей в форме автоматически создаётся Combobox вместо Entry.
# Расширяется просто: добавил строку — и поле стало выпадающим.
ENUM_FIELDS = {
    "slot": [slot.value for slot in PaperDollSlot],  # clothing, patch, weapon, tool, ring, amulet
    # В будущем можно добавить:
    # "attack_type": ["piercing", "slashing", "blunt"],
    # "ammo_type": ["bolt", "arrow", "bullet"],
    # "weapon_class": ["dagger", "sword", "crossbow", "staff"],
}

# ---------------------------------------------------------------------------
# ДИНАМИЧЕСКОЕ СКАНИРОВАНИЕ КЛАССОВ
# ---------------------------------------------------------------------------

def discover_item_classes():
    """
    Сканирует папку objects/ и находит все классы-наследники Item.
    Возвращает словарь {category_name: class}.
    """
    from objects.item import Item, ItemCategory
    
    item_classes = {}
    
    # Ищем все файлы item_*.py в папке objects
    objects_path = Path(OBJECTS_DIR)
    for py_file in objects_path.glob("item_*.py"):
        module_name = f"objects.{py_file.stem}"
        try:
            # Динамический импорт модуля
            module = __import__(module_name, fromlist=[''])
            
            # Ищем все классы в модуле, которые наследуются от Item
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Item) and obj != Item:
                    # Извлекаем category из класса (пытаемся найти в __init__)
                    category_name = extract_category_from_class(obj)
                    if category_name:
                        item_classes[category_name] = obj
        except Exception as e:
            print(f"Предупреждение: не удалось загрузить {module_name}: {e}")
    
    return item_classes


def extract_category_from_class(cls):
    """
    Пытается извлечь category из класса (через проверку в __init__).
    Это эвристика — работает для наших классов.
    """
    # Проверяем имя класса
    class_name_lower = cls.__name__.lower()
    
    # Маппинг имён классов на категории
    category_map = {
        'document': 'document',
        'key': 'key',
        'quest': 'quest',
        'clothing': 'clothing',
        'weapon': 'weapon',
        'consumable': 'consumable',
        'tool': 'tool',
        'valuable': 'valuable',
        'ingredient': 'ingredient',
        'jewelry': 'jewelry',
    }
    
    for key, category in category_map.items():
        if key in class_name_lower:
            return category
    
    return None

def get_fields_for_class(cls):
    """
    Извлекает список полей из класса через анализ __init__.
    Для полей из ENUM_FIELDS помечает тип как 'enum' и сохраняет варианты.
    Возвращает список словарей с описанием полей.
    """
    fields = []
    
    try:
        sig = inspect.signature(cls.__init__)
        for param_name, param in sig.parameters.items():
            # Пропускаем служебные параметры
            if param_name in ['self', 'item_id', 'quantity']:
                continue
            
            # Определяем тип поля
            field_type = 'str'  # по умолчанию
            default_value = None
            enum_values = None
            
            # --- ПРОВЕРКА НА ENUM-ПОЛЕ (выпадающий список) ---
            if param_name in ENUM_FIELDS:
                field_type = 'enum'
                enum_values = ENUM_FIELDS[param_name]
                default_value = param.default if param.default != inspect.Parameter.empty else enum_values[0]
            elif param.default != inspect.Parameter.empty:
                default_value = param.default
                # Определяем тип по значению по умолчанию
                if isinstance(default_value, bool):
                    field_type = 'bool'
                elif isinstance(default_value, int):
                    field_type = 'int'
                elif isinstance(default_value, float):
                    field_type = 'float'
                elif isinstance(default_value, list):
                    field_type = 'list'
            
            fields.append({
                'name': param_name,
                'type': field_type,
                'default': default_value,
                'required': param.default == inspect.Parameter.empty,
                'enum_values': enum_values,  # Только для type='enum'
            })
    except Exception as e:
        print(f"Предупреждение: не удалось извлечь поля из {cls.__name__}: {e}")
    
    return fields

# ---------------------------------------------------------------------------
# ГЛАВНОЕ ПРИЛОЖЕНИЕ
# ---------------------------------------------------------------------------

class ItemCreatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Last Way — Item Creator")
        self.root.geometry("1200x750")
        self.root.minsize(1000, 650)
        
        # Загружаем данные
        self.items_data = {}
        self._load_items_json()
        
        # Сканируем классы предметов
        self.item_classes = discover_item_classes()
        self.class_fields_cache = {}  # {category: [fields]}
        
        for category, cls in self.item_classes.items():
            self.class_fields_cache[category] = get_fields_for_class(cls)
        
        self.current_editing_id = None
        self.field_widgets = {}  # {field_name: (widget, var)}
        
        self._build_ui()
        self._refresh_items_list()
    
    def _load_items_json(self):
        if not os.path.exists(ITEMS_JSON_PATH):
            self.items_data = {}
            return
        try:
            with open(ITEMS_JSON_PATH, "r", encoding="utf-8") as f:
                self.items_data = json.load(f)
        except Exception as e:
            messagebox.showerror("Ошибка чтения", f"Не удалось прочитать items.json:\n{e}")
            self.items_data = {}
    
    def _save_items_json(self):
        try:
            with open(ITEMS_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(self.items_data, f, ensure_ascii=False, indent=2, sort_keys=True)
            return True
        except Exception as e:
            messagebox.showerror("Ошибка записи", f"Не удалось сохранить items.json:\n{e}")
            return False
    
    def _build_ui(self):
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- ЛЕВАЯ ПАНЕЛЬ ---
        left_frame = ttk.Frame(main_paned, width=300)
        main_paned.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="Существующие предметы", 
                  font=("Arial", 11, "bold")).pack(pady=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._refresh_items_list())
        search_entry = ttk.Entry(left_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(left_frame, text="(поиск по ID и имени)", 
                  font=("Arial", 8)).pack()
        
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.items_listbox = tk.Listbox(
            list_frame, 
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            selectmode=tk.SINGLE
        )
        self.items_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.items_listbox.yview)
        self.items_listbox.bind("<<ListboxSelect>>", self._on_item_selected)
        
        ttk.Button(left_frame, text="➕ Новый предмет", 
                   command=self._new_item).pack(fill=tk.X, pady=2)
        ttk.Button(left_frame, text="🗑 Удалить выбранный", 
                   command=self._delete_item).pack(fill=tk.X, pady=2)
        
        # --- ПРАВАЯ ПАНЕЛЬ ---
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)
        
        ttk.Label(right_frame, text="Параметры предмета", 
                  font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # Выбор категории
        category_frame = ttk.Frame(right_frame)
        category_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(category_frame, text="Категория:", 
                  font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        
        self.category_var = tk.StringVar()
        category_values = list(self.item_classes.keys())
        self.category_combobox = ttk.Combobox(
            category_frame, 
            textvariable=self.category_var,
            values=category_values, 
            state="readonly", 
            width=30
        )
        self.category_combobox.pack(side=tk.LEFT, padx=5)
        self.category_combobox.bind("<<ComboboxSelected>>", self._on_category_changed)
        
        if category_values:
            self.category_combobox.set(category_values[0])
        
        # Форма с прокруткой
        form_canvas = tk.Canvas(right_frame, highlightthickness=0)
        form_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, 
                                        command=form_canvas.yview)
        self.form_frame = ttk.Frame(form_canvas)
        
        self.form_frame.bind(
            "<Configure>",
            lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all"))
        )
        
        form_canvas.create_window((0, 0), window=self.form_frame, anchor="nw")
        form_canvas.configure(yscrollcommand=form_scrollbar.set)
        
        form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        form_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # -----------------------------------------------------------------
        # FIX: Создаём ОТДЕЛЬНЫЙ фрейм для базовых полей.
        # Это решает ошибку Tkinter "cannot use geometry manager pack inside
        # ... which already has slaves managed by grid".
        # Теперь базовые поля используют grid внутри base_fields_frame,
        # а сам base_fields_frame упакован через pack в form_frame.
        # -----------------------------------------------------------------
        self.base_fields_frame = ttk.Frame(self.form_frame)
        self.base_fields_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Создаём базовые поля (используют grid внутри base_fields_frame)
        self._build_base_fields()
        
        # Контейнер для динамических полей (тоже pack в form_frame)
        self.dynamic_fields_frame = ttk.Frame(self.form_frame)
        self.dynamic_fields_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Кнопки
        buttons_frame = ttk.Frame(right_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(buttons_frame, text="💾 Сохранить в items.json", 
                   command=self._save_current_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="🔄 Очистить форму", 
                   command=self._clear_form).pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Генерируем поля для начальной категории
        self._on_category_changed(None)
    
    def _build_base_fields(self):
        """
        Создаёт базовые поля (общие для всех предметов).
        FIX: все виджеты размещаются внутри self.base_fields_frame через grid.
        """
        self.base_fields = {}
        row = 0
        parent = self.base_fields_frame  # <-- FIX: используем отдельный фрейм
        
        # ID
        ttk.Label(parent, text="ID (уникальный ключ):", 
                  font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=5, pady=5)
        self.base_fields["id"] = tk.StringVar()
        ttk.Entry(parent, textvariable=self.base_fields["id"], 
                  width=40, font=("Consolas", 10)).grid(
            row=row, column=1, sticky="ew", padx=5, pady=5)
        row += 1
        
        # Наименование
        ttk.Label(parent, text="Наименование *:", 
                  font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=5, pady=5)
        self.base_fields["name"] = tk.StringVar()
        ttk.Entry(parent, textvariable=self.base_fields["name"], 
                  width=40).grid(
            row=row, column=1, sticky="ew", padx=5, pady=5)
        row += 1
        
        # Вес
        ttk.Label(parent, text="Вес (кг):").grid(
            row=row, column=0, sticky="w", padx=5, pady=3)
        self.base_fields["weight"] = tk.DoubleVar(value=0.0)
        ttk.Spinbox(parent, textvariable=self.base_fields["weight"],
                    from_=0.0, to=1000.0, increment=0.1, width=37).grid(
            row=row, column=1, sticky="ew", padx=5, pady=3)
        row += 1
        
        # Объём
        ttk.Label(parent, text="Объём (слоты):").grid(
            row=row, column=0, sticky="w", padx=5, pady=3)
        self.base_fields["volume"] = tk.IntVar(value=1)
        ttk.Spinbox(parent, textvariable=self.base_fields["volume"],
                    from_=1, to=100, increment=1, width=37).grid(
            row=row, column=1, sticky="ew", padx=5, pady=3)
        row += 1
        
        # Стоимость
        ttk.Label(parent, text="Стоимость (монеты):").grid(
            row=row, column=0, sticky="w", padx=5, pady=3)
        self.base_fields["cost"] = tk.IntVar(value=0)
        ttk.Spinbox(parent, textvariable=self.base_fields["cost"],
                    from_=0, to=100000, increment=1, width=37).grid(
            row=row, column=1, sticky="ew", padx=5, pady=3)
        row += 1
        
        # Прочность
        ttk.Label(parent, text="Прочность (0-100):").grid(
            row=row, column=0, sticky="w", padx=5, pady=3)
        self.base_fields["durability"] = tk.IntVar(value=100)
        ttk.Spinbox(parent, textvariable=self.base_fields["durability"],
                    from_=0, to=100, increment=1, width=37).grid(
            row=row, column=1, sticky="ew", padx=5, pady=3)
        row += 1
        
        # Можно надеть
        self.base_fields["equippable"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="Можно надеть на Paper Doll",
                        variable=self.base_fields["equippable"]).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=5, pady=3)
        row += 1
        
        # Ограничение по полу
        ttk.Label(parent, text="Ограничение по полу:").grid(
            row=row, column=0, sticky="w", padx=5, pady=3)
        self.base_fields["gender_restrict"] = tk.StringVar(value="any")
        ttk.Combobox(parent, textvariable=self.base_fields["gender_restrict"],
                     values=["any", "male", "female"], state="readonly", width=37).grid(
            row=row, column=1, sticky="ew", padx=5, pady=3)
        row += 1
        
        # FIX: настраиваем растягивание колонки внутри base_fields_frame
        parent.columnconfigure(1, weight=1)
    
    def _on_category_changed(self, event):
        """Обработчик смены категории — перестраивает динамические поля."""
        category = self.category_var.get()
        if not category:
            return
        
        # Очищаем старые динамические поля
        for widget in self.dynamic_fields_frame.winfo_children():
            widget.destroy()
        self.field_widgets.clear()
        
        # Получаем поля для этой категории
        fields = self.class_fields_cache.get(category, [])
        
        if not fields:
            ttk.Label(self.dynamic_fields_frame, 
                      text="(нет специфичных полей для этой категории)",
                      foreground="gray").pack(pady=10)
            return
        
        # Разделитель
        ttk.Separator(self.dynamic_fields_frame, orient=tk.HORIZONTAL).pack(
            fill=tk.X, padx=5, pady=10)
        
        ttk.Label(self.dynamic_fields_frame, 
                  text=f"Специфичные поля для категории '{category}':",
                  font=("Arial", 10, "bold")).pack(anchor="w", padx=5, pady=5)
        
        # Контейнер для grid внутри dynamic_fields_frame
        grid_frame = ttk.Frame(self.dynamic_fields_frame)
        grid_frame.pack(fill=tk.BOTH, expand=True)
        
        # Генерируем поля
        # Генерируем поля
        row = 0
        for field in fields:
            field_name = field['name']
            field_type = field['type']
            default = field['default']
            required = field['required']
            enum_values = field.get('enum_values')
            
            label_text = field_name.replace('_', ' ').title()
            if required:
                label_text += " *"
            
            ttk.Label(grid_frame, text=label_text + ":").grid(
                row=row, column=0, sticky="w", padx=5, pady=3)
            
            # Создаём виджет в зависимости от типа
            if field_type == 'bool':
                var = tk.BooleanVar(value=default if default is not None else False)
                widget = ttk.Checkbutton(grid_frame, variable=var)
            elif field_type == 'int':
                var = tk.IntVar(value=default if default is not None else 0)
                widget = ttk.Spinbox(grid_frame, textvariable=var,
                                    from_=-10000, to=10000, increment=1, width=37)
            elif field_type == 'float':
                var = tk.DoubleVar(value=default if default is not None else 0.0)
                widget = ttk.Spinbox(grid_frame, textvariable=var,
                                    from_=-10000.0, to=10000.0, increment=0.1, width=37)
            elif field_type == 'enum':
                # --- ВЫПАДАЮЩИЙ СПИСОК ---
                var = tk.StringVar(value=default if default is not None else enum_values[0])
                widget = ttk.Combobox(grid_frame, textvariable=var,
                                      values=enum_values, state="readonly", width=37)
            elif field_type == 'list':
                var = tk.StringVar(value="" if default is None else ", ".join(default))
                widget = ttk.Entry(grid_frame, textvariable=var, width=40)
                ttk.Label(grid_frame, 
                          text="(значения через запятую)", 
                          font=("Arial", 8)).grid(
                    row=row, column=2, sticky="w", padx=5)
            else:  # str
                var = tk.StringVar(value=default if default is not None else "")
                widget = ttk.Entry(grid_frame, textvariable=var, width=40)
            
            widget.grid(row=row, column=1, sticky="ew", padx=5, pady=3)
            self.field_widgets[field_name] = (widget, var, field_type)
            row += 1
   
        grid_frame.columnconfigure(1, weight=1)
    
    def _refresh_items_list(self):
        self.items_listbox.delete(0, tk.END)
        search_term = self.search_var.get().lower().strip()
        
        sorted_ids = sorted(self.items_data.keys())
        
        for item_id in sorted_ids:
            item_props = self.items_data[item_id]
            item_name = item_props.get("name", item_id)
            category = item_props.get("category", "unknown")
            
            # Проверяем, есть ли все нужные поля
            fields = self.class_fields_cache.get(category, [])
            missing_fields = [f['name'] for f in fields if f['name'] not in item_props]
            
            if search_term:
                if search_term not in item_id.lower() and search_term not in item_name.lower():
                    continue
            
            # Добавляем маркер, если есть пропущенные поля
            marker = " ⚠️" if missing_fields else ""
            display_text = f"{item_id} — {item_name}{marker}"
            self.items_listbox.insert(tk.END, display_text)
    
    def _on_item_selected(self, event):
        selection = self.items_listbox.curselection()
        if not selection:
            return
        
        display_text = self.items_listbox.get(selection[0])
        item_id = display_text.split(" — ")[0].replace(" ⚠️", "")
        
        if item_id not in self.items_data:
            return
        
        self._load_item_to_form(item_id)
    
    def _clear_form(self):
        self.current_editing_id = None
        self.base_fields["id"].set("")
        self.base_fields["name"].set("")
        self.base_fields["weight"].set(0.0)
        self.base_fields["volume"].set(1)
        self.base_fields["cost"].set(0)
        self.base_fields["durability"].set(100)
        self.base_fields["equippable"].set(False)
        self.base_fields["gender_restrict"].set("any")
        
        # Очищаем динамические поля
        for field_name, (widget, var, field_type) in self.field_widgets.items():
            if field_type == 'bool':
                var.set(False)
            elif field_type in ('int', 'float'):
                var.set(0)
            elif field_type == 'list':
                var.set("")
            else:
                var.set("")
        
        self.status_var.set("Форма очищена. Создать новый предмет.")
    
    def _new_item(self):
        self._clear_form()
        self.items_listbox.selection_clear(0, tk.END)
        self.status_var.set("Режим создания нового предмета.")
    
    def _load_item_to_form(self, item_id):
        self.current_editing_id = item_id
        props = self.items_data[item_id]
        
        # Базовые поля
        self.base_fields["id"].set(item_id)
        self.base_fields["name"].set(props.get("name", ""))
        self.base_fields["weight"].set(float(props.get("weight", 0.0)))
        self.base_fields["volume"].set(int(props.get("volume", 1)))
        self.base_fields["cost"].set(int(props.get("cost", 0)))
        self.base_fields["durability"].set(int(props.get("durability", 100)))
        self.base_fields["equippable"].set(bool(props.get("equippable", False)))
        self.base_fields["gender_restrict"].set(props.get("gender_restrict", "any"))
        
        # Категория
        category = props.get("category", "")
        if category in self.item_classes:
            self.category_combobox.set(category)
            self._on_category_changed(None)
        

        # Динамические поля
        for field_name, (widget, var, field_type) in self.field_widgets.items():
            value = props.get(field_name)
            if value is not None:
                if field_type == 'bool':
                    var.set(bool(value))
                elif field_type == 'int':
                    var.set(int(value))
                elif field_type == 'float':
                    var.set(float(value))
                elif field_type == 'enum':
                    # Для enum-полей значение уже строка, просто устанавливаем
                    var.set(str(value))
                elif field_type == 'list':
                    var.set(", ".join(value) if isinstance(value, list) else str(value))
                else:
                    var.set(str(value))
        
        self.status_var.set(f"Редактирование: {item_id}")
    
    def _save_current_item(self):
        # Валидация базовых полей
        item_id = self.base_fields["id"].get().strip()
        name = self.base_fields["name"].get().strip()
        category = self.category_var.get()
        
        if not item_id:
            messagebox.showwarning("Ошибка валидации", "Поле 'ID' не может быть пустым.")
            return
        
        if not all(c.isalnum() or c in "_-" for c in item_id):
            messagebox.showwarning(
                "Ошибка валидации", 
                "ID может содержать только латинские буквы, цифры, _ и -."
            )
            return
        
        if not name:
            messagebox.showwarning("Ошибка валидации", "Поле 'Наименование' не может быть пустым.")
            return
        
        if not category:
            messagebox.showwarning("Ошибка валидации", "Выберите категорию.")
            return
        
        # Проверка дубликатов
        if self.current_editing_id is None and item_id in self.items_data:
            if not messagebox.askyesno(
                "Предмет уже существует",
                f"Предмет с ID '{item_id}' уже есть.\nПерезаписать?"
            ):
                return
        
        # Собираем словарь
        item_dict = {
            "name": name,
            "category": category,
            "weight": round(float(self.base_fields["weight"].get()), 2),
            "volume": int(self.base_fields["volume"].get()),
            "cost": int(self.base_fields["cost"].get()),
            "durability": int(self.base_fields["durability"].get()),
            "equippable": bool(self.base_fields["equippable"].get()),
            "gender_restrict": self.base_fields["gender_restrict"].get()
        }
        
        # Добавляем storage_type на основе категории
        storage_map = {
            'document': 'archive',
            'key': 'archive',
            'quest': 'casket',
            'clothing': 'burden',
            'weapon': 'burden',
            'consumable': 'burden',
            'tool': 'burden',
            'valuable': 'casket',
            'ingredient': 'burden',
            'jewelry': 'casket',
        }
        item_dict["storage_type"] = storage_map.get(category, "burden")
        
        # Добавляем динамические поля
        for field_name, (widget, var, field_type) in self.field_widgets.items():
            value = var.get()
            if field_type == 'list':
                # Преобразуем строку в список
                if value.strip():
                    item_dict[field_name] = [v.strip() for v in value.split(",")]
                else:
                    item_dict[field_name] = []
            elif field_type == 'enum':
                # Enum-поле — сохраняем как строку (значение из выпадающего списка)
                item_dict[field_name] = str(value)
            else:
                item_dict[field_name] = value


        # Удаляем старый, если меняли ID
        if self.current_editing_id and self.current_editing_id != item_id:
            if self.current_editing_id in self.items_data:
                del self.items_data[self.current_editing_id]
        
        self.items_data[item_id] = item_dict
        
        if self._save_items_json():
            self.status_var.set(f"✅ Предмет '{item_id}' успешно сохранён.")
            self.current_editing_id = item_id
            self._refresh_items_list()
            
            for i in range(self.items_listbox.size()):
                if self.items_listbox.get(i).startswith(item_id + " —"):
                    self.items_listbox.selection_clear(0, tk.END)
                    self.items_listbox.selection_set(i)
                    self.items_listbox.see(i)
                    break
    
    def _delete_item(self):
        selection = self.items_listbox.curselection()
        if not selection:
            messagebox.showinfo("Нет выбора", "Выберите предмет для удаления.")
            return
        
        display_text = self.items_listbox.get(selection[0])
        item_id = display_text.split(" — ")[0].replace(" ⚠️", "")
        
        if not messagebox.askyesno(
            "Подтверждение удаления",
            f"Удалить предмет '{item_id}' из items.json?"
        ):
            return
        
        if item_id in self.items_data:
            del self.items_data[item_id]
            if self._save_items_json():
                self.status_var.set(f"🗑 Предмет '{item_id}' удалён.")
                self._new_item()
                self._refresh_items_list()


def main():
    root = tk.Tk()
    
    style = ttk.Style()
    try:
        style.theme_use("vista")
    except tk.TclError:
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
    
    app = ItemCreatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()