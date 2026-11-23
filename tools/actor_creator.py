"""
ACTOR CREATOR — Утилита для создания и редактирования существ в игре Last Way
Графический интерфейс на tkinter для работы с data/actors.json.
Поддерживает два типа существ: NPC и Animal.
Автогенерация ID в реальном времени.
Динамические поля: patrol_points (для patrol), follow_target (для follow).

Запуск: python tools/actor_creator.py (из корня проекта)
"""
import sys
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox

# ---------------------------------------------------------------------------
# НАСТРОЙКА ПУТЕЙ (ОБЯЗАТЕЛЬНО ПЕРЕД ИМПОРТАМИ!)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# КОНСТАНТЫ
# ---------------------------------------------------------------------------
ACTORS_JSON_PATH = os.path.join(PROJECT_ROOT, "data", "actors.json")

ACTOR_TYPES = {
    "npc": "npc",
    "animal": "ani",
}

VALID_GENDERS = ["male", "female"]
VALID_MOVEMENTS = ["stationary", "patrol", "follow"]
VALID_SPECIES = ["cat", "dog", "rat"]
VALID_BEHAVIORS = ["emergent_needs", "wander"]


# ---------------------------------------------------------------------------
# ГЕНЕРАТОР ID СУЩЕСТВА
# ---------------------------------------------------------------------------
def generate_actor_id(actor_type: str, actors_data: dict, custom_suffix: str = "") -> str:
    """
    Генерирует ID вида: id_act_{prefix}_{NNN}[_suffix]
    
    Пример:
        actor_type="npc",    custom_suffix="gomes" → id_act_npc_001_gomes
        actor_type="animal", custom_suffix="cat"   → id_act_ani_002_cat
    """
    prefix = ACTOR_TYPES.get(actor_type, "act")
    
    max_num = 0
    search_str = f"id_act_{prefix}_"
    for act_id in actors_data.keys():
        if act_id.startswith(search_str):
            parts = act_id.split("_")
            if len(parts) >= 4:
                try:
                    num = int(parts[3])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
    
    new_id = f"id_act_{prefix}_{max_num + 1:03d}"
    
    if custom_suffix:
        suffix = custom_suffix.strip().replace(" ", "_").lower()
        suffix = ''.join(c for c in suffix if c.isalnum() or c in "_-")
        if suffix:
            new_id += f"_{suffix}"
    
    return new_id


# ---------------------------------------------------------------------------
# ГЛАВНОЕ ПРИЛОЖЕНИЕ
# ---------------------------------------------------------------------------
class ActorCreatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Last Way — Actor Creator")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        
        # Загружаем данные
        self.actors_data = {}
        self._load_actors_json()
        
        self.current_editing_id = None
        self.current_generated_id = None
        self.field_widgets = {}
        
        # FIX: флаги защиты от рекурсии (ДО _build_ui!)
        self._is_rebuilding = False
        self._movement_trace_id = None
        
        self._build_ui()
        self._populate_list()
    
    # =========================================================================
    # ЗАГРУЗКА / СОХРАНЕНИЕ JSON
    # =========================================================================
    
    def _load_actors_json(self):
        if not os.path.exists(ACTORS_JSON_PATH):
            self.actors_data = {}
            return
        try:
            with open(ACTORS_JSON_PATH, "r", encoding="utf-8") as f:
                self.actors_data = json.load(f)
        except Exception as e:
            messagebox.showerror("Ошибка чтения",
                                 f"Не удалось прочитать actors.json:\n{e}")
            self.actors_data = {}
    
    def _save_actors_json(self):
        try:
            with open(ACTORS_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(self.actors_data, f, ensure_ascii=False,
                          indent=2, sort_keys=True)
            return True
        except Exception as e:
            messagebox.showerror("Ошибка записи",
                                 f"Не удалось сохранить actors.json:\n{e}")
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
        
        ttk.Label(left_frame, text="Существующие существа",
                  font=("Arial", 11, "bold")).pack(pady=(0, 5))
        
        # Фильтр
        filter_frame = ttk.Frame(left_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(filter_frame, text="Фильтр:", font=("Arial", 9)).pack(
            side=tk.LEFT, padx=(0, 5))
        
        self.filter_var = tk.StringVar(value="Все")
        self.filter_combo = ttk.Combobox(
            filter_frame, textvariable=self.filter_var,
            values=["Все"] + list(ACTOR_TYPES.keys()),
            state="readonly", width=15
        )
        self.filter_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.filter_combo.bind("<<ComboboxSelected>>",
                               lambda e: self._populate_list())
        
        # Поиск
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._populate_list())
        search_entry = ttk.Entry(left_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(left_frame, text="(поиск по ID и имени)",
                  font=("Arial", 8)).pack()
        
        # Список
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.actors_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            selectmode=tk.SINGLE
        )
        self.actors_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.actors_listbox.yview)
        self.actors_listbox.bind("<<ListboxSelect>>", self._on_actor_selected)
        
        # Кнопки
        ttk.Button(left_frame, text="➕ Новое существо",
                   command=self._new_actor).pack(fill=tk.X, pady=2)
        ttk.Button(left_frame, text="🗑 Удалить выбранное",
                   command=self._delete_actor).pack(fill=tk.X, pady=2)
        
        # --- ПРАВАЯ ПАНЕЛЬ ---
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)
        
        ttk.Label(right_frame, text="Параметры существа",
                  font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # Выбор типа
        type_frame = ttk.Frame(right_frame)
        type_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(type_frame, text="Тип существа:",
                  font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        
        self.actor_type_var = tk.StringVar(value="npc")
        type_values = list(ACTOR_TYPES.keys())
        self.type_combobox = ttk.Combobox(
            type_frame, textvariable=self.actor_type_var,
            values=type_values, state="readonly", width=20
        )
        self.type_combobox.pack(side=tk.LEFT, padx=5)
        self.type_combobox.bind("<<ComboboxSelected>>", self._on_type_changed)
        
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
        
        ttk.Button(buttons_frame, text="💾 Сохранить в actors.json",
                   command=self._save_current_actor).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="🔄 Очистить форму",
                   command=self._clear_form).pack(side=tk.LEFT, padx=5)
        
        # Статус
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(self.root, textvariable=self.status_var,
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Генерируем поля для начального типа
        self._on_type_changed(None)
    
    def _build_base_fields(self):
        """Создаёт базовые поля (ID, суффикс, общие поля)."""
        self.base_fields = {}
        row = 0
        parent = self.base_fields_frame
        
        # ------------------------------------------------------------------
        # ID (Label с копированием по двойному клику)
        # ------------------------------------------------------------------
        ttk.Label(parent, text="ID (автогенерация):",
                  font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=5, pady=5)
        
        self.id_label = ttk.Label(
            parent, text="(выберите тип)",
            font=("Consolas", 10, "bold"),
            foreground="blue",
            cursor="hand2"  # Курсор-рука при наведении
        )
        self.id_label.grid(row=row, column=1, sticky="w", padx=5, pady=5)
        # Привязываем двойной клик для копирования
        self.id_label.bind("<Double-Button-1>", self._copy_id_to_clipboard)
        
        # Подсказка
        ttk.Label(parent, text="(двойной клик для копирования)",
                  font=("Arial", 8), foreground="gray").grid(
            row=row, column=2, sticky="w", padx=5)
        row += 1
        
        # ------------------------------------------------------------------
        # Суффикс ID
        # ------------------------------------------------------------------
        ttk.Label(parent, text="Суффикс ID (опц.):",
                  font=("Arial", 9)).grid(
            row=row, column=0, sticky="w", padx=5, pady=3)
        self.suffix_var = tk.StringVar()
        self.suffix_entry = ttk.Entry(parent, textvariable=self.suffix_var, width=40)
        self.suffix_entry.grid(row=row, column=1, sticky="ew", padx=5, pady=3)
        self.suffix_var.trace_add("write", lambda *args: self._update_generated_id())
        ttk.Label(parent, text="(например: gomes, cat_black)",
                  font=("Arial", 8), foreground="gray").grid(
            row=row, column=2, sticky="w", padx=5)
        row += 1
        
        # Разделитель
        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=10)
        row += 1
        
        # ------------------------------------------------------------------
        # Общие поля
        # ------------------------------------------------------------------
        ttk.Label(parent, text="Имя *:",
                  font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=5, pady=5)
        self.base_fields["name"] = tk.StringVar()
        ttk.Entry(parent, textvariable=self.base_fields["name"],
                  width=40).grid(row=row, column=1, sticky="ew", padx=5, pady=5)
        row += 1
        
        ttk.Label(parent, text="Пол *:",
                  font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=5, pady=5)
        self.base_fields["gender"] = tk.StringVar(value="male")
        ttk.Combobox(parent, textvariable=self.base_fields["gender"],
                     values=VALID_GENDERS, state="readonly", width=37).grid(
            row=row, column=1, sticky="ew", padx=5, pady=5)
        row += 1
        
        parent.columnconfigure(1, weight=1)
    
    # =========================================================================
    # КОПИРОВАНИЕ ID
    # =========================================================================
    
    def _copy_id_to_clipboard(self, event=None):
        """
        Копирует текущий ID в буфер обмена (двойной клик по ID-метке).
        """
        if self.current_editing_id:
            id_to_copy = self.current_editing_id
        elif self.current_generated_id:
            id_to_copy = self.current_generated_id
        else:
            return
        
        self.root.clipboard_clear()
        self.root.clipboard_append(id_to_copy)
        self.status_var.set(f"📋 ID скопирован в буфер: {id_to_copy}")
    
    # =========================================================================
    # АВТОГЕНЕРАЦИЯ ID
    # =========================================================================
    
    def _update_generated_id(self):
        """Пересчитывает и отображает сгенерированный ID."""
        if self.current_editing_id is not None:
            return
        
        actor_type = self.actor_type_var.get()
        suffix = self.suffix_var.get().strip() if hasattr(self, 'suffix_var') else ""
        
        if not actor_type:
            self.id_label.config(text="(выберите тип)", foreground="gray")
            self.current_generated_id = None
            return
        
        new_id = generate_actor_id(actor_type, self.actors_data, suffix)
        self.current_generated_id = new_id
        
        if new_id in self.actors_data:
            self.id_label.config(text=new_id + " ⚠️ КОНФЛИКТ!", foreground="red")
        else:
            self.id_label.config(text=new_id, foreground="blue")
    
    # =========================================================================
    # ДИНАМИЧЕСКИЕ ПОЛЯ
    # =========================================================================
    
    def _on_type_changed(self, event):
        """Обработчик смены типа существа."""
        actor_type = self.actor_type_var.get()
        if not actor_type:
            return
        self._rebuild_dynamic_fields()
        self._update_generated_id()
    
    def _on_movement_changed(self, event=None):
        """Обработчик смены поведения NPC."""
        if self._is_rebuilding:
            return
        self._rebuild_dynamic_fields(preserve_values=True)
    
    def _rebuild_dynamic_fields(self, preserve_values=False):
        """Перестраивает динамические поля на основе текущего типа и поведения."""
        if self._is_rebuilding:
            return
        self._is_rebuilding = True
        
        try:
            # 1. Сохраняем текущие значения (безопасно, через try/except)
            old_values = {}
            if preserve_values:
                for fname, (widget, var, ftype) in list(self.field_widgets.items()):
                    try:
                        if ftype == "textarea":
                            old_values[fname] = widget.get("1.0", tk.END).strip()
                        else:
                            old_values[fname] = var.get()
                    except Exception:
                        pass  # Виджет уже уничтожен, пропускаем
            
            # 2. Удаляем старый trace для movement (если он был)
            if self._movement_trace_id is not None:
                if "movement" in self.field_widgets:
                    old_movement_var = self.field_widgets["movement"][1]
                    try:
                        old_movement_var.trace_remove("write", self._movement_trace_id)
                    except Exception:
                        pass
                self._movement_trace_id = None
            
            # 3. Очищаем старые поля
            for widget in self.dynamic_fields_frame.winfo_children():
                widget.destroy()
            self.field_widgets.clear()
            
            actor_type = self.actor_type_var.get()
            if not actor_type:
                return
            
            ttk.Separator(self.dynamic_fields_frame, orient=tk.HORIZONTAL).pack(
                fill=tk.X, padx=5, pady=10)
            ttk.Label(self.dynamic_fields_frame,
                      text=f"Специфичные поля для типа '{actor_type}':",
                      font=("Arial", 10, "bold")).pack(anchor="w", padx=5, pady=5)
            
            grid_frame = ttk.Frame(self.dynamic_fields_frame)
            grid_frame.pack(fill=tk.BOTH, expand=True)
            
            # Определяем список полей для текущего типа
            if actor_type == "npc":
                fields = [
                    ("dialog_id", "ID диалога", "str", "", None),
                    ("movement", "Поведение", "enum", "stationary", VALID_MOVEMENTS),
                    ("move_delay_ms", "Задержка движения (мс)", "int", 500, None),
                ]
            elif actor_type == "animal":
                fields = [
                    ("species", "Вид", "enum", "cat", VALID_SPECIES),
                    ("behavior_type", "Тип поведения", "enum",
                     "emergent_needs", VALID_BEHAVIORS),
                    ("food_pos", "Точка еды (x,y)", "coords", "", None),
                    ("bed_pos", "Точка сна (x,y)", "coords", "", None),
                    ("toy_pos", "Точка игры (x,y)", "coords", "", None),
                ]
            else:
                fields = []
            
            row = 0
            for field_info in fields:
                self._create_field_widget(grid_frame, row, field_info, old_values)
                row += 1
            
            # Условные поля для NPC в зависимости от movement
            if actor_type == "npc":
                movement_var = None
                for fname, (widget, var, ftype) in self.field_widgets.items():
                    if fname == "movement":
                        movement_var = var
                        break
                
                if movement_var:
                    movement = movement_var.get()
                    
                    # Привязываем новый trace и сохраняем его ID
                    self._movement_trace_id = movement_var.trace_add(
                        "write", lambda *args: self._on_movement_changed()
                    )
                    
                    # Условные поля
                    if movement == "patrol":
                        patrol_info = ("patrol_points", "Точки патруля",
                                       "textarea", "", None)
                        self._create_field_widget(grid_frame, row, patrol_info,
                                                  old_values)
                        row += 1
                    elif movement == "follow":
                        follow_info = ("follow_target",
                                       "Цель следования (ID)",
                                       "str", "", None)
                        self._create_field_widget(grid_frame, row, follow_info,
                                                  old_values)
                        row += 1
            
            grid_frame.columnconfigure(1, weight=1)
        finally:
            self._is_rebuilding = False
    
    def _create_field_widget(self, parent, row, field_info, old_values=None):
        """Создаёт один виджет поля."""
        fname, flabel, ftype, fdefault, foptions = field_info
        
        value = fdefault
        if old_values and fname in old_values:
            value = old_values[fname]
        
        ttk.Label(parent, text=flabel + ":").grid(
            row=row, column=0, sticky="w", padx=5, pady=3)
        
        if ftype == "enum":
            var = tk.StringVar(value=value if value in foptions else foptions[0])
            widget = ttk.Combobox(parent, textvariable=var,
                                  values=foptions, state="readonly", width=37)
        elif ftype == "int":
            var = tk.IntVar(value=int(value) if value else 0)
            widget = ttk.Spinbox(parent, textvariable=var,
                                 from_=0, to=10000, increment=50, width=37)
        elif ftype == "coords":
            var = tk.StringVar()
            if isinstance(value, (list, tuple)) and len(value) == 2:
                var.set(f"{value[0]},{value[1]}")
            elif isinstance(value, str):
                var.set(value)
            else:
                var.set("")
            widget = ttk.Entry(parent, textvariable=var, width=40)
            ttk.Label(parent, text="(формат: x,y или пусто)",
                      font=("Arial", 8), foreground="gray").grid(
                row=row, column=2, sticky="w", padx=5)
        elif ftype == "textarea":
            var = tk.StringVar()
            widget = tk.Text(parent, width=40, height=6)
            if isinstance(value, list):
                lines = []
                for pt in value:
                    if isinstance(pt, (list, tuple)) and len(pt) == 2:
                        lines.append(f"{pt[0]},{pt[1]}")
                widget.insert("1.0", "\n".join(lines))
            elif isinstance(value, str) and value:
                widget.insert("1.0", value)
            widget.grid(row=row, column=1, sticky="ew", padx=5, pady=3)
            ttk.Label(parent, text="(каждая точка с новой строки: x,y)",
                      font=("Arial", 8), foreground="gray").grid(
                row=row + 1, column=1, sticky="w", padx=5)
            self.field_widgets[fname] = (widget, var, ftype)
            return
        else:  # str
            var = tk.StringVar(value=str(value) if value is not None else "")
            widget = ttk.Entry(parent, textvariable=var, width=40)
        
        widget.grid(row=row, column=1, sticky="ew", padx=5, pady=3)
        self.field_widgets[fname] = (widget, var, ftype)
    
    # =========================================================================
    # СПИСОК СУЩЕСТВ
    # =========================================================================
    
    def _populate_list(self):
        """Заполняет список с учётом фильтра и поиска."""
        self.actors_listbox.delete(0, tk.END)
        
        search_term = self.search_var.get().lower().strip()
        filter_type = self.filter_var.get()
        
        sorted_ids = sorted(self.actors_data.keys())
        
        for actor_id in sorted_ids:
            data = self.actors_data[actor_id]
            name = data.get("name", actor_id)
            
            if actor_id.startswith("id_act_npc_"):
                actor_type = "npc"
            elif actor_id.startswith("id_act_ani_"):
                actor_type = "animal"
            else:
                actor_type = "unknown"
            
            if filter_type != "Все" and actor_type != filter_type:
                continue
            
            if search_term:
                if (search_term not in actor_id.lower()
                        and search_term not in name.lower()):
                    continue
            
            type_marker = f"[{actor_type.upper()}]"
            display_text = f"{actor_id} — {name} {type_marker}"
            self.actors_listbox.insert(tk.END, display_text)
    
    def _on_actor_selected(self, event):
        """Обработчик выбора существа в списке."""
        selection = self.actors_listbox.curselection()
        if not selection:
            return
        
        display_text = self.actors_listbox.get(selection[0])
        actor_id = display_text.split(" — ")[0]
        
        if actor_id not in self.actors_data:
            return
        
        self._load_actor_to_form(actor_id)
    
    # =========================================================================
    # ФОРМА: ЗАПОЛНЕНИЕ / ОЧИСТКА
    # =========================================================================
    
    def _clear_form(self):
        """Очищает форму."""
        self.current_editing_id = None
        self.current_generated_id = None
        
        if hasattr(self, 'suffix_var'):
            self.suffix_var.set("")
        
        self.id_label.config(text="(выберите тип)", foreground="gray")
        
        if hasattr(self, 'base_fields'):
            self.base_fields["name"].set("")
            self.base_fields["gender"].set("male")
        
        for field_name, (widget, var, field_type) in list(self.field_widgets.items()):
            if field_type == "textarea":
                widget.delete("1.0", tk.END)
            elif field_type == "int":
                var.set(0)
            else:
                var.set("")
        
        self.status_var.set("Форма очищена.")
    
    def _new_actor(self):
        """Режим создания нового существа."""
        self.current_editing_id = None
        self._clear_form()
        self.actors_listbox.selection_clear(0, tk.END)
        
        self.suffix_entry.configure(state="normal")
        self.suffix_var.set("")
        
        self._update_generated_id()
        
        self.status_var.set(
            "Режим создания нового существа. "
            "Выберите тип, введите суффикс (опц.) и нажмите Сохранить."
        )
    
    def _load_actor_to_form(self, actor_id):
        """Загружает существующее существо в форму для редактирования."""
        self.current_editing_id = actor_id
        data = self.actors_data[actor_id]
        
        # Определяем тип по ID
        if actor_id.startswith("id_act_npc_"):
            actor_type = "npc"
        elif actor_id.startswith("id_act_ani_"):
            actor_type = "animal"
        else:
            actor_type = "npc"
        
        # Показываем существующий ID
        self.current_generated_id = None
        self.id_label.config(text=actor_id, foreground="gray")
        
        # Блокируем суффикс
        self.suffix_entry.configure(state="disabled")
        self.suffix_var.set("")
        
        # Устанавливаем тип (временно отключаем обработчик)
        self.type_combobox.unbind("<<ComboboxSelected>>")
        self.actor_type_var.set(actor_type)
        self.type_combobox.bind("<<ComboboxSelected>>", self._on_type_changed)
        
        # Базовые поля
        self.base_fields["name"].set(data.get("name", ""))
        self.base_fields["gender"].set(data.get("gender", "male"))
        
        # Перестраиваем динамические поля под тип (создаёт базовые поля)
        self._rebuild_dynamic_fields()
        
        # =====================================================================
        # БЕЗОПАСНАЯ УСТАНОВКА ЗНАЧЕНИЙ
        # Блокируем _is_rebuilding, чтобы trace_add на movement не вызвал
        # _on_movement_changed и не уничтожил виджеты во время итерации.
        # =====================================================================
        self._is_rebuilding = True
        try:
            for field_name in list(self.field_widgets.keys()):
                if field_name not in self.field_widgets:
                    continue
                widget, var, field_type = self.field_widgets[field_name]
                value = data.get(field_name)
                if value is not None:
                    try:
                        if field_type == "textarea":
                            if isinstance(value, list):
                                lines = []
                                for pt in value:
                                    if isinstance(pt, (list, tuple)) and len(pt) == 2:
                                        lines.append(f"{pt[0]},{pt[1]}")
                                widget.delete("1.0", tk.END)
                                widget.insert("1.0", "\n".join(lines))
                        elif field_type == "coords":
                            if isinstance(value, (list, tuple)) and len(value) == 2:
                                var.set(f"{value[0]},{value[1]}")
                            else:
                                var.set("")
                        elif field_type == "int":
                            var.set(int(value))
                        else:
                            var.set(str(value))
                    except Exception:
                        pass  # Игнорируем ошибки установки значений
        finally:
            self._is_rebuilding = False
        
        # Теперь, когда movement установлено, перестраиваем поля,
        # чтобы появились условные поля (patrol_points или follow_target)
        self._rebuild_dynamic_fields(preserve_values=True)
        
        # И ещё раз заполняем значения (для новых условных полей)
        self._is_rebuilding = True
        try:
            for field_name in list(self.field_widgets.keys()):
                if field_name not in self.field_widgets:
                    continue
                widget, var, field_type = self.field_widgets[field_name]
                value = data.get(field_name)
                if value is not None:
                    try:
                        if field_type == "textarea":
                            if isinstance(value, list):
                                lines = []
                                for pt in value:
                                    if isinstance(pt, (list, tuple)) and len(pt) == 2:
                                        lines.append(f"{pt[0]},{pt[1]}")
                                widget.delete("1.0", tk.END)
                                widget.insert("1.0", "\n".join(lines))
                        elif field_type == "coords":
                            if isinstance(value, (list, tuple)) and len(value) == 2:
                                var.set(f"{value[0]},{value[1]}")
                            else:
                                var.set("")
                        elif field_type == "int":
                            var.set(int(value))
                        else:
                            var.set(str(value))
                    except Exception:
                        pass
        finally:
            self._is_rebuilding = False
        
        self.status_var.set(f"Редактирование: {actor_id}")

    # =========================================================================
    # СОЗДАНИЕ / УДАЛЕНИЕ / СОХРАНЕНИЕ
    # =========================================================================
    
    def _save_current_actor(self):
        """Сохраняет текущее существо в actors.json."""
        actor_type = self.actor_type_var.get()
        if not actor_type:
            messagebox.showwarning("Ошибка", "Выберите тип существа.")
            return
        
        name = self.base_fields["name"].get().strip()
        if not name:
            messagebox.showwarning("Ошибка валидации",
                                   "Поле 'Имя' не может быть пустым.")
            return
        
        # Определяем ID
        if self.current_editing_id:
            actor_id = self.current_editing_id
        else:
            if not self.current_generated_id:
                self._update_generated_id()
            
            actor_id = self.current_generated_id
            if not actor_id:
                messagebox.showerror("Ошибка", "Не удалось сгенерировать ID.")
                return
            
            if actor_id in self.actors_data:
                messagebox.showerror(
                    "Конфликт ID",
                    f"Сгенерированный ID '{actor_id}' уже существует."
                )
                return
        
        # Собираем данные
        data = {
            "name": name,
            "gender": self.base_fields["gender"].get(),
        }
        
        for field_name, (widget, var, field_type) in self.field_widgets.items():
            if field_type == "textarea":
                text = widget.get("1.0", tk.END).strip()
                points = []
                for line in text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",")
                    if len(parts) == 2:
                        try:
                            x, y = int(parts[0].strip()), int(parts[1].strip())
                            points.append([x, y])
                        except ValueError:
                            messagebox.showwarning(
                                "Ошибка формата",
                                f"Неверный формат точки: '{line}'\n"
                                f"Ожидается: x,y"
                            )
                            return
                data[field_name] = points
            elif field_type == "coords":
                text = var.get().strip()
                if not text:
                    data[field_name] = None
                else:
                    parts = text.split(",")
                    if len(parts) == 2:
                        try:
                            x, y = int(parts[0].strip()), int(parts[1].strip())
                            data[field_name] = [x, y]
                        except ValueError:
                            messagebox.showwarning(
                                "Ошибка формата",
                                f"Неверный формат координат: '{text}'"
                            )
                            return
                    else:
                        messagebox.showwarning(
                            "Ошибка формата",
                            f"Неверный формат координат: '{text}'"
                        )
                        return
            elif field_type == "int":
                data[field_name] = int(var.get())
            else:
                data[field_name] = str(var.get())
        
        # Сохраняем
        self.actors_data[actor_id] = data
        
        if self._save_actors_json():
            self.status_var.set(f"✅ Существо '{actor_id}' успешно сохранено.")
            self.current_editing_id = actor_id
            
            self.id_label.config(text=actor_id, foreground="gray")
            self.suffix_entry.configure(state="disabled")
            
            self._populate_list()
            
            for i in range(self.actors_listbox.size()):
                if self.actors_listbox.get(i).startswith(actor_id + " —"):
                    self.actors_listbox.selection_clear(0, tk.END)
                    self.actors_listbox.selection_set(i)
                    self.actors_listbox.see(i)
                    break
    
    def _delete_actor(self):
        """Удаляет выбранное существо."""
        selection = self.actors_listbox.curselection()
        if not selection:
            messagebox.showinfo("Нет выбора", "Выберите существо для удаления.")
            return
        
        display_text = self.actors_listbox.get(selection[0])
        actor_id = display_text.split(" — ")[0]
        
        if not messagebox.askyesno(
            "Подтверждение удаления",
            f"Удалить существо '{actor_id}' из actors.json?\n\n"
            f"ВНИМАНИЕ: ссылки на этого NPC в location.json НЕ будут "
            f"автоматически удалены!"
        ):
            return
        
        if actor_id in self.actors_data:
            del self.actors_data[actor_id]
            if self._save_actors_json():
                self.status_var.set(f"🗑 Существо '{actor_id}' удалено.")
                self._new_actor()
                self._populate_list()
    
    # =========================================================================
    # ЗАПУСК
    # =========================================================================
    
    def run(self):
        self.root.mainloop()


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
    
    app = ActorCreatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()