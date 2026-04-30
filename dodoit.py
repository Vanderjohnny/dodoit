import tkinter as tk
from tkinter import colorchooser
import threading, json, os, time, webbrowser, random, math, ctypes
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

def get_virtual_desktop_size():
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(78), user32.GetSystemMetrics(79), user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)

SAVE_FILE = os.path.join(os.environ['APPDATA'], 'dodoit_v3_final.json')

LANGUAGES = {
    "pt-BR": {
        "title": "Nova Nota", "color_btn": "Cor", "text_label": "Texto:",
        "size_label": "Tam:", "repeat_label": "Duração (minutos):",
        "launch_btn": "Lançar Nota", "water_btn": "💧 ÁGUA (30min)",
        "manage_label": "Ativas/Agendadas:", "delete_btn": "Deletar",
        "water_text": "BEBER ÁGUA! 💧", "lang_label": "Idioma:"
    },
    "EN": {
        "title": "New Note", "color_btn": "Color", "text_label": "Text:",
        "size_label": "Size:", "repeat_label": "Duration (min):",
        "launch_btn": "Launch Note", "water_btn": "💧 WATER (30min)",
        "manage_label": "Active Tasks:", "delete_btn": "Delete",
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
        self.is_exploding = False
        self.is_sleeping = False
        
        self.expiry_time = self.start_time + (duration_min * 60) if duration_min > 0 else None
        self.vw, self.vh, self.vl, self.vt = get_virtual_desktop_size()

        self.overrideredirect(True)
        self.attributes("-topmost", True, "-alpha", 0.9, "-transparentcolor", "grey")
        
        self.x = random.randint(self.vl, self.vl + self.vw - self.size)
        self.y = random.randint(self.vt, self.vt + self.vh - self.size)
        self.geometry(f"{self.size}x{self.size}+{int(self.x)}+{int(self.y)}")

        self.canvas = tk.Canvas(self, width=self.size, height=self.size, bg="grey", highlightthickness=0)
        self.canvas.pack()
        self.circle = self.canvas.create_oval(5, 5, self.size-5, self.size-5, fill=color, outline="", width=0)
        
        f_sz = 8 if self.size <= 100 else (12 if self.size <= 150 else 16)
        self.label = tk.Label(self.canvas, text=text, bg=color, wraplength=self.size-20, font=("Arial", f_sz, "bold"))
        self.label.place(relx=0.5, rely=0.4, anchor="center")
        
        self.btn_x = tk.Button(self.canvas, text="✕", command=self.handle_close, font=("Arial", f_sz-2), bg="#ffcccc", relief="flat")
        self.btn_x.place(relx=0.5, rely=0.75, anchor="center")

        self.bind("<Enter>", lambda e: setattr(self, 'paused', True))
        self.bind("<Leave>", lambda e: setattr(self, 'paused', False))

        self.dx, self.dy = random.choice([4, -4]), random.choice([4, -4])
        self.particles = []
        self.animate()

    def animate(self):
        try:
            if self.is_exploding:
                self.animate_explosion()
                return

            now = time.time()
            
            # Reforço para ficar sempre em cima
            self.lift()
            self.attributes("-topmost", True)

            # Lógica de Expiração / Dormir (Água)
            if self.expiry_time and now >= self.expiry_time:
                if self.is_water:
                    self.is_sleeping = True
                    self.withdraw()
                    # Define próxima aparição
                    self.start_time = now + (self.duration_min * 60)
                    self.expiry_time = self.start_time + (self.duration_min * 60)
                else:
                    self.start_explosion()
                    return

            # Acordar (Água)
            if self.is_sleeping and now >= self.start_time:
                self.is_sleeping = False
                self.deiconify()

            if not self.is_sleeping and not self.paused:
                self.x += self.dx
                self.y += self.dy
                if self.x + self.size >= self.vl + self.vw or self.x <= self.vl: self.dx *= -1
                if self.y + self.size >= self.vt + self.vh or self.y <= self.vt: self.dy *= -1
                self.geometry(f"+{int(self.x)}+{int(self.y)}")
            
            self.after(20, self.animate)
        except: pass

    def start_explosion(self):
        self.is_exploding = True
        self.canvas.itemconfig(self.circle, state='hidden')
        self.label.place_forget()
        self.btn_x.place_forget()
        for _ in range(20):
            p_id = self.canvas.create_oval(self.size/2, self.size/2, self.size/2+5, self.size/2+5, fill=self.color, outline="")
            angle = random.uniform(0, 2*math.pi)
            speed = random.uniform(2, 7)
            self.particles.append({'id': p_id, 'dx': math.cos(angle)*speed, 'dy': math.sin(angle)*speed, 'life': 1.0})
        self.animate_explosion()

    def animate_explosion(self):
        active = False
        for p in self.particles:
            if p['life'] > 0:
                active = True
                self.canvas.move(p['id'], p['dx'], p['dy'])
                p['life'] -= 0.05
                if p['life'] <= 0: self.canvas.delete(p['id'])
        if active: self.after(30, self.animate_explosion)
        else: self.destroy_and_remove()

    def handle_close(self):
        if self.is_water:
            self.expiry_time = time.time() # Força dormir agora
        else:
            self.destroy_and_remove()

    def destroy_and_remove(self):
        self.manager.remove_note(self)
        self.destroy()

class AppManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dodoit V3 Pro")
        self.root.geometry("380x700")
        self.notes = []
        self.selected_color = "#ffff88"
        self.size_var = tk.IntVar(value=100)
        self.lang_var = tk.StringVar(value="pt-BR")
        self.root.protocol('WM_DELETE_WINDOW', self.root.withdraw)

        # UI
        l_fr = tk.Frame(self.root); l_fr.pack(pady=5)
        self.l_l = tk.Label(l_fr); self.l_l.pack(side="left")
        self.l_m = tk.OptionMenu(l_fr, self.lang_var, *LANGUAGES.keys(), command=self.update_ui); self.l_m.pack(side="left")

        self.t_l = tk.Label(self.root, font=("Arial", 10, "bold")); self.t_l.pack()
        self.c_btn = tk.Button(self.root, command=self.pick_color); self.c_btn.pack(pady=5)
        self.entry = tk.Entry(self.root, width=30); self.entry.pack()

        self.sz_l = tk.Label(self.root); self.sz_l.pack()
        f_sz = tk.Frame(self.root); f_sz.pack()
        for s in [("P", 100), ("M", 150), ("G", 200)]: tk.Radiobutton(f_sz, text=s[0], variable=self.size_var, value=s[1]).pack(side="left")

        self.d_l = tk.Label(self.root); self.d_l.pack()
        self.d_e = tk.Entry(self.root, width=10); self.d_e.insert(0, "0"); self.d_e.pack()

        self.ln_b = tk.Button(self.root, command=self.add_note, bg="#ccffcc"); self.ln_b.pack(pady=10)
        self.wt_b = tk.Button(self.root, command=self.add_water, bg="#add8e6"); self.wt_b.pack()

        self.m_l = tk.Label(self.root, font=("Arial", 10, "bold")); self.m_l.pack(pady=10)
        self.list_frame = tk.Frame(self.root); self.list_frame.pack(fill="both")

        self.load_data()
        self.update_ui()
        threading.Thread(target=self.create_tray, daemon=True).start()
        self.root.mainloop()

    def update_ui(self, *args):
        l = LANGUAGES[self.lang_var.get()]
        self.l_l.config(text=l["lang_label"])
        self.t_l.config(text=l["title"])
        self.c_btn.config(text=l["color_btn"])
        self.sz_l.config(text=l["size_label"])
        self.d_l.config(text=l["repeat_label"])
        self.ln_b.config(text=l["launch_btn"])
        self.wt_b.config(text=l["water_btn"])
        self.m_l.config(text=l["manage_label"])
        self.update_list()

    def pick_color(self):
        c = colorchooser.askcolor()[1]
        if c: self.selected_color = c

    def add_water(self):
        l = LANGUAGES[self.lang_var.get()]
        self.add_note(text=l["water_text"], color="#0000ff", dur=30, sz=250, is_w=True)

    def add_note(self, text=None, color=None, start=None, dur=None, sz=None, is_w=False, save=True):
        if text is None: text = self.entry.get() or "Nota"
        if dur is None:
            try: dur = int(self.d_e.get())
            except: dur = 0
        n = PostItBall(self.root, text, color or self.selected_color, self, start, dur, sz or self.size_var.get(), is_w)
        self.notes.append(n)
        if save: self.save_data()
        self.update_list()

    def save_data(self):
        data = {"lang": self.lang_var.get(), "notes": [{"text": n.text, "color": n.color, "start": n.start_time, "dur": n.duration_min, "sz": n.size, "w": n.is_water} for n in self.notes]}
        with open(SAVE_FILE, 'w', encoding='utf-8') as f: json.dump(data, f)

    def load_data(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                    c = json.load(f); self.lang_var.set(c.get("lang", "pt-BR"))
                    for i in c.get("notes", []): self.add_note(i['text'], i['color'], i['start'], i['dur'], i['sz'], i['w'], save=False)
            except: pass

    def remove_note(self, obj):
        if obj in self.notes: self.notes.remove(obj); self.save_data(); self.update_list()

    def update_list(self):
        l = LANGUAGES[self.lang_var.get()]
        for w in self.list_frame.winfo_children(): w.destroy()
        for n in self.notes:
            f = tk.Frame(self.list_frame); f.pack(fill="x")
            tk.Label(f, text=n.text[:15], bg=n.color, width=20).pack(side="left")
            tk.Button(f, text=l["delete_btn"], command=lambda x=n: x.destroy_and_remove()).pack(side="right")

    def create_tray(self):
        img = Image.new('RGB', (64, 64), 'yellow')
        Icon("Dodoit", img, "Dodoit", Menu(MenuItem('Abrir', lambda: self.root.deiconify()), MenuItem('Sair', lambda i: self.root.quit()))).run()

if __name__ == "__main__":
    AppManager()
