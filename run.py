import tkinter as tk
from jackhammer_app.gui import JackhammerGUI

def main():
    root = tk.Tk()
    JackhammerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()