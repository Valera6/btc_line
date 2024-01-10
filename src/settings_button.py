import json, tempfile, os
import tkinter as tk

tempdir = os.path.join(tempfile.gettempdir(), 'BTCline')
script_dir = os.path.dirname(os.path.realpath(__file__))
settings = json.load(open(os.path.join(tempdir, "settings.json"), 'r'))
src_dir = os.environ.get('SRC_DIR')
# with open(os.path.join(tempdir, 'src.txt'), 'r') as f:
#     src_dir = f.read()

settings_window = None


def update_settings(callback=None):
    global settings_window, widget_vars
    settings = json.load(open(os.path.join(tempdir, "settings.json"), 'r'))
    def find(key, value):
        for item in settings:
            if item == key:
                settings[item] = value
            try:
                if key in settings[item].keys():
                    settings[item][key] = value
            except:
                pass
        return settings

    for widget_name, widget in settings_window.children.items():
        if isinstance(widget, tk.Label):
            label_text = widget.cget('text')
            label = label_text.strip('\n :')
        if isinstance(widget, tk.Checkbutton):
            key = label
            value = widget_vars[key]
            if isinstance(value, tk.BooleanVar):
                settings = find(key, value.get())
        if isinstance(widget, tk.Scale):
            settings = find(label, widget.get())
        
    apply_changes(settings, callback)


def apply_changes(settings, callback=None):
    json.dump(settings, open(os.path.join(tempdir, "settings.json"), 'w'))
    close_settings_window()
    if callback is not None:
        callback()

def close_settings_window():
    global settings_window
    if settings_window is not None:
        settings_window.destroy()
        settings_window = None
def open_settings_window(callback=None):
    global settings_window, widget_vars
    if settings_window is not None:
        settings_window.lift()
        return
    widget_vars = {}
    settings_window = tk.Toplevel()
    settings_window.attributes("-topmost", True)
    settings_window.title("Settings")

    settings_window.protocol("WM_DELETE_WINDOW", close_settings_window)

    settings = json.load(open(os.path.join(tempdir, "settings.json"), 'r'))
    row = 0
    for key, value in settings.items():
        if not isinstance(value, dict):
            label = tk.Label(settings_window, text=key + ":")
            label.grid(row=row, column=0, sticky="w")

        if isinstance(value, bool):
            var = tk.BooleanVar(value=value)
            widget = tk.Checkbutton(settings_window, variable=var)
            widget.grid(row=row, column=1)
            widget_vars[key] = var
        elif isinstance(value, int):
            widget = tk.Scale(settings_window, from_=0, to=24, orient="horizontal", length=200)
            widget.set(value)
            widget.grid(row=row, column=1)
        elif isinstance(value, dict):
            separator = '\n'
            for subkey, subvalue in value.items():
                sublabel = tk.Label(settings_window, text=separator + "    " + subkey + ":")
                sublabel.grid(row=row, column=0, sticky="w")
                separator = ''
                if isinstance(subvalue, bool):
                    subvar = tk.BooleanVar(value=subvalue)
                    subwidget = tk.Checkbutton(settings_window, variable=subvar)
                    subwidget.grid(row=row, column=1)
                    widget_vars[subkey] = subvar
                elif isinstance(subvalue, int):
                    subwidget = tk.Scale(settings_window, from_=1, to=24, orient="horizontal", length=200)
                    subwidget.set(subvalue)
                    subwidget.grid(row=row, column=1)
                setattr(settings_window, subkey, subvalue)
                row += 1 # ok, because we don't expect any dictionaries here.
        else:
            raise ValueError("Invalid setting type")

        row += 1

    save_button = tk.Button(settings_window, text="Save", command=lambda: update_settings(callback))
    save_button.grid(row=row, column=0, columnspan=2)
    current_font = save_button.cget("font")
    fontsize = save_button.tk.call("font", "actual", current_font, "-size")
    default_settings = json.load(open(os.path.join(script_dir, 'display.json')))['default_settings']
    reset_button = tk.Button(settings_window, text="Reset", font=(current_font, int(fontsize * 2 / 3)), command=lambda: apply_changes(default_settings, callback))
    reset_button.grid(row=row, column=0, padx=0, pady=0)

def create_settings_button(master):
    gear_icon = tk.PhotoImage(file=os.path.join(src_dir, 'icons/gear.png'))
    gear_icon = gear_icon.subsample(gear_icon.width() // 17, gear_icon.height() // 17)
    settings_button = tk.Button(master, image=gear_icon, bg='black', padx=0, pady=0, borderwidth=0, command=open_settings_window)
    settings_button.image = gear_icon
    settings_button.place(x=0, y=0, width=17, height=17)

    return settings_button

if __name__ == "__main__":
    root = tk.Tk()
    create_settings_button(root)
    
    root.mainloop()