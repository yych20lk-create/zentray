import sys
import os
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
            continue

        label_text = item_data.get("label", "")
        icon_name = item_data.get("icon")

        if icon_name and icon_dir:
            img_path = os.path.join(icon_dir, f"{icon_name}.png")
            if os.path.exists(img_path):
                item = Gtk.ImageMenuItem(label=label_text)
                image = Gtk.Image.new_from_file(img_path)
                item.set_image(image)
                item.set_always_show_image(True)
            else:
                item = Gtk.MenuItem(label=label_text)
        else:
            item = Gtk.MenuItem(label=label_text)

        if not item_data.get("enabled", True):
            item.set_sensitive(False)

        if "submenu" in item_data:
            submenu = build_menu(item_data["submenu"])
            item.set_submenu(submenu)
        else:
            item.connect("activate", on_menu_item_clicked, item_data["id"])

        menu.append(item)

    menu.show_all()
    return menu

icon_dir = sys.argv[1] if len(sys.argv) > 1 else ""

if icon_dir:
    indicator = AppIndicator.Indicator.new_with_path(
        "gtd_ticker",
        "pie_none_0",
        AppIndicator.IndicatorCategory.APPLICATION_STATUS,
        icon_dir
    )
else:
    indicator = AppIndicator.Indicator.new(
        "gtd_ticker",
        "emblem-default",
        AppIndicator.IndicatorCategory.APPLICATION_STATUS
    )
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
            elif data.get("type") == "icon":
                icon_name = data["icon"]
                GLib.idle_add(indicator.set_icon, icon_name)
            elif data.get("type") == "quit":
                GLib.idle_add(Gtk.main_quit)
                break
        except Exception:
            pass

threading.Thread(target=read_stdin, daemon=True).start()
Gtk.main()
