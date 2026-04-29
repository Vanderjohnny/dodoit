import tkinter as tk
from tkinter import colorchooser
import threading, json, os, time, webbrowser, random, math, ctypes
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

# Configuração para capturar a área total de múltiplos monitores no Windows
def get_virtual_desktop_size():
    user32 = ctypes.windll.user32
    # SM_CXVIRTUALSCREEN = 78, SM_CYVIRTUALSCREEN = 79
    # SM_XVIRTUALSCREEN = 76, SM_YVIRTUALSCREEN = 77
    width = user32.GetSystemMetrics(78)
    height = user32.GetSystemMetrics(79)
    left = user32.GetSystemMetrics(76)
    top = user32.GetSystemMetrics(77)
    return width, height, left, top

SAVE_FILE = os.path.join(os.environ['APPDATA'], 'dodoit_v3_final.json')

LANGUAGES = {
    "pt-BR": {
        "title": "Nova Nota", "color_btn": "Escolher Cor", "text_label": "Texto:",
        "size_label": "Tamanho:", "repeat_label": "Duração (minutos p/ sumir):",
        "launch_btn": "Lançar Nota Normal", "water_btn": "💧 BOLINHA DA ÁGUA (30min)",
        "manage_label": "Tarefas Ativas/Agendadas:", "delete_btn": "Deletar",
        "water_text": "BEBER ÁGUA! 💧", "lang_label": "Idioma:"
    },
    "EN": {
        "title": "New Note", "color_btn": "Pick Color", "text_label": "Text:",
        "size_label": "Size:", "repeat_label": "Duration (minutes to vanish):",
        "launch_btn": "Launch Normal Note", "water_btn": "💧 WATER BALL (30min)",
        "manage_label": "Active/Scheduled Tasks:", "delete_btn": "Delete",
        "water_text": "DRINK WATER! 💧", "lang_label": "Language:"
    }
}

class PostItBall(tk.Toplevel):
    def __init__(self, parent, text, color, manager, start_time=None, duration_min=0, size=100, is_water=False):
        super().__init__(parent)
        self.manager = manager
        self.text = text
        self.color = color
        self.start_time = start_time or time.time()
        self.duration_min = duration_min
        self.size = size
        self.is_water = is_water
        self.paused = False
        self.visible = True
        self.exploding = False
        
        self.expiry_time = self.start_time + (duration_min * 60) if duration_min > 0 else None

        # Captura dimensões de todos os monitores
        self.v_width, self.v_height, self.v_left, self.v_top = get_virtual_desktop_size()

        self.overrideredirect(True)
        self.attributes("-topmost", True, "-alpha", 0.9, "-transparentcolor", "grey")
        
        # Posição inicial aleatória dentro de qualquer monitor
        self.x = random.randint(self.v_left, self.v_left + self.v_width - self.size)
        self.y = random.randint(self.v_top, self.v_top + self.v_height - self.size)
        self.geometry(f"{self.size}x{self.size}+{int(self.x)}+{int(self.y)}")

        self.canvas = tk.Canvas(self, width=self.size, height=self.size, bg="grey", highlightthickness=0)
        self.canvas.pack()
        self.circle = self.canvas.create_oval(5, 5, self.size-5, self.size-5, fill=color, outline="", width=0)
        
        f_size = 8 if self.size <= 100 else (12 if self.size <= 150 else 16)
        self.label = tk.Label(self.canvas, text=text, bg=color, wraplength=self.size-20, font=("Arial", f_size, "bold"))
        self.label.place(relx=0.5, rely=0.4, anchor="center")
        
        self.btn_done = tk.Button(self.canvas, text="✕", command=self.close_note, font=("Arial", f_size-2, "bold"), bg="#ffcccc", relief="flat")
        self.btn_done.place(relx=0.5, rely=0.75, anchor="center")

        self.bind("<Enter>", lambda e: setattr(self, 'paused', True))
        self.bind("<Leave>", lambda e: setattr(self, 'paused', False))

        self.dx = random.choice([4, -4, 3, -3])
        self.dy = random.choice([4, -4, 3, -3])
        self.particles = []
        self.animate()

    def animate(self):
        try:
            if self.exploding:
                self.animate_explosion()
                return

            now = time.time()
            if self.expiry_time and now >= self.expiry_time:
                if self.is_water:
                    self.start_time = now + (self.duration_min * 60)
                    self.expiry_time = self.start_time + (self.duration_min * 60)
                    self.withdraw()
                    self.visible = False
                else:
                    self.start_explosion()
                    return

            if self.is_water and not self.visible and now >= self.start_time:
                self.deiconify()
                self.visible = True

            if self.visible and not self.paused:
                self.x += self.dx
                self.y += self.dy
                
                # Colisão com as bordas do desktop virtual (Multi-monitor)
                if self.x + self.size >= self.v_left + self.v_width or self.x <= self.v_left: 
                    self.dx *= -1
                if self.y + self.size >= self.v_top + self.v_height or self.y <= self.v_top: 
                    self.dy *= -1
                
                self.geometry(f"+{int(self.x)}+{int(self.y)}")
            
            self.after(20, self.animate)
        except: pass

    def start_explosion(self):
        self.exploding = True
        self.canvas.itemconfig(self.circle, state='hidden')
        self.label.place_forget()
        self.btn_done.place_forget()
        
        new_size = self.size * 2
        self.x -= self.size / 2
        self.y -= self.size / 2
        self.geometry(f"{int(new_size)}x{int(new_size)}+{int(self.x)}+{int(self.y)}")
        self.canvas.config(width=new_size, height=new_size)
        
        for _ in range(25):
            p_size = random.randint(3, 8)
            p_id = self.canvas.create_oval(new_size/2, new_size/2, new_size/2+p_size, new_size/2+p_size, fill=self.color, outline="")
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 8)
            self.particles.append({'id': p_id, 'dx': math.cos(angle)*speed, 'dy': math.sin(angle)*speed, 'life': 1.0})
        self.animate_explosion()

    def animate_explosion(self):
        try:
            active = False
            for p in self.particles:
                if p['life'] > 0:
                    active = True
                    self.canvas.move(p['id'], p['dx'], p['dy'])
                    p['life'] -= 0.04
                    if p['life'] <= 0: self.canvas.delete(p['id'])
            if active: self.after(30, self.animate_explosion)
            else: self.close_note()
        except: pass

    def close_note(self):
        self.manager.remove_note(self)
        self.destroy()

class AppManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dodoit V3 Pro Max")
        self.root.geometry("400x750")
        self.notes = []
        self.selected_color = "#ffff88"
        self.size_var = tk.IntVar(value=100)
        self.lang_var = tk.StringVar(value="pt-BR")
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)

        # UI - LINGUAGEM
        l_frame = tk.Frame(self.root); l_frame.pack(pady=5)
        self.l_lbl = tk.Label(l_frame); self.l_lbl.pack(side="left")
        self.l_menu = tk.OptionMenu(l_frame, self.lang_var, *LANGUAGES.keys(), command=self.update_ui)
        self.l_menu.pack(side="left")

        # UI - CONTROLES
        self.title_lbl = tk.Label(self.root, font=("Arial", 11, "bold")); self.title_lbl.pack()
        f_color = tk.Frame(self.root); f_color.pack(pady=5)
        self.c_prev = tk.Frame(f_color, width=25, height=25, bg=self.selected_color, highlightthickness=1); self.c_prev.pack(side="left", padx=5)
        self.c_btn = tk.Button(f_color, command=self.pick_color); self.c_btn.pack(side="left")

        self.txt_lbl = tk.Label(self.root); self.txt_lbl.pack()
        self.entry = tk.Entry(self.root, width=35); self.entry.pack(pady=2)

        self.sz_lbl = tk.Label(self.root); self.sz_lbl.pack()
        f_sz = tk.Frame(self.root); f_sz.pack()
        for sz in [("P", 100), ("M", 150), ("G", 200)]:
            tk.Radiobutton(f_sz, text=sz[0], variable=self.size_var, value=sz[1]).pack(side="left")

        self.dur_lbl = tk.Label(self.root); self.dur_lbl.pack()
        self.dur_entry = tk.Entry(self.root, width=10); self.dur_entry.insert(0, "0"); self.dur_entry.pack()

        self.launch_btn = tk.Button(self.root, command=self.add_note, bg="#ccffcc", width=25); self.launch_btn.pack(pady=10)
        self.water_btn = tk.Button(self.root, command=self.add_water, bg="#add8e6", font=("Arial", 9, "bold")); self.water_btn.pack(pady=5)

        self.m_lbl = tk.Label(self.root, font=("Arial", 10, "bold")); self.m_lbl.pack(pady=5)
        self.list_frame = tk.Frame(self.root); self.list_frame.pack(expand=True, fill="both")

        tk.Label(self.root, text="Developed by @alexandreguerrra", fg="blue", cursor="hand2", font=("Arial", 8)).pack(side="bottom", pady=10)

        self.load_data()
        self.update_ui()
        threading.Thread(target=self.create_tray, daemon=True).start()
        self.root.mainloop()

    def update_ui(self, *args):
        l = LANGUAGES[self.lang_var.get()]
        self.l_lbl.config(text=l["lang_label"])
        self.title_lbl.config(text=l["title"])
        self.c_btn.config(text=l["color_btn"])
        self.txt_lbl.config(text=l["text_label"])
        self.sz_lbl.config(text=l["size_label"])
        self.dur_lbl.config(text=l["repeat_label"])
        self.launch_btn.config(text=l["launch_btn"])
        self.water_btn.config(text=l["water_btn"])
        self.m_lbl.config(text=l["manage_label"])
        self.update_list()

    def pick_color(self):
        c = colorchooser.askcolor()[1]
        if c: self.selected_color = c; self.c_prev.config(bg=c)

    def add_water(self):
        l = LANGUAGES[self.lang_var.get()]
        self.add_note(text=l["water_text"], color="#0000ff", dur=30, sz=250, is_w=True)

    def add_note(self, text=None, color=None, start=None, dur=None, sz=None, is_w=False, save=True):
        if text is None: text = self.entry.get() or "Note"
        if dur is None:
            try: dur = int(self.dur_entry.get())
            except: dur = 0
        if sz is None: sz = self.size_var.get()
        n = PostItBall(self.root, text, color or self.selected_color, self, start, dur, sz, is_w)
        self.notes.append(n)
        if save: self.save_data()
        self.update_list()

    def save_data(self):
        data = { "lang": self.lang_var.get(), "notes": [{"text": n.text, "color": n.color, "start": n.start_time, "dur": n.duration_min, "size": n.size, "w": n.is_water} for n in self.notes] }
        with open(SAVE_FILE, 'w', encoding='utf-8') as f: json.dump(data, f)

    def load_data(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                    c = json.load(f)
                    self.lang_var.set(c.get("lang", "pt-BR"))
                    for i in c.get("notes", []): self.add_note(i['text'], i['color'], i['start'], i['dur'], i['size'], i['w'], save=False)
            except: pass

    def remove_note(self, obj):
        if obj in self.notes: self.notes.remove(obj); self.save_data(); self.update_list()

    def update_list(self):
        l = LANGUAGES[self.lang_var.get()]
        for w in self.list_frame.winfo_children(): w.destroy()
        for n in self.notes:
            f = tk.Frame(self.list_frame); f.pack(fill="x", pady=1)
            tk.Label(f, text=f"{n.text[:12]} ({n.duration_min}m)", bg=n.color, width=22, anchor="w").pack(side="left")
            tk.Button(f, text=l["delete_btn"], bg="#ffcccc", command=lambda x=n: x.close_note()).pack(side="right")

    def hide_window(self): self.root.withdraw()
    def show_window(self): self.root.after(0, self.root.deiconify)
    def create_tray(self):
        img = Image.new('RGB', (64, 64), 'yellow')
        draw = ImageDraw.Draw(img); draw.ellipse([10, 10, 54, 54], fill="yellow")
        Icon("Dodoit", img, "Dodoit", Menu(MenuItem('Open', self.show_window), MenuItem('Exit', lambda i: self.root.quit()))).run()

if __name__ == "__main__":
    AppManager()
