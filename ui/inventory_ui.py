# ui/inventory_ui.py
# =============================================================================
# ИНВЕНТАРЬ (INVENTORY MENU) — только отрисовка и ввод.
# Механика — в systems/inventory_system.py.
# =============================================================================

import pygame
import os
from settings import WIDTH, HEIGHT, BLACK, WHITE, YELLOW, GREEN, RED
from logger import log
from objects.item import PaperDollSlot, ItemCategory

BG_IMAGE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "images", "inventory_bg.png"
)

BLOCK_ORDER_DEFAULT = ["paper_doll", "archive", "casket", "burden"]
BLOCK_ORDER_EXCHANGE = ["paper_doll", "archive", "casket", "burden", "source"]

BLOCK_LABELS = {
    "paper_doll": "ЭКИПИРОВКА",
    "archive": "АРХИВ",
    "casket": "ЛАРЕЦ",
    "burden": "ПОКЛАЖА",
    "source": "ИСТОЧНИК",
}

PAPERDOLL_SLOTS = [
    ("clothing", "Одежда"),
    ("patch", "Вышивка"),
    ("weapon", "Оружие"),
    ("tool", "Инструмент"),
    ("ring", "Перстень"),
    ("amulet", "Амулет"),
]

CATEGORY_COLORS = {
    "weapon":     (220, 70, 70),
    "document":   (100, 150, 255),
    "key":        (255, 215, 0),
    "consumable": (100, 255, 100),
    "clothing":   (200, 200, 200),
    "tool":       (200, 180, 120),
    "valuable":   (255, 200, 100),
    "jewelry":    (255, 200, 100),
    "quest":      (200, 100, 255),
    "ingredient": (150, 255, 150),
    "ammo":       (220, 180, 100),
}
DEFAULT_ITEM_COLOR = (230, 230, 230)


class InventoryMenu:
    """
    Полноэкранное окно инвентаря с тремя блоками.
    Режимы: "inventory" (по I), "exchange" (с контейнером/дропом).
    """

    def __init__(self, game_engine):
        self.engine = game_engine
        self.is_active = False
        self.mode = "inventory"

        self.source = None
        self.source_type = None

        self.active_block = "archive"

        self.paper_doll_selected = 0
        self.archive_selected = 0
        self.casket_selected = 0
        self.burden_selected = 0
        self.source_selected = 0

        self._fonts = {}
        self.bg_image = self._load_background()

    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ
    # =========================================================================

    def _get_font(self, size: int):
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def _load_background(self):
        if os.path.exists(BG_IMAGE_PATH):
            try:
                image = pygame.image.load(BG_IMAGE_PATH)
                return pygame.transform.scale(image, (WIDTH, HEIGHT))
            except Exception as e:
                log.warning(f"INVENTORY: не удалось загрузить фон {BG_IMAGE_PATH}: {e}")
        return None

    def _get_item_color(self, item) -> tuple:
        try:
            return CATEGORY_COLORS.get(item.category.value, DEFAULT_ITEM_COLOR)
        except Exception:
            return DEFAULT_ITEM_COLOR

    def _get_source_title(self) -> str:
        if self.source is None:
            return "Источник"
        if self.source_type == "container":
            return getattr(self.source, 'name', 'Контейнер')
        if self.source_type == "drop":
            return "Куча на земле"
        return "Источник"

    def _get_block_order(self) -> list:
        return BLOCK_ORDER_EXCHANGE if self.mode == "exchange" else BLOCK_ORDER_DEFAULT

    def _get_selected_index(self) -> int:
        return {
            "paper_doll": self.paper_doll_selected,
            "archive": self.archive_selected,
            "casket": self.casket_selected,
            "burden": self.burden_selected,
            "source": self.source_selected,
        }.get(self.active_block, 0)

    def _set_selected_index(self, value: int):
        if self.active_block == "paper_doll":
            self.paper_doll_selected = value
        elif self.active_block == "archive":
            self.archive_selected = value
        elif self.active_block == "casket":
            self.casket_selected = value
        elif self.active_block == "burden":
            self.burden_selected = value
        elif self.active_block == "source":
            self.source_selected = value

    def _get_active_items(self) -> list:
        inv = self.engine.game_state.inventory
        if self.active_block == "paper_doll":
            return []
        if self.active_block == "archive":
            return inv.get_items_by_storage("archive")
        if self.active_block == "casket":
            return inv.get_items_by_storage("casket")
        if self.active_block == "burden":
            return inv.get_items_by_storage("burden")
        if self.active_block == "source":
            return self.source.get_items() if self.source else []
        return []

    def _clamp_active_index(self):
        items = self._get_active_items()
        max_idx = max(0, len(items) - 1) if items else 0
        if self.active_block == "paper_doll":
            max_idx = len(PAPERDOLL_SLOTS) - 1
        current = self._get_selected_index()
        self._set_selected_index(max(0, min(current, max_idx)))

    # =========================================================================
    # ОТКРЫТИЕ / ЗАКРЫТИЕ
    # =========================================================================

    def open(self, source=None, source_type: str = None):
        self.is_active = True
        if source is not None:
            self.mode = "exchange"
            self.source = source
            self.source_type = source_type
            self.active_block = "source"
            self.source_selected = 0
            log.info(f"INVENTORY: открыт в режиме обмена с {source_type}")
        else:
            self.mode = "inventory"
            self.source = None
            self.source_type = None
            self.active_block = "archive"
            self.archive_selected = 0
            log.info("INVENTORY: открыт")

    def close(self):
        if self.mode == "exchange" and self.source_type == "drop" and self.source is not None:
            if self.source.is_empty:
                current_map = self.engine.current_map
                if self.source in current_map.drops:
                    current_map.drops.remove(self.source)
                    log.info(f"INVENTORY: пустой дроп {self.source.id} удалён с карты")

        log.info(f"INVENTORY: закрыт (режим {self.mode})")
        self.is_active = False
        self.mode = "inventory"
        self.source = None
        self.source_type = None

    # =========================================================================
    # ВВОД
    # =========================================================================

    def handle_event(self, event) -> bool:
        if event.type != pygame.KEYDOWN:
            return False

        if event.key in (pygame.K_i, pygame.K_ESCAPE):
            self.close()
            return True

        if event.key == pygame.K_LEFT:
            blocks = self._get_block_order()
            current_idx = blocks.index(self.active_block) if self.active_block in blocks else 0
            self.active_block = blocks[(current_idx - 1) % len(blocks)]
            self._clamp_active_index()
            return True

        if event.key == pygame.K_RIGHT:
            blocks = self._get_block_order()
            current_idx = blocks.index(self.active_block) if self.active_block in blocks else 0
            self.active_block = blocks[(current_idx + 1) % len(blocks)]
            self._clamp_active_index()
            return True

        if event.key == pygame.K_UP:
            self._set_selected_index(max(0, self._get_selected_index() - 1))
            return True

        if event.key == pygame.K_DOWN:
            items = self._get_active_items()
            if self.active_block == "paper_doll":
                max_idx = len(PAPERDOLL_SLOTS) - 1
            else:
                max_idx = max(0, len(items) - 1) if items else 0
            self._set_selected_index(min(max_idx, self._get_selected_index() + 1))
            return True

        if event.key == pygame.K_RETURN:
            self._on_enter()
            return True

        if event.key == pygame.K_e:
            self._on_equip()
            return True

        if event.key == pygame.K_DELETE:
            self._on_drop()
            return True

        return True

    # =========================================================================
    # ДЕЙСТВИЯ (делегируют в InventorySystem)
    # =========================================================================

    def _on_enter(self):
        """Enter: взять / положить / использовать. Механика — в InventorySystem."""
        try:
            player = self.engine.game_state.player
            system = self.engine.inventory_system

            # --- SOURCE: взять ---
            if self.active_block == "source":
                items = self.source.get_items() if self.source else []
                idx = self.source_selected
                if not items or idx >= len(items):
                    self.engine._show_message("Нечего брать")
                    return

                item = items[idx]
                taken, msg = system.pick_up_from_source(
                    item, self.source, self.source_type, player
                )
                self.engine._show_message(msg)
                if taken <= 0:
                    return

                storage = getattr(item.storage_type, 'value', None)
                if storage in ("archive", "casket", "burden"):
                    self.active_block = storage
                    items_in_block = self.engine.game_state.inventory.get_items_by_storage(storage)
                    if items_in_block:
                        self._set_selected_index(len(items_in_block) - 1)

                remaining = self.source.get_items() if self.source else []
                self.source_selected = (
                    min(self.source_selected, len(remaining) - 1) if remaining else 0
                )
                return

            if self.active_block == "paper_doll":
                return

            items = self._get_active_items()
            idx = self._get_selected_index()
            if not items or idx >= len(items):
                return
            item = items[idx]

            if item.category == ItemCategory.DOCUMENT:
                self.close()
                system.use_item(item, player)
                return

            if self.mode == "exchange" and self.source is not None:
                ok, msg = system.transfer_to_source(item, self.source, self.source_type, player)
                self.engine._show_message(msg)
                if ok:
                    self._clamp_active_index()
                return

            ok, msg = system.use_item(item, player)
            if msg:
                self.engine._show_message(msg)
            self._clamp_active_index()

        except Exception as e:
            import traceback
            log.error(f"INVENTORY._on_enter: КРИТИЧЕСКАЯ ОШИБКА: {e}")
            log.error(traceback.format_exc())
            self.engine._show_message(f"Ошибка: {type(e).__name__}")

    def _on_equip(self):
        """E: надеть (из инвентаря) или снять (с Paper Doll)."""
        player = self.engine.game_state.player
        system = self.engine.inventory_system

        if self.active_block == "paper_doll":
            slot_id = PAPERDOLL_SLOTS[self.paper_doll_selected][0]
            try:
                slot = PaperDollSlot(slot_id)
            except ValueError:
                return
            ok, msg = system.unequip_item(slot, player)
            self.engine._show_message(msg)
            return

        if self.active_block in ("archive", "casket", "burden"):
            items = self._get_active_items()
            idx = self._get_selected_index()
            if not items or idx >= len(items):
                self.engine._show_message("Нечего экипировать")
                return
            item = items[idx]
            ok, msg = system.equip_item(item, player)
            self.engine._show_message(msg)
            if ok:
                self._clamp_active_index()
            return

        if self.active_block == "source":
            self.engine._show_message("Нельзя экипировать отсюда")

    def _on_drop(self):
        """Delete: выбросить выбранный предмет под ноги."""
        player = self.engine.game_state.player
        system = self.engine.inventory_system

        if self.active_block == "source":
            self.engine._show_message("Нельзя выбросить отсюда")
            return

        if self.active_block == "paper_doll":
            slot_id = PAPERDOLL_SLOTS[self.paper_doll_selected][0]
            try:
                slot = PaperDollSlot(slot_id)
            except ValueError:
                return
            item = self.engine.game_state.inventory.get_equipped(slot)
            if item is None:
                self.engine._show_message("Слот пуст")
                return
        else:
            items = self._get_active_items()
            idx = self._get_selected_index()
            if not items or idx >= len(items):
                self.engine._show_message("Нечего выбрасывать")
                return
            item = items[idx]

        ok, msg = system.drop_item(item, player)
        self.engine._show_message(msg)
        if ok:
            self._clamp_active_index()

    # =========================================================================
    # ОТРИСОВКА
    # =========================================================================

    def render(self, screen):
        if not self.is_active:
            return

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(180)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))
        else:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(220)
            overlay.fill((10, 8, 5))
            screen.blit(overlay, (0, 0))

        box_width = int(WIDTH * 0.9)
        box_height = int(HEIGHT * 0.85)
        box_x = (WIDTH - box_width) // 2
        box_y = (HEIGHT - box_height) // 2

        box_rect = pygame.Rect(box_x, box_y, box_width, box_height)
        pygame.draw.rect(screen, (20, 15, 10), box_rect)
        pygame.draw.rect(screen, (120, 100, 60), box_rect, 2)

        padding = 20
        content_x = box_x + padding
        content_y = box_y + padding
        content_width = box_width - 2 * padding
        content_height = box_height - 2 * padding - 40

        if self.mode == "exchange":
            w1 = int(content_width * 0.22)
            w2 = int(content_width * 0.35)
            w3 = content_width - w1 - w2 - 20
        else:
            w1 = int(content_width * 0.28)
            w2 = content_width - w1 - 10
            w3 = 0

        gap = 10
        h = content_height
        x1 = content_x
        x2 = content_x + w1 + gap
        x3 = content_x + w1 + gap + w2 + gap
        y = content_y

        self._render_paper_doll(screen, x1, y, w1, h)
        self._render_inventory_block(screen, x2, y, w2, h)
        if self.mode == "exchange":
            self._render_source_block(screen, x3, y, w3, h)

        self._render_hints(screen, box_x, box_y + box_height - 35, box_width)

    def _render_paper_doll(self, screen, x, y, w, h):
        is_active = (self.active_block == "paper_doll")

        rect = pygame.Rect(x, y, w, h)
        border_color = YELLOW if is_active else (80, 80, 80)
        border_width = 3 if is_active else 1
        pygame.draw.rect(screen, (30, 25, 20), rect)
        pygame.draw.rect(screen, border_color, rect, border_width)

        title_font = self._get_font(22)
        screen.blit(title_font.render(BLOCK_LABELS["paper_doll"], True, YELLOW), (x + 10, y + 8))
        pygame.draw.line(screen, (80, 70, 50), (x + 10, y + 35), (x + w - 10, y + 35), 1)

        slot_font = self._get_font(18)
        item_font = self._get_font(16)
        slot_height = 45
        start_y = y + 50
        inv = self.engine.game_state.inventory

        for i, (slot_id, slot_name) in enumerate(PAPERDOLL_SLOTS):
            slot_y = start_y + i * slot_height
            is_selected = (is_active and i == self.paper_doll_selected)

            if is_selected:
                pygame.draw.rect(screen, (60, 50, 20),
                                 pygame.Rect(x + 5, slot_y - 2, w - 10, slot_height - 4))

            marker = "▶" if is_selected else " "
            screen.blit(slot_font.render(marker, True, YELLOW), (x + 10, slot_y + 5))
            screen.blit(slot_font.render(slot_name + ":", True, (200, 200, 200)), (x + 30, slot_y + 5))

            try:
                slot = PaperDollSlot(slot_id)
                item = inv.get_equipped(slot)
                if item:
                    color = self._get_item_color(item)
                    value_surf = item_font.render(item.name, True, color)
                else:
                    value_surf = item_font.render("—", True, (120, 120, 120))
            except ValueError:
                value_surf = item_font.render("—", True, (120, 120, 120))

            screen.blit(value_surf, (x + 30, slot_y + 25))

        weight_text = f"Вес: {inv.get_total_weight():.1f}/{inv.max_weight:.1f} кг"
        screen.blit(self._get_font(16).render(weight_text, True, (180, 180, 180)), (x + 10, y + h - 25))

    def _render_inventory_block(self, screen, x, y, w, h):
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, (30, 25, 20), rect)
        pygame.draw.rect(screen, (80, 70, 50), rect, 1)

        screen.blit(self._get_font(22).render("ИНВЕНТАРЬ", True, YELLOW), (x + 10, y + 8))

        section_height = (h - 40) // 3
        sections = [
            ("archive", "АРХИВ", self.archive_selected),
            ("casket", "ЛАРЕЦ", self.casket_selected),
            ("burden", "ПОКЛАЖА", self.burden_selected),
        ]

        for i, (block_id, label, sel_idx) in enumerate(sections):
            sec_y = y + 40 + i * section_height
            self._render_storage_section(
                screen, x + 5, sec_y, w - 10, section_height - 5,
                block_id, label, sel_idx
            )

    def _render_storage_section(self, screen, x, y, w, h, block_id, label, sel_idx):
        is_active = (self.active_block == block_id)

        if is_active:
            bg_color = (40, 35, 25)
            border_color = YELLOW
            border_width = 2
        else:
            bg_color = (25, 22, 18)
            border_color = (60, 55, 45)
            border_width = 1

        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, bg_color, rect)
        pygame.draw.rect(screen, border_color, rect, border_width)

        label_color = YELLOW if is_active else (150, 140, 110)
        screen.blit(self._get_font(16).render(f"[{label}]", True, label_color), (x + 8, y + 4))

        items = self.engine.game_state.inventory.get_items_by_storage(block_id)
        item_font = self._get_font(16)
        row_height = 22
        max_visible = (h - 30) // row_height
        list_y = y + 26

        if not items:
            screen.blit(item_font.render("(пусто)", True, (100, 95, 85)), (x + 15, list_y))
        else:
            for i, item in enumerate(items):
                if i >= max_visible:
                    screen.blit(
                        item_font.render(f"... ещё {len(items) - max_visible}", True, (120, 115, 100)),
                        (x + 15, list_y + max_visible * row_height)
                    )
                    break

                row_y = list_y + i * row_height
                is_selected = (is_active and i == sel_idx)

                if is_selected:
                    pygame.draw.rect(screen, (60, 50, 20),
                                     pygame.Rect(x + 3, row_y - 1, w - 6, row_height - 2))

                marker = "▶ " if is_selected else "   "
                color = self._get_item_color(item)
                text = f"{marker}{item.name}"
                if item.quantity > 1:
                    text += f" (x{item.quantity})"

                screen.blit(item_font.render(text, True, color), (x + 10, row_y + 1))

                weight_text = f"{item.weight * item.quantity:.1f}"
                weight_surf = item_font.render(weight_text, True, (120, 115, 100))
                screen.blit(weight_surf, (x + w - weight_surf.get_width() - 8, row_y + 1))

    def _render_source_block(self, screen, x, y, w, h):
        is_active = (self.active_block == "source")

        rect = pygame.Rect(x, y, w, h)
        border_color = YELLOW if is_active else (80, 80, 80)
        border_width = 3 if is_active else 1
        pygame.draw.rect(screen, (30, 25, 20), rect)
        pygame.draw.rect(screen, border_color, rect, border_width)

        title_text = self.source.name if self.source_type == "container" else "Куча на земле"
        screen.blit(self._get_font(20).render(title_text.upper(), True, YELLOW), (x + 10, y + 8))
        pygame.draw.line(screen, (80, 70, 50), (x + 10, y + 35), (x + w - 10, y + 35), 1)

        items = self.source.get_items() if self.source else []
        item_font = self._get_font(18)
        row_height = 26
        max_visible = (h - 50) // row_height
        list_y = y + 45

        if not items:
            screen.blit(item_font.render("(пусто)", True, (120, 120, 120)), (x + 15, list_y))
        else:
            for i, item in enumerate(items):
                if i >= max_visible:
                    screen.blit(
                        item_font.render(f"... ещё {len(items) - max_visible}", True, (150, 150, 150)),
                        (x + 15, list_y + max_visible * row_height)
                    )
                    break

                row_y = list_y + i * row_height
                is_selected = (is_active and i == self.source_selected)

                if is_selected:
                    pygame.draw.rect(screen, (60, 50, 20),
                                     pygame.Rect(x + 3, row_y - 1, w - 6, row_height - 2))

                marker = "▶ " if is_selected else "   "
                color = self._get_item_color(item)
                text = f"{marker}{item.name}"
                if item.quantity > 1:
                    text += f" (x{item.quantity})"

                screen.blit(item_font.render(text, True, color), (x + 10, row_y + 2))

                weight_text = f"{item.weight * item.quantity:.1f} кг"
                weight_surf = item_font.render(weight_text, True, (120, 115, 100))
                screen.blit(weight_surf, (x + w - weight_surf.get_width() - 10, row_y + 2))

    def _render_hints(self, screen, x, y, w):
        hint_text = "   |   ".join([
            "← → — блоки", "↑ ↓ — выбор", "Enter — использовать",
            "E — экипировать", "Del — выбросить", "ESC — закрыть",
        ])
        hint_surf = self._get_font(16).render(hint_text, True, (180, 170, 140))
        screen.blit(hint_surf, (x + (w - hint_surf.get_width()) // 2, y))