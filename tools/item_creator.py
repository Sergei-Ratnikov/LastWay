"""
=============================================================================
ITEM CREATOR — Утилита для создания и редактирования предметов в игре Last Way
=============================================================================
Графический интерфейс на tkinter для работы с data/items.json.
Автоматически читает структуру полей из классов-наследников Item в objects/.
Автогенерация ID в реальном времени при смене категории или суффикса.

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
# НАСТРОЙКА ПУТЕЙ (ОБЯЗАТЕЛЬНО ПЕРЕД ИМПОРТАМИ ИЗ ПРОЕКТА!)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# ИМПОРТЫ ИЗ ПРОЕКТА
# ---------------------------------------------------------------------------
from objects.item import PaperDollSlot

# ---------------------------------------------------------------------------
# КОНСТАНТЫ
# ---------------------------------------------------------------------------
ITEMS_JSON_PATH = os.path.join(PROJECT_ROOT, "data", "items.json")
OBJECTS_DIR = os.path.join(PROJECT_ROOT, "objects")

# Префиксы для автогенерации ID по категориям
ITEM_PREFIXES = {
    "consumable": "con", "document": "doc", "key": "key",
    "weapon": "wea", "clothing": "clo", "tool": "too",
    "jewelry": "jew", "valuable": "val", "quest": "que", "ingredient": "ing"
}

# Маппинг категории → тип хранения (storage_type)
STORAGE_MAP = {
    'document': 'archive', 'key': 'archive',
    'quest': 'casket', 'valuable': 'casket', 'jewelry': 'casket',
    'clothing': 'burden', 'weapon': 'burden', 'consumable': 'burden',
    'tool': 'burden', 'ingredient': 'burden',
}

# Поля с ограниченным набором значений (выпадающие списки)
ENUM_FIELDS = {
    "slot": [slot.value for slot in PaperDollSlot],
}


# ---------------------------------------------------------------------------
# ГЕНЕРАТОР ID ПРЕДМЕТА
# ---------------------------------------------------------------------------
def generate_item_id(category: str, items_data: dict, custom_suffix: str = "") -> str:
    """
    Генерирует ID вида: id_inv_{prefix}_{NNN}[_suffix]
    
    Пример:
        category="weapon", custom_suffix="dagger" → id_inv_wea_003_dagger
        category="document", custom_suffix=""     → id_inv_doc_001
    """
    prefix = ITEM_PREFIXES.get(category, "itm")
    
    max_num = 0
    search_str = f"id_inv_{prefix}_"
    for item_id in items_data.keys():
        if item_id.startswith(search_str):
            parts = item_id.split("_")
            if len(parts) >= 4:
                try:
                    num = int(parts[3])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
    
    new_id = f"id_inv_{prefix}_{max_num + 1:03d}"
    
    if custom_suffix:
        suffix = custom_suffix.strip().replace(" ", "_").lower()
        suffix = ''.join(c for c in suffix if c.isalnum() or c in "_-")
        if suffix:
            new_id += f"_{suffix}"
    
    return new_id


# ---------------------------------------------------------------------------
# ДИНАМИЧЕСКОЕ СКАНИРОВАНИЕ КЛАССОВ
# ---------------------------------------------------------------------------
def discover_item_classes():
    """Сканирует папку objects/ и находит все классы-наследники Item."""
    from objects.item import Item
    
    item_classes = {}
    objects_path = Path(OBJECTS_DIR)
    
    for py_file in objects_path.glob("item_*.py"):
        module_name = f"objects.{py_file.stem}"
        try:
            module = __import__(module_name, fromlist=[''])
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Item) and obj != Item:
                    category_name = extract_category_from_class(obj)
                    if category_name:
                        item_classes[category_name] = obj
        except Exception as e:
            print(f"Предупреждение: не удалось загрузить {module_name}: {e}")
    
    return item_classes


def extract_category_from_class(cls):
    """Извлекает category из имени класса (эвристика)."""
    class_name_lower = cls.__name__.lower()
    
    category_map = {
        'document': 'document', 'key': 'key', 'quest': 'quest',
        'clothing': 'clothing', 'weapon': 'weapon', 'consumable': 'consumable',
        'tool': 'tool', 'valuable': 'valuable', 'ingredient': 'ingredient',
        'jewelry': 'jewelry',
    }
    
    for key, category in category_map.items():
        if key in class_name_lower:
            return category
    
    return None


def get_fields_for_class(cls):
    """Извлекает список полей из __init__ класса."""
    fields = []
    
    try:
        sig = inspect.signature(cls.__init__)
        for param_name, param in sig.parameters.items():
            if param_name in ['self', 'item_id', 'quantity']:
                continue
            
            field_type = 'str'
            default_value = None
            enum_values = None
            
            if param_name in ENUM_FIELDS:
                field_type = 'enum'
                enum_values = ENUM_FIELDS[param_name]
                default_value = param.default if param.default != inspect.Parameter.empty else enum_values[0]
            elif param.default != inspect.Parameter.empty:
                default_value = param.default
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
                'enum_values': enum_values,
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
        self.class_fields_cache = {}
        
        for category, cls in self.item_classes.items():
            self.class_fields_cache[category] = get_fields_for_class(cls)
        
        self.current_editing_id = None
        self.current_generated_id = None  # Сгенерированный ID для нового предмета
        self.field_widgets = {}
        
        self._build_ui()
        self._populate_list()
    
    # =========================================================================
    # ЗАГРУЗКА / СОХРАНЕНИЕ JSON
    # =========================================================================
    
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
    
    # =========================================================================
    # ПОСТРОЕНИЕ UI
    # =========================================================================
    
    def _build_ui(self):
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- ЛЕВАЯ ПАНЕЛЬ ---
        left_frame = ttk.Frame(main_paned, width=300)
        main_paned.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="Существующие предметы", 
                  font=("Arial", 11, "bold")).pack(pady=(0, 5))
        
        # Фильтр по категории
        filter_frame = ttk.Frame(left_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(filter_frame, text="Фильтр:", font=("Arial", 9)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.filter_var = tk.StringVar(value="Все")
        filter_values = ["Все"] + sorted(list(ITEM_PREFIXES.keys()))
        self.filter_combo = ttk.Combobox(
            filter_frame, textvariable=self.filter_var,
            values=filter_values, state="readonly", width=20
        )
        self.filter_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self._populate_list())
        
        # Поиск
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._populate_list())
        search_entry = ttk.Entry(left_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(left_frame, text="(поиск по ID и имени)", 
                  font=("Arial", 8)).pack()
        
        # Список предметов
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
        
        # Кнопки
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
        category_values = sorted(list(self.item_classes.keys()))
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
        
        # Базовые поля
        self.base_fields_frame = ttk.Frame(self.form_frame)
        self.base_fields_frame.pack(fill=tk.X, padx=5, pady=5)
        self._build_base_fields()
        
        # Динамические поля
        self.dynamic_fields_frame = ttk.Frame(self.form_frame)
        self.dynamic_fields_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Кнопки
        buttons_frame = ttk.Frame(right_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(buttons_frame, text="💾 Сохранить в items.json", 
                   command=self._save_current_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="🔄 Очистить форму", 
                   command=self._clear_form).pack(side=tk.LEFT, padx=5)
        
        # Статус
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Генерируем поля для начальной категории
        self._on_category_changed(None)
    
    def _build_base_fields(self):
        """Создаёт базовые поля (общие для всех предметов)."""
        self.base_fields = {}
        row = 0
        parent = self.base_fields_frame
        
        # ------------------------------------------------------------------
        # ID (Label, не редактируется вручную)
        # ------------------------------------------------------------------
        ttk.Label(parent, text="ID (автогенерация):", 
                  font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=5, pady=5)
        
        # Label для отображения сгенерированного ID
        self.id_label = ttk.Label(
            parent, text="(выберите категорию)",
            font=("Consolas", 10, "bold"),
            foreground="blue"
        )
        self.id_label.grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1
        
        # ------------------------------------------------------------------
        # Суффикс ID (редактируемый, влияет на автогенерацию)
        # ------------------------------------------------------------------
        ttk.Label(parent, text="Суффикс ID (опц.):", 
                  font=("Arial", 9)).grid(
            row=row, column=0, sticky="w", padx=5, pady=3)
        self.suffix_var = tk.StringVar()
        self.suffix_entry = ttk.Entry(parent, textvariable=self.suffix_var, width=40)
        self.suffix_entry.grid(row=row, column=1, sticky="ew", padx=5, pady=3)
        # Привязываем обработчик изменения суффикса
        self.suffix_var.trace_add("write", lambda *args: self._update_generated_id())
        ttk.Label(parent, text="(например: dagger, healing_potion)", 
                  font=("Arial", 8), foreground="gray").grid(
            row=row, column=2, sticky="w", padx=5)
        row += 1
        
        # ------------------------------------------------------------------
        # Наименование
        # ------------------------------------------------------------------
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
        
        parent.columnconfigure(1, weight=1)
    
    # =========================================================================
    # АВТОГЕНЕРАЦИЯ ID
    # =========================================================================
    
    def _update_generated_id(self):
        """
        Пересчитывает и отображает сгенерированный ID.
        Вызывается при смене категории или суффикса.
        """
        if self.current_editing_id is not None:
            # Режим редактирования — ID фиксирован, не пересчитываем
            return
        
        category = self.category_var.get()
        suffix = self.suffix_var.get().strip() if hasattr(self, 'suffix_var') else ""
        
        if not category:
            self.id_label.config(text="(выберите категорию)", foreground="gray")
            self.current_generated_id = None
            return
        
        # Генерируем новый ID
        new_id = generate_item_id(category, self.items_data, suffix)
        self.current_generated_id = new_id
        
        # Проверяем, не конфликтует ли с существующими
        if new_id in self.items_data:
            # Маловероятно, но на всякий случай подсветим красным
            self.id_label.config(text=new_id + " ⚠️ КОНФЛИКТ!", foreground="red")
        else:
            self.id_label.config(text=new_id, foreground="blue")
    
    # =========================================================================
    # ДИНАМИЧЕСКИЕ ПОЛЯ
    # =========================================================================
    
    def _on_category_changed(self, event):
        """Обработчик смены категории — перестраивает динамические поля и ID."""
        category = self.category_var.get()
        if not category:
            return
        
        # Очищаем старые динамические поля
        for widget in self.dynamic_fields_frame.winfo_children():
            widget.destroy()
        self.field_widgets.clear()
        
        fields = self.class_fields_cache.get(category, [])
        
        if not fields:
            ttk.Label(self.dynamic_fields_frame, 
                      text="(нет специфичных полей для этой категории)",
                      foreground="gray").pack(pady=10)
        else:
            ttk.Separator(self.dynamic_fields_frame, orient=tk.HORIZONTAL).pack(
                fill=tk.X, padx=5, pady=10)
            
            ttk.Label(self.dynamic_fields_frame, 
                      text=f"Специфичные поля для категории '{category}':",
                      font=("Arial", 10, "bold")).pack(anchor="w", padx=5, pady=5)
            
            grid_frame = ttk.Frame(self.dynamic_fields_frame)
            grid_frame.pack(fill=tk.BOTH, expand=True)
            
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
        
        # ВАЖНО: перегенерировать ID при смене категории
        self._update_generated_id()
    
    # =========================================================================
    # СПИСОК ПРЕДМЕТОВ
    # =========================================================================
    
    def _populate_list(self):
        """Заполняет список предметов с учётом фильтра и поиска."""
        self.items_listbox.delete(0, tk.END)
        
        search_term = self.search_var.get().lower().strip()
        filter_category = self.filter_var.get()
        
        sorted_ids = sorted(self.items_data.keys())
        
        for item_id in sorted_ids:
            item_props = self.items_data[item_id]
            item_name = item_props.get("name", item_id)
            category = item_props.get("category", "unknown")
            
            if filter_category != "Все" and category != filter_category:
                continue
            
            if search_term:
                if search_term not in item_id.lower() and search_term not in item_name.lower():
                    continue
            
            fields = self.class_fields_cache.get(category, [])
            missing_fields = [f['name'] for f in fields if f['name'] not in item_props]
            marker = " ⚠️" if missing_fields else ""
            
            display_text = f"{item_id} — {item_name}{marker}"
            self.items_listbox.insert(tk.END, display_text)
    
    def _on_item_selected(self, event):
        """Обработчик выбора предмета в списке."""
        selection = self.items_listbox.curselection()
        if not selection:
            return
        
        display_text = self.items_listbox.get(selection[0])
        item_id = display_text.split(" — ")[0].replace(" ⚠️", "")
        
        if item_id not in self.items_data:
            return
        
        self._load_item_to_form(item_id)
    
    # =========================================================================
    # ФОРМА: ЗАПОЛНЕНИЕ / ОЧИСТКА
    # =========================================================================
    
    def _clear_form(self):
        """Очищает форму (не переводит в режим создания!)."""
        self.current_editing_id = None
        self.current_generated_id = None
        
        # Очищаем поле суффикса
        if hasattr(self, 'suffix_var'):
            self.suffix_var.set("")
        
        # Сбрасываем ID label
        self.id_label.config(text="(выберите категорию)", foreground="gray")
        
        # Очищаем базовые поля
        self.base_fields["name"].set("")
        self.base_fields["weight"].set(0.0)
        self.base_fields["volume"].set(1)
        self.base_fields["cost"].set(0)
        self.base_fields["durability"].set(100)
        self.base_fields["equippable"].set(False)
        self.base_fields["gender_restrict"].set("any")
        
        for field_name, (widget, var, field_type) in self.field_widgets.items():
            if field_type == 'bool':
                var.set(False)
            elif field_type in ('int', 'float'):
                var.set(0)
            else:
                var.set("")
        
        self.status_var.set("Форма очищена.")
    
    def _new_item(self):
        """Переводит форму в режим создания нового предмета."""
        self.current_editing_id = None
        self._clear_form()
        self.items_listbox.selection_clear(0, tk.END)
        
        # Активируем поле суффикса
        self.suffix_entry.configure(state="normal")
        self.suffix_var.set("")
        
        # Генерируем ID (для текущей категории)
        self._update_generated_id()
        
        self.status_var.set("Режим создания нового предмета. Введите суффикс (опц.) и нажмите Сохранить.")
    
    def _load_item_to_form(self, item_id):
        """Загружает существующий предмет в форму для редактирования."""
        self.current_editing_id = item_id
        props = self.items_data[item_id]
        
        # Показываем существующий ID (не перегенерируем)
        self.current_generated_id = None
        self.id_label.config(text=item_id, foreground="gray")
        
        # Блокируем суффикс (нельзя менять ID существующего предмета)
        self.suffix_entry.configure(state="disabled")
        self.suffix_var.set("")
        
        # Базовые поля
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
            # Временно отключаем обработчик, чтобы не сработал _update_generated_id
            self.category_combobox.unbind("<<ComboboxSelected>>")
            self.category_combobox.set(category)
            self.category_combobox.bind("<<ComboboxSelected>>", self._on_category_changed)
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
                    var.set(str(value))
                elif field_type == 'list':
                    var.set(", ".join(value) if isinstance(value, list) else str(value))
                else:
                    var.set(str(value))
        
        self.status_var.set(f"Редактирование: {item_id}")
    
    # =========================================================================
    # СОХРАНЕНИЕ / УДАЛЕНИЕ
    # =========================================================================
    
    def _save_current_item(self):
        """Сохраняет текущий предмет в items.json."""
        category = self.category_var.get()
        name = self.base_fields["name"].get().strip()
        
        if not category:
            messagebox.showwarning("Ошибка валидации", "Выберите категорию.")
            return
        
        if not name:
            messagebox.showwarning("Ошибка валидации", "Поле 'Наименование' не может быть пустым.")
            return
        
        # --- ОПРЕДЕЛЯЕМ ID ---
        if self.current_editing_id:
            # Редактирование существующего — ID не меняется
            item_id = self.current_editing_id
        else:
            # Создание нового — берём сгенерированный ID
            if not self.current_generated_id:
                # На всякий случай перегенерируем
                self._update_generated_id()
            
            item_id = self.current_generated_id
            if not item_id:
                messagebox.showerror("Ошибка", "Не удалось сгенерировать ID.")
                return
            
            if item_id in self.items_data:
                messagebox.showerror(
                    "Конфликт ID",
                    f"Сгенерированный ID '{item_id}' уже существует.\n"
                    f"Попробуйте другой суффикс."
                )
                return
        
        # --- СОБИРАЕМ СЛОВАРЬ ПРЕДМЕТА ---
        item_dict = {
            "name": name,
            "category": category,
            "weight": round(float(self.base_fields["weight"].get()), 2),
            "volume": int(self.base_fields["volume"].get()),
            "cost": int(self.base_fields["cost"].get()),
            "durability": int(self.base_fields["durability"].get()),
            "equippable": bool(self.base_fields["equippable"].get()),
            "gender_restrict": self.base_fields["gender_restrict"].get(),
            "storage_type": STORAGE_MAP.get(category, "burden"),
        }
        
        # Добавляем динамические поля
        for field_name, (widget, var, field_type) in self.field_widgets.items():
            value = var.get()
            if field_type == 'list':
                if value.strip():
                    item_dict[field_name] = [v.strip() for v in value.split(",")]
                else:
                    item_dict[field_name] = []
            elif field_type == 'enum':
                item_dict[field_name] = str(value)
            else:
                item_dict[field_name] = value
        
        # Сохраняем
        self.items_data[item_id] = item_dict
        
        if self._save_items_json():
            self.status_var.set(f"✅ Предмет '{item_id}' успешно сохранён.")
            self.current_editing_id = item_id
            
            # Переключаемся в режим редактирования (ID серый, суффикс disabled)
            self.id_label.config(text=item_id, foreground="gray")
            self.suffix_entry.configure(state="disabled")
            
            # Обновляем список и выделяем сохранённый предмет
            self._populate_list()
            
            for i in range(self.items_listbox.size()):
                if self.items_listbox.get(i).startswith(item_id + " —"):
                    self.items_listbox.selection_clear(0, tk.END)
                    self.items_listbox.selection_set(i)
                    self.items_listbox.see(i)
                    break
    
    def _delete_item(self):
        """Удаляет выбранный предмет."""
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
                self._populate_list()


# ---------------------------------------------------------------------------
# ТОЧКА ВХОДА
# ---------------------------------------------------------------------------
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