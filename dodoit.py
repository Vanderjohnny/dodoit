import tkinter as tk
from tkinter import colorchooser
import threading
import json
import os
import time
import webbrowser
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

SAVE_FILE = os.path.join(os.environ['APPDATA'], 'dodoit_v3.json')

class PostItBall(tk.Toplevel):
    def __init__(self, parent, text, color, manager, start_time=None, repeat_min=0, next_reveal=0):
        super().__init__(parent)
        self.manager = manager
        self.text = text
        self.color = color
        self.start_time = start_time or time.time()
        self.repeat_min = repeat_min
        self.next_reveal = next_reveal
        self.size = 100
        self.paused = False
        
        self.overrideredirect(True)
        self.attributes("-topmost", True, "-alpha", 0.9, "-transparentcolor", "grey")
        self.geometry(f"{self.size}x{self.size}")

        self.canvas = tk.Canvas(self, width=self.size, height=self.size, bg="grey", highlightthickness=0)
        self.canvas.pack()

        self.circle = self.canvas.create_oval(5, 5, self.size-5, self.size-5, fill=color, outline="", width=0)
        self.label = tk.Label(self.canvas, text=text, bg=color, wraplength=70, font=("Arial", 8, "bold"))
        self.label.place(relx=0.5, rely=0.4, anchor="center")

        self.btn_done = tk.Button(self.canvas, text="✕", command=self.handle_close, font=("Arial", 8, "bold"), bg="#ffcccc", relief="flat")
        self.btn_done.place(relx=0.5, rely=0.75, anchor="center")

        self.bind("<Enter>", lambda e: setattr(self, 'paused', True))
        self.bind("<Leave>", lambda e: setattr(self, 'paused', False))

        self.x, self.y = 200, 200
        self.base_speed = 3.0
        self.dx, self.dy = self.base_speed, self.base_speed
        
        if self.next_reveal > time.time():
            self.withdraw()
            
        self.animate()

    def animate(self):
        try:
            now = time.time()
            if now >= self.next_reveal:
                if not self.winfo_viewable():
                    self.deiconify()
                
                if not self.paused:
                    hours_passed = (now - self.start_time) / 3600
                    factor = max(0.3, 1.0 - (hours_passed * 0.1)) 
                    
                    current_dx = (self.base_speed * factor) if self.dx > 0 else -(self.base_speed * factor)
                    current_dy = (self.base_speed * factor) if self.dy > 0 else -(self.base_speed * factor)

                    sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
                    self.x += current_dx
                    self.y += current_dy

                    if self.x + self.size >= sw or self.x <= 0: self.dx *= -1
                    if self.y + self.size >= sh or self.y <= 0: self.dy *= -1

                    self.geometry(f"+{int(self.x)}+{int(self.y)}")
            
            self.after(15, self.animate)
        except: pass

    def handle_close(self):
        if self.repeat_min > 0:
            self.next_reveal = time.time() + (self.repeat_min * 60)
            self.withdraw()
            self.manager.save_data()
        else:
            self.manager.remove_note(self)
            self.destroy()

class AppManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dodoit V3")
        self.root.geometry("380x620")
        self.notes = []
        self.selected_color = "#ffff88"

        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)

        tk.Label(self.root, text="Configurações da Nota:", font=("Arial", 10, "bold")).pack(pady=5)
        self.color_preview = tk.Frame(self.root, width=30, height=30, bg=self.selected_color, highlightthickness=1)
        self.color_preview.pack(pady=5)
        tk.Button(self.root, text="Escolher Cor", command=self.pick_color).pack(pady=5)

        tk.Label(self.root, text="Texto da nota:").pack()
        self.entry = tk.Entry(self.root)
        self.entry.pack(pady=5, padx=20, fill="x")

        tk.Label(self.root, text="Repetir a cada (minutos - 0 para única):").pack()
        self.repeat_entry = tk.Entry(self.root)
        self.repeat_entry.insert(0, "0")
        self.repeat_entry.pack(pady=5)

        tk.Button(self.root, text="Lançar Bolinha", command=self.add_note, bg="#ccffcc").pack(pady=10)

        tk.Label(self.root, text="Tarefas Ativas/Agendadas:", font=("Arial", 10, "bold")).pack(pady=5)
        self.list_frame = tk.Frame(self.root)
        self.list_frame.pack(expand=True, fill="both", padx=10, pady=5)

        self.insta_label = tk.Label(self.root, text="Desenvolvido por @alexandreguerrra", fg="blue", cursor="hand2", font=("Arial", 8))
        self.insta_label.pack(side="bottom", pady=10)
        self.insta_label.bind("<Button-1>", lambda e: webbrowser.open("https://www.instagram.com/alexandreguerrra"))

        self.load_data()
        threading.Thread(target=self.create_tray_icon, daemon=True).start()
        self.root.mainloop()

    def pick_color(self):
        color = colorchooser.askcolor(title="Cor do Post-it")[1]
        if color:
            self.selected_color = color
            self.color_preview.config(bg=color)

    def save_data(self):
        data = [
            {
                "text": n.text, 
                "color": n.color, 
                "start_time": n.start_time,
                "repeat_min": n.repeat_min,
                "next_reveal": n.next_reveal
            } for n in self.notes
        ]
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    def load_data(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                    for item in json.load(f):
                        self.add_note(
                            item['text'], 
                            item['color'], 
                            item['start_time'], 
                            repeat_min=item.get('repeat_min', 0),
                            next_reveal=item.get('next_reveal', 0),
                            save=False
                        )
            except: pass

    def add_note(self, text=None, color=None, start_time=None, repeat_min=None, next_reveal=0, save=True):
        if text is None:
            text = self.entry.get() or "Nota"
            self.entry.delete(0, tk.END)
        
        if repeat_min is None:
            try: repeat_min = int(self.repeat_entry.get())
            except: repeat_min = 0

        new_note = PostItBall(self.root, text, color if color else self.selected_color, self, start_time, repeat_min, next_reveal)
        self.notes.append(new_note)
        if save: self.save_data()
        self.update_list()

    def remove_note(self, note_obj):
        if note_obj in self.notes:
            self.notes.remove(note_obj)
            note_obj.destroy() # Garante que a janela feche
            self.save_data()
            self.update_list()

    def update_list(self):
        for widget in self.list_frame.winfo_children(): widget.destroy()
        for note in self.notes:
            frame = tk.Frame(self.list_frame)
            frame.pack(fill="x", pady=2)
            
            label_text = f"{note.text[:12]} ({note.repeat_min}m)" if note.repeat_min > 0 else note.text[:15]
            tk.Label(frame, text=label_text, bg=note.color, width=20, anchor="w").pack(side="left", padx=5)
            
            # Botão de deletar definitivo no Gerenciador
            tk.Button(frame, text="Deletar", bg="#ffcccc", command=lambda n=note: self.remove_note(n)).pack(side="right")

    def hide_window(self): self.root.withdraw()
    def show_window(self): self.root.after(0, self.root.deiconify)
    def quit_app(self, icon):
        icon.stop()
        self.root.after(0, self.root.quit)

    def create_tray_icon(self):
        image = Image.new('RGB', (64, 64), color='yellow')
        draw = ImageDraw.Draw(image)
        draw.ellipse([10, 10, 54, 54], fill="yellow")
        Icon("Dodoit", image, "Dodoit", Menu(MenuItem('Abrir', self.show_window), MenuItem('Sair', self.quit_app))).run()

if __name__ == "__main__":
    AppManager()
