"""Kharcha Track - a small, offline expense tracker built with Kivy.

Runs on desktop for development and on Android once packaged with Buildozer
(see buildozer.spec). All data is stored locally in a JSON file inside the
app's private data directory, so it works completely offline.

Developed to be mobile friendly: portrait layout, tap a row to edit it, use
the delete button, or the "+" button to add a new expense.
"""

import json
import os
import sys
import time
import uuid
from datetime import date, datetime, timedelta

# Keep Kivy from swallowing our own command line flags (e.g. --smoke).
os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.togglebutton import ToggleButton

# Change this symbol if you use another currency.
CURRENCY = "\u20b9"  # Indian Rupee

# (name, colour) - the colour is used for the category dot / chips / bars.
CATEGORIES = (
    ("Food", "#ff9800"),
    ("Transport", "#2196f3"),
    ("Shopping", "#e91e63"),
    ("Bills", "#9c27b0"),
    ("Health", "#4caf50"),
    ("Fun", "#00bcd4"),
    ("Other", "#9e9e9e"),
)
CATEGORY_COLORS = dict(CATEGORIES)
CATEGORY_NAMES = [name for name, _ in CATEGORIES]

KV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kharcha.kv")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def hex_rgba(value, alpha=1.0):
    """Convert '#rrggbb' to a Kivy friendly [r, g, b, a] list."""
    value = value.lstrip("#")
    return [int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [alpha]


def _indian_group(digits):
    """Group digits the Indian way: 1234567 -> '12,34,567'."""
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def money(amount):
    """Format a number as currency, e.g. 1234567.5 -> 'Rs 12,34,567.50'."""
    negative = amount < 0
    amount = abs(amount)
    if abs(amount - round(amount)) < 1e-9:
        whole, frac = "{0}".format(int(round(amount))), ""
    else:
        whole, frac = "{0:.2f}".format(amount).split(".")
    text = _indian_group(whole)
    if frac:
        text += "." + frac
    return "{0}{1}{2}".format("-" if negative else "", CURRENCY, text)


def month_key(day):
    return day.strftime("%Y-%m")


def month_label(key):
    return datetime.strptime(key, "%Y-%m").strftime("%B %Y")


def shift_month(key, delta):
    year, month = (int(part) for part in key.split("-"))
    month += delta
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1
    return "{0:04d}-{1:02d}".format(year, month)


def pretty_day(iso):
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%d %b %Y")


# --------------------------------------------------------------------------- #
# widgets defined here so they can carry real Kivy properties
# --------------------------------------------------------------------------- #
class ExpenseRow(BoxLayout):
    """One row in the transaction list."""
    eid = StringProperty("")
    note = StringProperty("")
    category = StringProperty("")
    amount_text = StringProperty("")
    day_text = StringProperty("")
    cat_color = ListProperty([1, 1, 1, 1])


class RowTapArea(ButtonBehavior, BoxLayout):
    eid = StringProperty("")


class FilterChip(ToggleButton):
    cat_color = ListProperty([1, 1, 1, 1])


class CatChip(ToggleButton):
    cat_color = ListProperty([1, 1, 1, 1])


class CategoryBar(BoxLayout):
    label_text = StringProperty("")
    amount_text = StringProperty("")
    fraction = NumericProperty(0.0)
    cat_color = ListProperty([1, 1, 1, 1])


# --------------------------------------------------------------------------- #
# main screen
# --------------------------------------------------------------------------- #
class KharchaRoot(BoxLayout):
    month = StringProperty()
    month_text = StringProperty()
    filter_cat = StringProperty("All")

    total_amount = StringProperty("0")
    total_meta = StringProperty("")
    empty_hint = StringProperty("")

    # every saved expense: {'id', 'amount', 'category', 'note', 'date', 'created'}
    entries = ListProperty([])

    # add / edit popup state
    popup_title = StringProperty("Add expense")
    popup_date = StringProperty("")
    popup_date_text = StringProperty("")
    editing_id = StringProperty("")
    err_text = StringProperty("")

    # where expenses.json lives (set by the App)
    data_dir = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.month = month_key(date.today())
        self.month_text = month_label(self.month)
        self._set_popup_date(date.today().isoformat())
        self.add_popup = None
        self.confirm_popup = None
        self._pending_delete = ""
        self.bind(month=self._on_month_change,
                  filter_cat=self._on_month_change)
        Clock.schedule_once(self._after_build, 0)

    # -- startup ---------------------------------------------------------- #
    def _after_build(self, _dt):
        # Popups are created now (not in __init__) because their KV rules
        # reference `app.root`, which only exists once the App is running.
        self.add_popup = Factory.AddExpensePopup()
        self.confirm_popup = Factory.ConfirmPopup()
        self._build_filter_chips()
        self._build_category_buttons()
        self.refresh()

    @property
    def data_file(self):
        base = self.data_dir or os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "expenses.json")

    def _on_month_change(self, *_args):
        self.month_text = month_label(self.month)
        self.refresh()

    def _build_filter_chips(self):
        box = self.ids.chip_box
        box.clear_widgets()
        for name in ["All"] + CATEGORY_NAMES:
            chip = FilterChip(text=name, group="kharcha_filter")
            chip.cat_color = self._category_rgba(name)
            if name == "All":
                chip.state = "down"
            chip.bind(on_release=self._on_chip_release)
            box.add_widget(chip)

    def _build_category_buttons(self):
        grid = self.add_popup.ids.cat_grid
        grid.clear_widgets()
        for name in CATEGORY_NAMES:
            chip = CatChip(text=name, group="expense_category")
            chip.cat_color = self._category_rgba(name)
            grid.add_widget(chip)
        self._select_category("Food")

    @staticmethod
    def _category_rgba(name):
        return hex_rgba(CATEGORY_COLORS.get(name, "#9e9e9e"))

    def _on_chip_release(self, chip):
        self.filter_cat = chip.text

    # -- data ------------------------------------------------------------- #
    def load_data(self):
        entries = []
        try:
            with open(self.data_file, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (OSError, ValueError):
            raw = []
        if isinstance(raw, list):
            for item in raw:
                entry = self._clean_entry(item)
                if entry:
                    entries.append(entry)
        self.entries[:] = entries
        self.refresh()

    @staticmethod
    def _clean_entry(item):
        try:
            return {
                "id": str(item["id"]),
                "amount": round(float(item["amount"]), 2),
                "category": str(item.get("category", "Other")),
                "note": str(item.get("note", "")),
                "date": str(item["date"]),
                "created": float(item.get("created", 0)),
            }
        except (KeyError, TypeError, ValueError):
            return None

    def save_data(self):
        directory = os.path.dirname(self.data_file)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)
        tmp = self.data_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(list(self.entries), handle, ensure_ascii=False, indent=1)
        os.replace(tmp, self.data_file)

    def month_entries(self):
        prefix = self.month + "-"
        rows = [e for e in self.entries if e["date"].startswith(prefix)]
        rows.sort(key=lambda e: (e["date"], e["created"]), reverse=True)
        return rows

    # -- rendering -------------------------------------------------------- #
    def refresh(self):
        month_rows = self.month_entries()
        total = sum(entry["amount"] for entry in month_rows)
        self.total_amount = money(total)

        if not month_rows:
            self.total_meta = "No expenses this month yet"
        else:
            totals = self._category_totals(month_rows)
            top_name, top_value = max(totals.items(), key=lambda kv: kv[1])
            count = len(month_rows)
            self.total_meta = "{0} expense{1}  ·  top: {2} ({3})".format(
                count, "" if count == 1 else "s", top_name, money(top_value))

        data = []
        for entry in month_rows:
            if self.filter_cat != "All" and entry["category"] != self.filter_cat:
                continue
            data.append({
                "eid": entry["id"],
                "note": entry["note"],
                "category": entry["category"],
                "amount_text": money(entry["amount"]),
                "day_text": pretty_day(entry["date"]),
                "cat_color": self._category_rgba(entry["category"]),
            })
        self.ids.rv.data = data
        self.empty_hint = "" if data else (
            "Nothing here for this month.\nTap + to add an expense."
            if self.filter_cat == "All" else
            "No {0} expenses this month.".format(self.filter_cat))
        self._refresh_breakdown(month_rows)

    @staticmethod
    def _category_totals(rows):
        totals = {}
        for entry in rows:
            totals[entry["category"]] = \
                totals.get(entry["category"], 0.0) + entry["amount"]
        return totals

    def _refresh_breakdown(self, month_rows):
        box = self.ids.breakdown
        box.clear_widgets()
        totals = self._category_totals(month_rows)
        total = sum(totals.values())
        if total <= 0:
            return
        ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:3]
        for name, value in ranked:
            bar = CategoryBar(
                label_text=name,
                amount_text=money(value),
                fraction=value / total,
                cat_color=self._category_rgba(name),
            )
            box.add_widget(bar)

    # -- month navigation ------------------------------------------------- #
    def shift_month_by(self, delta):
        self.month = shift_month(self.month, delta)

    def go_to_today(self):
        self.month = month_key(date.today())

    # -- add / edit ------------------------------------------------------- #
    def display_month(self, iso_date):
        self.month = month_key(date.fromisoformat(iso_date))

    def _set_popup_date(self, iso_date):
        self.popup_date = iso_date
        self.popup_date_text = pretty_day(iso_date)

    def shift_popup_date(self, delta):
        new_day = date.fromisoformat(self.popup_date) + timedelta(days=delta)
        self._set_popup_date(new_day.isoformat())

    def today_popup_date(self):
        self._set_popup_date(date.today().isoformat())

    def _select_category(self, name):
        for button in self.add_popup.ids.cat_grid.children:
            button.state = "down" if button.text == name else "normal"

    def _selected_category(self):
        for button in self.add_popup.ids.cat_grid.children:
            if button.state == "down":
                return button.text
        return "Other"

    def open_add(self):
        self.editing_id = ""
        self.popup_title = "Add expense"
        self.err_text = ""
        self.add_popup.ids.amount_input.text = ""
        self.add_popup.ids.note_input.text = ""
        self._select_category("Food")
        self._set_popup_date(date.today().isoformat())
        self.add_popup.open()

    def open_edit(self, eid):
        entry = self._find(eid)
        if not entry:
            return
        self.editing_id = eid
        self.popup_title = "Edit expense"
        self.err_text = ""
        self.add_popup.ids.amount_input.text = "{0:g}".format(entry["amount"])
        self.add_popup.ids.note_input.text = entry["note"]
        self._select_category(entry["category"])
        self._set_popup_date(entry["date"])
        self.add_popup.open()

    def save_from_popup(self):
        raw = self.add_popup.ids.amount_input.text.strip().replace(",", "")
        try:
            amount = float(raw)
        except ValueError:
            amount = 0.0
        if amount <= 0:
            self.err_text = "Please enter an amount greater than zero."
            return

        category = self._selected_category()
        note = self.add_popup.ids.note_input.text.strip()

        if self.editing_id:
            entry = self._find(self.editing_id)
            if entry:
                entry.update(amount=round(amount, 2), category=category,
                             note=note, date=self.popup_date)
        else:
            self.entries.append({
                "id": uuid.uuid4().hex[:12],
                "amount": round(amount, 2),
                "category": category,
                "note": note,
                "date": self.popup_date,
                "created": time.time(),
            })

        self.save_data()
        self.err_text = ""
        self.editing_id = ""
        self.add_popup.dismiss()
        self.display_month(self.popup_date)

    # -- delete ----------------------------------------------------------- #
    def ask_delete(self, eid):
        self._pending_delete = eid
        self.confirm_popup.open()

    def confirm_delete(self):
        eid = self._pending_delete
        self._pending_delete = ""
        self.confirm_popup.dismiss()
        if not eid:
            return
        self.entries[:] = [e for e in self.entries if e["id"] != eid]
        self.save_data()
        self.refresh()

    def delete_entry(self, eid):
        self.entries[:] = [e for e in self.entries if e["id"] != eid]
        self.save_data()
        self.refresh()

    def _find(self, eid):
        for entry in self.entries:
            if entry["id"] == eid:
                return entry
        return None

    # -- used by the smoke test ------------------------------------------- #
    def seed_demo(self):
        today = date.today()
        samples = [
            (250.0, "Food", "Lunch with team", today),
            (80.0, "Transport", "Metro recharge", today),
            (1499.0, "Shopping", "New t-shirt", today),
            (1200.0, "Bills", "Electricity", today - timedelta(days=45)),
        ]
        for amount, category, note, day in samples:
            self.entries.append({
                "id": uuid.uuid4().hex[:12],
                "amount": amount,
                "category": category,
                "note": note,
                "date": day.isoformat(),
                "created": time.time(),
            })
        self.save_data()
        self.refresh()


class KharchaTrack(App):
    title = "Kharcha Track"

    def build(self):
        Window.clearcolor = (0.07, 0.08, 0.10, 1)
        Builder.load_file(KV_FILE)
        data_dir = self.user_data_dir
        if "--smoke" in sys.argv or "--shot" in sys.argv:
            # dev modes use a scratch folder and a phone-like window size
            import tempfile
            data_dir = os.path.join(tempfile.gettempdir(), "kharcha-track-dev")
            Window.size = (360, 640)
            Window.top = 0
            Window.left = 0
        root = KharchaRoot(data_dir=data_dir)
        self._root = root
        root.load_data()
        if "--smoke" in sys.argv:
            Clock.schedule_once(self._smoke_start, 0.6)
        elif "--shot" in sys.argv:
            Clock.schedule_once(self._shot_start, 0.6)
        return root

    def on_pause(self):
        # Keep the process alive when Android sends the app to the background.
        return True

    def on_resume(self):
        if getattr(self, "_root", None):
            self._root.load_data()

    # ------------------------------------------------------------------ #
    # --shot : render with demo data and save screenshot.png (dev helper)
    # ------------------------------------------------------------------ #
    def _shot_start(self, _dt):
        root = self._root
        if not root.entries:
            root.seed_demo()
            self._smoke_seeded = True
        root.refresh()
        target = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "screenshot.png")
        Window.screenshot(name=target)
        Clock.schedule_once(lambda _d: self.stop(), 0.8)

    # ------------------------------------------------------------------ #
    # --smoke : quickly boots the UI, exercises the controller and exits
    # ------------------------------------------------------------------ #
    def _smoke_start(self, _dt):
        root = self._root
        seeded = False
        if not root.entries:
            root.seed_demo()
            seeded = True
        self._smoke_seeded = seeded
        Clock.schedule_once(self._smoke_check, 0.8)

    def _smoke_check(self, _dt):
        root = self._root
        rv = root.ids.rv

        assert rv.data, "transaction list has no data"
        rows = []
        stack = [rv]
        while stack:
            widget = stack.pop()
            if isinstance(widget, ExpenseRow):
                rows.append(widget)
            stack.extend(getattr(widget, "children", []))
        assert rows, "RecycleView produced no ExpenseRow widgets"
        for row in rows:
            assert row.height > 0, "row has zero height"
        assert rows[0].amount_text.startswith(CURRENCY), "amount not formatted"
        assert len(rows) == len(rv.data), "all rows should be visible"

        before = len(root.entries)
        root.add_popup.ids.amount_input.text = "1234.5"
        root.add_popup.ids.note_input.text = "smoke add"
        root._select_category("Food")
        root._set_popup_date(date.today().isoformat())
        root.editing_id = ""
        root.save_from_popup()
        assert len(root.entries) == before + 1, "add failed"
        added = root.entries[-1]

        root.open_edit(added["id"])
        root.add_popup.ids.amount_input.text = "9.99"
        root.save_from_popup()
        assert root._find(added["id"])["amount"] == 9.99, "edit failed"

        root.delete_entry(added["id"])
        assert root._find(added["id"]) is None, "delete failed"
        assert len(root.entries) == before, "entry count not restored"

        total = sum(e["amount"] for e in root.month_entries())
        assert root.total_amount == money(total), "total label mismatch"
        assert money(1234567.5) == CURRENCY + "12,34,567.50", "money() wrong"

        with open(root.data_file, "r", encoding="utf-8") as handle:
            saved = json.load(handle)
        assert isinstance(saved, list) and len(saved) == len(root.entries)

        # ---- geometry / layout sanity ---------------------------------- #
        from kivy.core.window import Window as _Win
        assert root.width > 0 and root.height > 0, "root not laid out"
        summary = root.ids.summary
        assert summary.height > 120, "summary card too short: %s" % summary.height
        assert root.ids.rv.height > 200, "list area too short"
        assert root.ids.chip_box.width >= root.ids.chip_box.minimum_width * 0.9, \
            "chip row collapsed"
        fab = root.ids.fab
        assert fab.width >= 50 and fab.y > root.ids.rv.y, "fab misplaced"
        assert _Win.height >= root.ids.rv.y, "content taller than window"

        # popup fits on screen when opened
        root.open_add()
        popup = root.add_popup
        assert popup._window is not None, "popup did not open"
        assert popup.height <= _Win.height * 0.95, \
            "add popup taller than window: %s" % popup.height
        assert len(root.add_popup.ids.cat_grid.children) == len(CATEGORIES)
        root.add_popup.dismiss()

        print(
            "GEOM win=%sx%s root=%sx%s summary_h=%s rv=%sx%s@(%s,%s) "
            "chips=%s fab=@(%s,%s) rows=%d" % (
                _Win.width, _Win.height, root.width, root.height,
                summary.height,
                round(root.ids.rv.width), round(root.ids.rv.height),
                round(root.ids.rv.x), round(root.ids.rv.y),
                round(root.ids.chip_box.minimum_width),
                round(fab.x), round(fab.y), len(rows)))

        if getattr(self, "_smoke_seeded", False):
            try:
                os.remove(root.data_file)
            except OSError:
                pass

        print("SMOKE TEST PASSED")
        Clock.schedule_once(lambda _d: self.stop(), 0.1)


if __name__ == "__main__":
    KharchaTrack().run()
