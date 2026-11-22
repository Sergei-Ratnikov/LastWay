# tools/actor_creator.py
# =============================================================================
# ACTOR CREATOR — УТИЛИТА ДЛЯ СОЗДАНИЯ NPC
# Позволяет создавать, редактировать и удалять NPC в локациях.
# Сканирует data/locations/*/npcs/*.json
# =============================================================================

import sys
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path

# ---------------------------------------------------------------------------
# НАСТРОЙКА ПУТЕЙ (ДО ИМПОРТОВ ИЗ ПРОЕКТА!)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LOCATIONS_DIR = os.path.join(DATA_DIR, "locations")
REGISTRY_PATH = os.path.join(LOCATIONS_DIR, "registry.json")

# ---------------------------------------------------------------------------
# КОНСТАНТЫ UI
# ---------------------------------------------------------------------------
VALID_GENDERS = ["male", "female", "any"]
VALID_MOVEMENTS = ["stationary", "patrol"]


class ActorCreator:
    """Главный класс утилиты."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Actor Creator — Last Way")
        self.root.geometry("1000x700")
        
        # Данные
        self.locations = self._load_locations()
        self.current_location = None
        self.npc_list = []  # Список NPC текущей локации
        self.current_npc_file = None
        self.field_widgets = {}
        
        # Создаём UI
        self._build_ui()
        self._populate_locations()
    
    # =========================================================================
    # ЗАГРУЗКА ДАННЫХ
    # =========================================================================
    
    def _load_locations(self) -> list:
        """Загружает список локаций из registry.json."""
        if not os.path.exists(REGISTRY_PATH):
            messagebox.showerror("Ошибка", f"Файл не найден: {REGISTRY_PATH}")
            return []
        
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("locations", [])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать registry.json: {e}")
            return []
    
    def _get_location_path(self, location_id: str) -> str:
        """Возвращает путь к папке локации."""
        for loc in self.locations:
            if loc.get("id") == location_id:
                return os.path.join(LOCATIONS_DIR, loc.get("dir", location_id))
        return os.path.join(LOCATIONS_DIR, location_id)
    
    def _load_npcs_for_location(self, location_id: str):
        """Загружает список NPC для выбранной локации."""
        location_path = self._get_location_path(location_id)
        npcs_dir = os.path.join(location_path, "npcs")
        
        self.npc_list = []
        if not os.path.isdir(npcs_dir):
            return
        
        for filename in sorted(os.listdir(npcs_dir)):
            if filename.endswith(".json"):
                npc_id = filename[:-5]
                filepath = os.path.join(npcs_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.npc_list.append({
                        "id": npc_id,
                        "name": data.get("name", "Безымянный"),
                        "filepath": filepath,
                    })
                except Exception as e:
                    print(f"Предупреждение: не удалось прочитать {filename}: {e}")
    
    def _get_dialog_files(self, location_id: str) -> list:
        """Возвращает список ID диалогов для локации."""
        location_path = self._get_location_path(location_id)
        dialogs_dir = os.path.join(location_path, "dialogs")
        
        dialog_ids = []
        if os.path.isdir(dialogs_dir):
            for filename in sorted(os.listdir(dialogs_dir)):
                if filename.endswith(".json"):
                    dialog_ids.append(filename[:-5])
        return dialog_ids
    
    # =========================================================================
    # ПОСТРОЕНИЕ UI
    # =========================================================================
    
    def _build_ui(self):
        """Создаёт главный интерфейс."""
        # Главный контейнер
        main_paned = ttk.PanedWindow(self.root, orient="horizontal")
        main_paned.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- ЛЕВАЯ ПАНЕЛЬ: локации и NPC ---
        left_frame = ttk.Frame(main_paned, width=300)
        main_paned.add(left_frame, weight=1)
        
        # Выбор локации
        ttk.Label(left_frame, text="Локация:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        self.location_var = tk.StringVar()
        self.location_combo = ttk.Combobox(
            left_frame, textvariable=self.location_var, state="readonly", width=30
        )
        self.location_combo.pack(fill="x", pady=(0, 10))
        self.location_combo.bind("<<ComboboxSelected>>", self._on_location_changed)
        
        # Кнопки управления NPC
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(btn_frame, text="Новый NPC", command=self._on_new_npc).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self._on_delete_npc).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Обновить", command=self._on_refresh).pack(side="left", padx=2)
        
        # Список NPC
        ttk.Label(left_frame, text="Список NPC:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10, 5))
        self.npc_listbox = tk.Listbox(left_frame, height=25)
        self.npc_listbox.pack(fill="both", expand=True)
        self.npc_listbox.bind("<<ListboxSelect>>", self._on_npc_selected)
        
        # --- ПРАВАЯ ПАНЕЛЬ: форма редактирования ---
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)
        
        ttk.Label(right_frame, text="Редактирование NPC", 
                  font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        # Прокручиваемая форма
        canvas_frame = ttk.Frame(right_frame)
        canvas_frame.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.form_frame = ttk.Frame(canvas)
        
        self.form_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.form_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Кнопки сохранения
        bottom_frame = ttk.Frame(right_frame)
        bottom_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(bottom_frame, text="💾 Сохранить", command=self._save_current_npc).pack(side="right", padx=5)
        ttk.Button(bottom_frame, text="Очистить форму", command=self._clear_form).pack(side="right", padx=5)
    
    def _populate_locations(self):
        """Заполняет список локаций."""
        location_names = [f"{loc['id']} — {loc.get('name', '')}" for loc in self.locations]
        self.location_combo["values"] = location_names
        if location_names:
            self.location_combo.current(0)
            self._on_location_changed(None)
    
    def _populate_npc_list(self):
        """Обновляет список NPC в listbox."""
        self.npc_listbox.delete(0, "end")
        for npc in self.npc_list:
            self.npc_listbox.insert("end", f"{npc['id']} — {npc['name']}")
    
    # =========================================================================
    # ОБРАБОТЧИКИ СОБЫТИЙ
    # =========================================================================
    
    def _on_location_changed(self, event):
        """При смене локации загружаем её NPC."""
        selection = self.location_combo.current()
        if selection < 0:
            return
        
        loc = self.locations[selection]
        self.current_location = loc["id"]
        self._load_npcs_for_location(self.current_location)
        self._populate_npc_list()
        self._clear_form()
    
    def _on_npc_selected(self, event):
        """При выборе NPC в списке загружаем его в форму."""
        selection = self.npc_listbox.curselection()
        if not selection:
            return
        
        npc_info = self.npc_list[selection[0]]
        self._load_npc_to_form(npc_info["filepath"])
    
    def _on_new_npc(self):
        """Создание нового NPC."""
        if not self.current_location:
            messagebox.showwarning("Внимание", "Сначала выберите локацию")
            return
        
        npc_id = simpledialog.askstring("Новый NPC", "Введите ID (например, 001_004):")
        if not npc_id:
            return
        
        # Проверяем уникальность
        location_path = self._get_location_path(self.current_location)
        npcs_dir = os.path.join(location_path, "npcs")
        filepath = os.path.join(npcs_dir, f"{npc_id}.json")
        
        if os.path.exists(filepath):
            messagebox.showerror("Ошибка", f"NPC с ID '{npc_id}' уже существует")
            return
        
        # Создаём папку npcs, если её нет
        os.makedirs(npcs_dir, exist_ok=True)
        
        # Создаём пустой шаблон
        template = {
            "name": "Новый NPC",
            "gender": "male",
            "dialog_id": "",
            "movement": "stationary",
            "patrol_points": [],
            "move_delay_ms": 500,
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        
        # Перезагружаем список и выбираем новый NPC
        self._load_npcs_for_location(self.current_location)
        self._populate_npc_list()
        
        # Находим и выбираем новый NPC в списке
        for i, npc in enumerate(self.npc_list):
            if npc["id"] == npc_id:
                self.npc_listbox.selection_clear(0, "end")
                self.npc_listbox.selection_set(i)
                self.npc_listbox.see(i)
                self._load_npc_to_form(filepath)
                break
    
    def _on_delete_npc(self):
        """Удаление выбранного NPC."""
        selection = self.npc_listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите NPC для удаления")
            return
        
        npc_info = self.npc_list[selection[0]]
        if not messagebox.askyesno("Подтверждение", 
                                     f"Удалить NPC '{npc_info['id']}'?"):
            return
        
        try:
            os.remove(npc_info["filepath"])
            self._load_npcs_for_location(self.current_location)
            self._populate_npc_list()
            self._clear_form()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось удалить: {e}")
    
    def _on_refresh(self):
        """Обновить список NPC."""
        if self.current_location:
            self._load_npcs_for_location(self.current_location)
            self._populate_npc_list()
    
    # =========================================================================
    # ЗАГРУЗКА / СОХРАНЕНИЕ ФОРМЫ
    # =========================================================================
    
    def _clear_form(self):
        """Очищает форму редактирования."""
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.field_widgets = {}
        self.current_npc_file = None
    
    def _load_npc_to_form(self, filepath: str):
        """Загружает данные NPC в форму."""
        self._clear_form()
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {e}")
            return
        
        self.current_npc_file = filepath
        npc_id = Path(filepath).stem
        
        # Получаем список диалогов для валидации
        dialog_ids = self._get_dialog_files(self.current_location)
        
        # --- СОЗДАЁМ ПОЛЯ ФОРМЫ ---
        row = 0
        
        # ID (только для чтения)
        ttk.Label(self.form_frame, text="ID:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, sticky="w", padx=5, pady=3)
        id_label = ttk.Label(self.form_frame, text=npc_id, foreground="gray")
        id_label.grid(row=row, column=1, sticky="w", padx=5, pady=3)
        row += 1
        
        # Разделитель
        ttk.Separator(self.form_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1
        
        # --- БАЗОВЫЕ ПОЛЯ ---
        fields = [
            ("name", "Имя *", "str", data.get("name", "Безымянный")),
            ("gender", "Пол *", "enum", data.get("gender", "male"), VALID_GENDERS),
            ("dialog_id", "ID диалога *", "dialog", data.get("dialog_id", ""), dialog_ids),
            ("movement", "Поведение", "enum", data.get("movement", "stationary"), VALID_MOVEMENTS),
            ("move_delay_ms", "Задержка движения (мс)", "int", data.get("move_delay_ms", 500)),
        ]
        
        for field_info in fields:
            field_name = field_info[0]
            label_text = field_info[1]
            field_type = field_info[2]
            default = field_info[3]
            
            ttk.Label(self.form_frame, text=label_text + ":").grid(
                row=row, column=0, sticky="w", padx=5, pady=3)
            
            if field_type == "enum":
                values = field_info[4]
                var = tk.StringVar(value=default if default in values else values[0])
                widget = ttk.Combobox(self.form_frame, textvariable=var,
                                      values=values, state="readonly", width=30)
            elif field_type == "dialog":
                dialog_list = field_info[4]
                var = tk.StringVar(value=default)
                widget = ttk.Combobox(self.form_frame, textvariable=var,
                                      values=dialog_list, width=30)
                # Разрешаем вводить произвольное значение
                widget.config(state="normal")
            elif field_type == "int":
                var = tk.IntVar(value=default if default is not None else 0)
                widget = ttk.Spinbox(self.form_frame, textvariable=var,
                                    from_=0, to=10000, increment=100, width=30)
            else:  # str
                var = tk.StringVar(value=default if default is not None else "")
                widget = ttk.Entry(self.form_frame, textvariable=var, width=33)
            
            widget.grid(row=row, column=1, sticky="ew", padx=5, pady=3)
            self.field_widgets[field_name] = (widget, var, field_type)
            row += 1
        
        # --- РАЗДЕЛИТЕЛЬ ---
        ttk.Separator(self.form_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1
        
        # --- ТОЧКИ ПАТРУЛЯ (patrol_points) ---
        ttk.Label(self.form_frame, text="Точки патруля (x, y):", 
                  font=("Arial", 9, "bold")).grid(
            row=row, column=0, sticky="w", padx=5, pady=3)
        
        patrol_frame = ttk.Frame(self.form_frame)
        patrol_frame.grid(row=row, column=1, sticky="ew", padx=5, pady=3)
        
        # Унифицируем формат: список списков [[x, y], [x, y], ...]
        patrol_points = data.get("patrol_points", [])
        # Приводим к унифицированному формату
        unified = []
        for pt in patrol_points:
            if isinstance(pt, dict):
                # Старый формат: {"pos": [x, y]}
                pos = pt.get("pos", [0, 0])
                unified.append(pos)
            elif isinstance(pt, list) and len(pt) == 2:
                unified.append(pt)
        
        patrol_text = "\n".join([f"{p[0]},{p[1]}" for p in unified])
        
        self.patrol_text_widget = tk.Text(patrol_frame, width=30, height=8)
        self.patrol_text_widget.insert("1.0", patrol_text)
        self.patrol_text_widget.pack(side="left", fill="both", expand=True)
        
        patrol_scroll = ttk.Scrollbar(patrol_frame, orient="vertical",
                                       command=self.patrol_text_widget.yview)
        patrol_scroll.pack(side="right", fill="y")
        self.patrol_text_widget.configure(yscrollcommand=patrol_scroll.set)
        
        ttk.Label(self.form_frame, text="(каждая точка с новой строки: x,y)",
                  foreground="gray").grid(row=row+1, column=1, sticky="w", padx=5)
        
        row += 2
        
        # Настраиваем вес колонок
        self.form_frame.columnconfigure(1, weight=1)
    
    def _save_current_npc(self):
        """Сохраняет текущий NPC в JSON."""
        if not self.current_npc_file:
            messagebox.showwarning("Внимание", "Нечего сохранять")
            return
        
        # Собираем данные из формы
        data = {}
        
        for field_name, (widget, var, field_type) in self.field_widgets.items():
            value = var.get()
            
            if field_type == "dialog":
                # ВАЛИДАЦИЯ dialog_id: проверяем существование файла
                if value:
                    location_path = self._get_location_path(self.current_location)
                    dialog_file = os.path.join(location_path, "dialogs", f"{value}.json")
                    if not os.path.exists(dialog_file):
                        if not messagebox.askyesno(
                            "Предупреждение",
                            f"Файл диалога '{value}.json' не найден в dialogs/.\n"
                            f"Сохранить всё равно?"
                        ):
                            return
            
            data[field_name] = value
        
        # Обрабатываем patrol_points (унифицированный формат)
        patrol_text = self.patrol_text_widget.get("1.0", "end").strip()
        patrol_points = []
        for line in patrol_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) == 2:
                try:
                    x, y = int(parts[0].strip()), int(parts[1].strip())
                    patrol_points.append([x, y])
                except ValueError:
                    messagebox.showwarning(
                        "Ошибка",
                        f"Неверный формат точки патруля: '{line}'\n"
                        f"Ожидается формат: x,y"
                    )
                    return
        
        data["patrol_points"] = patrol_points
        
        # Сохраняем в файл
        try:
            with open(self.current_npc_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("Успех", f"NPC сохранён в {self.current_npc_file}")
            
            # Обновляем список
            self._load_npcs_for_location(self.current_location)
            self._populate_npc_list()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")
    
    # =========================================================================
    # ЗАПУСК
    # =========================================================================
    
    def run(self):
        """Запускает главный цикл Tkinter."""
        self.root.mainloop()


def main():
    """Точка входа."""
    app = ActorCreator()
    app.run()


if __name__ == "__main__":
    main()