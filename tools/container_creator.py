# tools/container_creator.py
# =============================================================================
# CONTAINER CREATOR — Утилита для создания и редактирования шаблонов контейнеров
# =============================================================================
# Работает с data/containers.json (единый справочник шаблонов контейнеров).
# Автогенерация ID: id_con_{NNN}[_suffix]
#
# Запуск: python tools/container_creator.py (из корня проекта)
# =============================================================================

import sys
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path

# ---------------------------------------------------------------------------
# НАСТРОЙКА ПУТЕЙ
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

CONTAINERS_JSON_PATH = os.path.join(PROJECT_ROOT, "data", "containers.json")

# Допустимые значения для enum-полей
VALID_ACCESS_SIDES = ["all", "north", "south", "east", "west"]


# ---------------------------------------------------------------------------
# ГЕНЕРАТОР ID КОНТЕЙНЕРА
# ---------------------------------------------------------------------------
def generate_container_id(containers_data: dict, custom_suffix: str = "") -> str:
    """
    Генерирует ID вида: id_con_{NNN}[_suffix]

    Примеры:
        custom_suffix="chest" → id_con_001_chest
        custom_suffix=""      → id_con_001
    """
    max_num = 0
    for con_id in containers_data.keys():
        if con_id.startswith("id_con_"):
            parts = con_id.split("_")
            if len(parts) >= 3:
                try:
                    num = int(parts[2])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass

    # Формируем базовую часть
    new_id = f"id_con_{max_num + 1:03d}"

    # Добавляем опциональный суффикс
    if custom_suffix:
        suffix = custom_suffix.strip().replace(" ", "_").lower()
        suffix = ''.join(c for c in suffix if c.isalnum() or c in "_-")
        if suffix:
            new_id += f"_{suffix}"

    return new_id


# ---------------------------------------------------------------------------
# ГЛАВНОЕ ПРИЛОЖЕНИЕ
# ---------------------------------------------------------------------------
class ContainerCreatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Last Way — Container Creator")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)

        self.containers = self._load_data()
        self.current_id = None
        self.field_widgets = {}

        self._build_ui()
        self._populate_list()

    # =========================================================================
    # ЗАГРУЗКА / СОХРАНЕНИЕ JSON
    # =========================================================================

    def _load_data(self) -> dict:
        if not os.path.exists(CONTAINERS_JSON_PATH):
            return {}
        try:
            with open(CONTAINERS_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            messagebox.showerror("Ошибка чтения",
                                 f"Не удалось прочитать containers.json:\n{e}")
            return {}

    def _save_data(self) -> bool:
        try:
            # Создаём папку data, если её нет
            os.makedirs(os.path.dirname(CONTAINERS_JSON_PATH), exist_ok=True)
            with open(CONTAINERS_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(self.containers, f, ensure_ascii=False,
                          indent=2, sort_keys=True)
            return True
        except Exception as e:
            messagebox.showerror("Ошибка записи",
                                 f"Не удалось сохранить containers.json:\n{e}")
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

        ttk.Label(left_frame, text="Шаблоны контейнеров",
                  font=("Arial", 11, "bold")).pack(pady=(0, 5))

        # Поиск
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._populate_list())
        search_entry = ttk.Entry(left_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(left_frame, text="(поиск по ID и имени)",
                  font=("Arial", 8)).pack()

        # Список контейнеров
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.containers_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            selectmode=tk.SINGLE
        )
        self.containers_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.containers_listbox.yview)
        self.containers_listbox.bind("<<ListboxSelect>>", self._on_select)

        # Кнопки
        ttk.Button(left_frame, text="➕ Новый контейнер",
                   command=self._new_container).pack(fill=tk.X, pady=2)
        ttk.Button(left_frame, text="🗑 Удалить выбранный",
                   command=self._delete_container).pack(fill=tk.X, pady=2)

        # --- ПРАВАЯ ПАНЕЛЬ ---
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)

        ttk.Label(right_frame, text="Параметры контейнера",
                  font=("Arial", 12, "bold")).pack(pady=(0, 10))

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

        # Кнопки
        buttons_frame = ttk.Frame(right_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(buttons_frame, text="💾 Сохранить в containers.json",
                   command=self._save_current).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="🔄 Очистить форму",
                   command=self._clear_form).pack(side=tk.LEFT, padx=5)

        # Статус
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(self.root, textvariable=self.status_var,
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # =========================================================================
    # СПИСОК КОНТЕЙНЕРОВ
    # =========================================================================

    def _populate_list(self):
        """Заполняет список контейнеров с учётом поиска."""
        self.containers_listbox.delete(0, tk.END)

        search_term = self.search_var.get().lower().strip()
        sorted_ids = sorted(self.containers.keys())

        for cid in sorted_ids:
            data = self.containers[cid]
            name = data.get("name", cid)

            # Поиск по ID и имени
            if search_term:
                if search_term not in cid.lower() and search_term not in name.lower():
                    continue

            display_text = f"{cid} — {name}"
            self.containers_listbox.insert(tk.END, display_text)

    def _on_select(self, event):
        """Обработчик выбора контейнера в списке."""
        selection = self.containers_listbox.curselection()
        if not selection:
            return

        display_text = self.containers_listbox.get(selection[0])
        cid = display_text.split(" — ")[0]

        if cid not in self.containers:
            return

        self._load_to_form(cid)

    # =========================================================================
    # ФОРМА: ЗАПОЛНЕНИЕ / ОЧИСТКА
    # =========================================================================

    def _clear_form(self):
        """Очищает форму редактирования."""
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.field_widgets = {}
        self.current_id = None
        self.status_var.set("Форма очищена.")

    def _load_to_form(self, cid):
        """Загружает контейнер в форму для редактирования."""
        self._clear_form()
        self.current_id = cid
        data = self.containers[cid]

        row = 0
        parent = self.form_frame

        # ID (только для чтения)
        ttk.Label(parent, text="ID:",
                  font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=5, pady=5)
        id_label = ttk.Label(parent, text=cid, foreground="blue",
                             font=("Consolas", 10, "bold"))
        id_label.grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1

        # Разделитель
        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1

        # Определяем поля
        fields = [
            ("name", "Название *", "str", data.get("name", "")),
            ("width", "Ширина (клетки)", "int", data.get("width", 1)),
            ("height", "Высота (клетки)", "int", data.get("height", 1)),
            ("locked", "Заперт", "bool", data.get("locked", False)),
            ("access_side", "Сторона доступа", "enum",
             data.get("access_side", "all"), VALID_ACCESS_SIDES),
        ]

        for field_info in fields:
            fname = field_info[0]
            flabel = field_info[1]
            ftype = field_info[2]
            fdefault = field_info[3]
            foptions = field_info[4] if len(field_info) > 4 else None

            ttk.Label(parent, text=flabel + ":").grid(
                row=row, column=0, sticky="w", padx=5, pady=3)

            if ftype == "bool":
                var = tk.BooleanVar(value=bool(fdefault))
                widget = ttk.Checkbutton(parent, variable=var)
            elif ftype == "int":
                var = tk.IntVar(value=int(fdefault) if fdefault else 1)
                widget = ttk.Spinbox(parent, textvariable=var,
                                     from_=1, to=10, increment=1, width=37)
            elif ftype == "enum":
                var = tk.StringVar(
                    value=fdefault if fdefault in foptions else foptions[0])
                widget = ttk.Combobox(parent, textvariable=var,
                                      values=foptions, state="readonly",
                                      width=37)
            else:  # str
                var = tk.StringVar(value=str(fdefault) if fdefault else "")
                widget = ttk.Entry(parent, textvariable=var, width=40)

            widget.grid(row=row, column=1, sticky="ew", padx=5, pady=3)
            self.field_widgets[fname] = (widget, var, ftype)
            row += 1

        # Подсказки
        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1

        hint_text = (
            "Примечания:\n"
            "• Ширина и высота задаются в клетках (1x1, 2x1, 3x1 и т.д.)\n"
            "• Сторона доступа 'all' — можно подойти с любой стороны\n"
            "• Конкретная сторона (north/south/east/west) — только с неё\n"
            "• Содержимое контейнера задаётся в location.json, не здесь"
        )
        hint_label = ttk.Label(parent, text=hint_text, foreground="gray",
                               font=("Arial", 9), justify=tk.LEFT)
        hint_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        parent.columnconfigure(1, weight=1)
        self.status_var.set(f"Редактирование: {cid}")

    # =========================================================================
    # СОЗДАНИЕ / УДАЛЕНИЕ / СОХРАНЕНИЕ
    # =========================================================================

    def _new_container(self):
        """Создание нового контейнера."""
        suffix = simpledialog.askstring(
            "Новый контейнер",
            "Введите суффикс ID (необязательно):\n"
            "Например: chest, table, wardrobe\n"
            "Оставьте пустым для ID без суффикса."
        )

        # Генерируем ID
        new_id = generate_container_id(self.containers, suffix or "")

        # Проверяем конфликт (маловероятно, но на всякий случай)
        if new_id in self.containers:
            messagebox.showerror(
                "Конфликт ID",
                f"Сгенерированный ID '{new_id}' уже существует."
            )
            return

        # Создаём шаблон
        self.containers[new_id] = {
            "name": "Новый контейнер",
            "width": 1,
            "height": 1,
            "locked": False,
            "access_side": "all",
        }

        if self._save_data():
            self.status_var.set(f"✅ Создан контейнер '{new_id}'")
            self._populate_list()

            # Выделяем новый элемент в списке
            for i in range(self.containers_listbox.size()):
                if self.containers_listbox.get(i).startswith(new_id + " —"):
                    self.containers_listbox.selection_clear(0, tk.END)
                    self.containers_listbox.selection_set(i)
                    self.containers_listbox.see(i)
                    self._load_to_form(new_id)
                    break

    def _delete_container(self):
        """Удаление выбранного контейнера."""
        selection = self.containers_listbox.curselection()
        if not selection:
            messagebox.showinfo("Нет выбора",
                                "Выберите контейнер для удаления.")
            return

        display_text = self.containers_listbox.get(selection[0])
        cid = display_text.split(" — ")[0]

        if not messagebox.askyesno(
            "Подтверждение удаления",
            f"Удалить шаблон контейнера '{cid}' из containers.json?\n\n"
            f"ВНИМАНИЕ: ссылки на этот контейнер в location.json "
            f"НЕ будут автоматически удалены!"
        ):
            return

        if cid in self.containers:
            del self.containers[cid]
            if self._save_data():
                self.status_var.set(f"🗑 Контейнер '{cid}' удалён.")
                self._clear_form()
                self._populate_list()

    def _save_current(self):
        """Сохраняет текущий контейнер в containers.json."""
        if not self.current_id:
            messagebox.showwarning("Внимание", "Нечего сохранять.")
            return

        # Валидация имени
        name_var = None
        for fname, (widget, var, ftype) in self.field_widgets.items():
            if fname == "name":
                name_var = var
                break

        if name_var:
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Ошибка валидации",
                                       "Поле 'Название' не может быть пустым.")
                return

        # Собираем данные
        data = self.containers[self.current_id]
        for fname, (widget, var, ftype) in self.field_widgets.items():
            value = var.get()
            if ftype == "int":
                data[fname] = int(value)
            elif ftype == "bool":
                data[fname] = bool(value)
            else:
                data[fname] = str(value)

        if self._save_data():
            self.status_var.set(
                f"✅ Контейнер '{self.current_id}' успешно сохранён.")
            self._populate_list()

            # Выделяем сохранённый элемент
            for i in range(self.containers_listbox.size()):
                if self.containers_listbox.get(i).startswith(
                        self.current_id + " —"):
                    self.containers_listbox.selection_clear(0, tk.END)
                    self.containers_listbox.selection_set(i)
                    self.containers_listbox.see(i)
                    break

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

    app = ContainerCreatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()