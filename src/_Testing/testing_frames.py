import tkinter as tk, tempfile, os
from PIL import Image, ImageTk

tempdir = os.path.join(tempfile.gettempdir(), 'BTCline')

def create_button(window, text):
    button = tk.Button(window, text=text)
    button.pack(side='left')

window = tk.Tk()
frame = tk.Frame(window)
frame.pack()

create_button(frame, "Button 1")
create_button(frame, "Button 2")

img = Image.open(os.path.join(tempdir,'SpotInflowFig.png'))
photoInflows = ImageTk.PhotoImage(img)
inflows = tk.Label(frame, image=photoInflows)
inflows.image = photoInflows
inflows.pack(side='left')

window.mainloop()