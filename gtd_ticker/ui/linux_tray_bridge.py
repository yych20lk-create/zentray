import sys
import json
import threading

try:
    import gi
    try:
        gi.require_version('AyatanaAppIndicator3', '0.1')
        from gi.repository import AyatanaAppIndicator3 as AppIndicator
    except ValueError:
        gi.require_version('AppIndicator3', '0.1')
        from gi.repository import AppIndicator3 as AppIndicator
    from gi.repository import Gtk, GLib
except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)

def on_menu_item_clicked(item, action_id):
    print(json.dumps({"action": action_id}), flush=True)

def build_menu(menu_data):
    menu = Gtk.Menu()
    for item_data in menu_data:
        if item_data == "separator":
            menu.append(Gtk.SeparatorMenuItem())
        elif "submenu" in item_data:
            item = Gtk.MenuItem(label=item_data["label"])
            submenu = build_menu(item_data["submenu"])
            item.set_submenu(submenu)
            if not item_data.get("enabled", True):
                item.set_sensitive(False)
            menu.append(item)
        else:
            item = Gtk.MenuItem(label=item_data["label"])
            item.connect("activate", on_menu_item_clicked, item_data["id"])
            if not item_data.get("enabled", True):
                item.set_sensitive(False)
            menu.append(item)
    menu.show_all()
    return menu

indicator = AppIndicator.Indicator.new(
    "gtd_ticker",
    "emblem-default",
    AppIndicator.IndicatorCategory.APPLICATION_STATUS)
indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

def read_stdin():
    for line in sys.stdin:
        try:
            data = json.loads(line)
            if data.get("type") == "label":
                text = data["text"]
                GLib.idle_add(indicator.set_label, text, text)
                GLib.idle_add(indicator.set_title, text)
            elif data.get("type") == "menu":
                menu = build_menu(data["items"])
                GLib.idle_add(indicator.set_menu, menu)
            elif data.get("type") == "quit":
                GLib.idle_add(Gtk.main_quit)
                break
        except Exception:
            pass

threading.Thread(target=read_stdin, daemon=True).start()
Gtk.main()
