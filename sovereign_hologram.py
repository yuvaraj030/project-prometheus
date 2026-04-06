"""
Sovereign Hologram Interface — 3D Holographic HUD.
Extracted from ultimate_agent.py for modularity.
"""

import math
import random
import asyncio
import queue

try:
    import tkinter as tk
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False


class SovereignHologram:
    def __init__(self, agent):
        self.agent = agent
        self.root = None
        self.canvas = None
        
        # UI Colors (JARVIS Theme)
        self.bg_color = "#000814" # Near Black
        self.color_idle = "#00FFFF"  # JARVIS Cyan
        self.color_thinking = "#FF3131" # Bright Red
        self.color_god = "#FFD700" # Gold
        
        self.accent_color = self.color_idle
        self.core_color = "#FFD700" # Gold
        
        # Runtime Overrides
        self.speed_mult = 1.0
        self.segments = 12 # Higher density for JARVIS
        self.msg_queue = queue.Queue()
        self.mode = "sphere" # sphere, avatar
        
    def update_params(self, **kwargs):
        """Thread-safe update request."""
        self.msg_queue.put({"type": "params", "data": kwargs})

    def _apply_params(self, color=None, speed=None, density=None, mode=None):
        """Internal update application (Must run in UI thread)."""
        if color:
            self.color_idle = color
            self.accent_color = color
        if speed is not None:
            self.speed_mult = speed
        if mode:
            self.mode = mode
            self.canvas.delete("all")
            # Scanlines (Stationary background decoration) re-add
            w, h = int(self.canvas['width']), int(self.canvas['height'])
            for i in range(0, h, 4):
                self.canvas.create_line(0, i, w, i, fill="#001a33", stipple="gray25")
            self._init_geometry()
            return # _init_geometry handles the rest

        if density is not None:
            self.segments = max(3, min(20, density))
            # Re-init geometry on next frame logic or immediate
            self.canvas.delete("all")
            self._init_geometry()
            # Restore labels/UI
            self.log_label = tk.Label(self.root, text="SYSTEM UPDATED", font=("Consolas", 10), 
                                      fg=self.accent_color, bg=self.bg_color, wraplength=300)
            self.canvas.create_window(self.cx, self.cy + 160, window=self.log_label)
            self.entry = tk.Entry(self.root, bg="black", fg=self.core_color, font=("Consolas", 12), highlightthickness=0, relief="flat")
            self.canvas.create_window(self.cx, self.cy + 200, window=self.entry, width=300)
            self.entry.bind("<Return>", self.on_enter)
        
    def run(self):
        if not TK_AVAILABLE:
            return
            
        self.root = tk.Tk()
        self.root.title("Sovereign HUD")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", self.bg_color)
        self.root.config(bg=self.bg_color)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w, h = 400, 500
        self.root.geometry(f"{w}x{h}+{screen_w-w-50}+{screen_h-h-50}")

        self.canvas = tk.Canvas(self.root, width=w, height=h, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack()

        self.cx, self.cy = w//2, h//2 - 50
        self.radius = 120
        self.angle = 0
        
        # Scanlines (Stationary background decoration)
        for i in range(0, h, 4):
            self.canvas.create_line(0, i, w, i, fill="#001a33", stipple="gray25")
        self.radius = 120
        self.angle = 0
        self.particles_3d = []
        self.labels_3d = [
            {"text": "SOVEREIGN", "p": [1.5, 0, 0]},
            {"text": "ANALYZING", "p": [-1.5, 0.5, 0]},
            {"text": "LINKED", "p": [0, -1.5, 0.5]}
        ]
        
        self._init_geometry()
        
        self.log_label = tk.Label(self.root, text="LINK ESTABLISHED", font=("Consolas", 10), 
                                  fg=self.accent_color, bg=self.bg_color, wraplength=300)
        self.canvas.create_window(self.cx, self.cy + 160, window=self.log_label)

        self.entry = tk.Entry(self.root, bg="black", fg=self.core_color, font=("Consolas", 12), highlightthickness=0, relief="flat")
        self.canvas.create_window(self.cx, self.cy + 200, window=self.entry, width=300)
        self.entry.bind("<Return>", self.on_enter)
        
        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.do_drag)
        self.root.bind("<Button-3>", lambda e: self.root.destroy())

        self.animate()
        self.process_queue()
        self.root.mainloop()

    def _init_geometry(self):
        if self.mode == "avatar":
            self._init_avatar()
        else:
            self._init_sphere()

        self.log_label = tk.Label(self.root, text="LINK ESTABLISHED", font=("Consolas", 10), 
                                  fg=self.accent_color, bg=self.bg_color, wraplength=300)
        self.canvas.create_window(self.cx, self.cy + 160, window=self.log_label)

        self.entry = tk.Entry(self.root, bg="black", fg=self.core_color, font=("Consolas", 12), highlightthickness=0, relief="flat")
        self.canvas.create_window(self.cx, self.cy + 200, window=self.entry, width=300)
        self.entry.bind("<Return>", self.on_enter)

    def _init_avatar(self):
        # Construct Wireframe Humanoid
        self.points_3d = []
        # Head
        for i in range(3):
            lat = math.pi * i / 3
            for j in range(6):
                lon = 2 * math.pi * j / 6
                self.points_3d.append([0.3*math.sin(lat)*math.cos(lon), 0.3*math.sin(lat)*math.sin(lon) - 0.8, 0.3*math.cos(lat)])
        
        # Torso (Ribs)
        for y in [-0.5, -0.2, 0.1, 0.4]:
            r = 0.4 - abs(y)*0.2
            for j in range(8):
                 ang = 2 * math.pi * j / 8
                 self.points_3d.append([r*math.cos(ang), y, r*math.sin(ang)])
        
        # Limbs (Simple lines)
        # Shoulders
        self.points_3d.append([-0.5, -0.6, 0])
        self.points_3d.append([0.5, -0.6, 0])
        # Arms
        self.points_3d.append([-0.7, 0, 0])
        self.points_3d.append([0.7, 0, 0])
        # Hips
        self.points_3d.append([-0.3, 0.6, 0])
        self.points_3d.append([0.3, 0.6, 0])
        # Legs
        self.points_3d.append([-0.4, 1.5, 0])
        self.points_3d.append([0.4, 1.5, 0])

        # Init projection items
        self.projected_items = [self.canvas.create_oval(0,0,0,0, fill=self.accent_color, outline="") for _ in self.points_3d]
        
        # Manual connections for limbs
        self.web_lines = []
        for i in range(len(self.points_3d)):
            for j in range(i+1, len(self.points_3d)):
                dist = math.sqrt(sum((self.points_3d[i][k]-self.points_3d[j][k])**2 for k in range(3)))
                if dist < 0.4: # Tighter connections for body
                     line = self.canvas.create_line(0,0,0,0, fill=self.accent_color, stipple="gray25", width=1)
                     self.web_lines.append((line, i, j))

        # Avatar specific rings (Halo)
        self.rings = []
        ring_items = []
        for s in range(12):
             line = self.canvas.create_line(0,0,0,0, fill=self.color_god, width=1)
             ring_items.append(line)
        self.rings.append({"items": ring_items, "radius": 0.5, "segments": 12, "speed": 0.5, "y_off": -0.9}) # Halo

        self.panels = [] # No panels in avatar mode
        self.core_layers = [] # No core in avatar mode

    def _init_sphere(self):
        # 1. Neural Web (Sphere)
        self.points_3d = []
        segments = self.segments 
        for i in range(segments):
            lat = math.pi * i / segments
            for j in range(segments * 2):
                lon = 2 * math.pi * j / (segments * 2)
                x = math.sin(lat) * math.cos(lon)
                y = math.sin(lat) * math.sin(lon)
                z = math.cos(lat)
                self.points_3d.append([x, y, z])
        
        self.web_lines = []
        for i in range(len(self.points_3d)):
            if i % 2 != 0: continue # Skip half the points for connection density
            for j in range(i+1, len(self.points_3d)):
                if j % 3 != 0: continue # Further prune connections
                dist = math.sqrt(sum((self.points_3d[i][k]-self.points_3d[j][k])**2 for k in range(3)))
                if dist < 0.6:
                    line = self.canvas.create_line(0,0,0,0, fill=self.accent_color, stipple="gray25", width=1)
                    self.web_lines.append((line, i, j))

        self.projected_items = [self.canvas.create_oval(0,0,0,0, fill=self.accent_color, outline="") for _ in self.points_3d]

        # 2. JARVIS Rings (Concentric Segmented Rings)
        self.rings = []
        for r in [1.3, 1.6, 2.0]:
            ring_items = []
            num_segments = 24
            for s in range(num_segments):
                line = self.canvas.create_line(0,0,0,0, fill=self.color_idle, width=2)
                ring_items.append(line)
            self.rings.append({"items": ring_items, "radius": r, "segments": num_segments, "speed": random.uniform(0.5, 2.0)})

        # 3. Floating Data Panels
        self.panels = []
        for _ in range(5):
            panel = self.canvas.create_rectangle(0,0,0,0, outline=self.color_idle, fill=self.bg_color, stipple="gray25")
            text = self.canvas.create_text(0,0, text="DATA_LINK", fill=self.color_idle, font=("Consolas", 6))
            p_pos = [random.uniform(-2.5, 2.5), random.uniform(-2, 2), random.uniform(-2, 2)]
            self.panels.append({"rect": panel, "text": text, "pos": p_pos})

        # 4. Multi-layered Core Glow
        self.core_layers = []
        for i in range(4):
            c = self.canvas.create_oval(0,0,0,0, outline=self.core_color if i==0 else self.accent_color, width=1)
            self.core_layers.append(c)

        self.label_items = [self.canvas.create_text(0, 0, text=l["text"], font=("Consolas", 8, "bold"), fill=self.accent_color) for l in self.labels_3d]

    def project(self, x, y, z, angle_x, angle_y):
        # Rotation X
        rad_x = angle_x
        ny = y * math.cos(rad_x) - z * math.sin(rad_x)
        nz = y * math.sin(rad_x) + z * math.cos(rad_x)
        y, z = ny, nz
        # Rotation Y
        rad_y = angle_y
        nx = x * math.cos(rad_y) + z * math.sin(rad_y)
        nz = -x * math.sin(rad_y) + z * math.cos(rad_y)
        x, z = nx, nz
        
        # Perspective Projection
        fov = 250
        dist = 3 # Distance from viewer
        factor = fov / (dist + z)
        px = x * factor + self.cx
        py = y * factor + self.cy
        return px, py, z

    def animate(self):
        # 0. Process Message Queue (Thread Safety)
        self.process_queue()
        
        state = self.agent.status
        self.angle += (0.04 if state == "IDLE" else 0.1) * self.speed_mult
        
        # Subtle Flicker
        if random.random() < 0.01:
            self.canvas.itemconfig("all", state="hidden")
            self.root.after(20, lambda: self.canvas.itemconfig("all", state="normal"))
            return self.root.after(30, self.animate)
        
        pulse_val = 1.0 + 0.1 * math.sin(self.angle * 1.5)
        if state == "THINKING":
            pulse_val += 0.2 * math.sin(self.angle * 15)
            target_color = self.color_thinking
        elif state == "GODMODE":
            pulse_val += 0.1
            target_color = self.color_god
        else:
            target_color = self.color_idle
        
        self.accent_color = target_color
        ax, ay = self.angle * 0.4, self.angle * 0.7
        
        # 1. Project Neural Web (Sphere or Avatar)
        proj_pts = []
        for i, p in enumerate(self.points_3d):
            scale = pulse_val
            if self.mode == "avatar":
                 y_off = 0.1 * math.sin(self.angle * 2)
                 if i < 40:
                     scale = 1.0 + 0.05 * math.sin(self.angle * 3)
                 else:
                     scale = 1.0
                 px, py, z = self.project(p[0] * scale, p[1] * scale + y_off, p[2] * scale, ax, ay)
            else:
                 px, py, z = self.project(p[0] * scale, p[1] * scale, p[2] * scale, ax, ay)
            
            proj_pts.append((px, py, z))

        for line, i, j in self.web_lines:
            p1, p2 = proj_pts[i], proj_pts[j]
            cull_z = -0.5 if self.mode == "avatar" else -0.2
            if p1[2] < cull_z and p2[2] < cull_z:
                self.canvas.itemconfig(line, state="hidden")
                continue
            self.canvas.itemconfig(line, state="normal")
            self.canvas.coords(line, p1[0], p1[1], p2[0], p2[1])

        for i, (px, py, z) in enumerate(proj_pts):
            if z < -0.4 and self.mode == "sphere":
                self.canvas.itemconfig(self.projected_items[i], state="hidden")
                continue
            self.canvas.itemconfig(self.projected_items[i], state="normal")
            size = 1 if z < 0 else 2
            self.canvas.coords(self.projected_items[i], px-size, py-size, px+size, py+size)

        # 2. Animate Rings
        for ri, ring in enumerate(self.rings):
            ra = self.angle * ring["speed"]
            y_offset = ring.get("y_off", 0)
            pts = []
            for s in range(ring["segments"]):
                ang = ra + (s * (2 * math.pi / ring["segments"]))
                rx = math.cos(ang) * ring["radius"]
                ry = math.sin(ang) * ring["radius"]
                if self.mode == "avatar":
                    px, py, z = self.project(rx, y_offset, ry, ax*0.1, ay*0.1)
                else:
                    px, py, z = self.project(rx, ry, math.sin(ra/2)*0.5, ax*0.3, ay*0.3)
                pts.append((px, py, z))
            
            for s in range(ring["segments"]):
                p1, p2 = pts[s], pts[(s+1)%ring["segments"]]
                if s % 3 == 0: 
                    self.canvas.itemconfig(ring["items"][s], state="hidden")
                    continue
                self.canvas.itemconfig(ring["items"][s], state="normal", fill=target_color)
                self.canvas.coords(ring["items"][s], p1[0], p1[1], p2[0], p2[1])

        # 3. Animate Panels (Staggered Update) - Skip in Avatar Mode
        if self.mode == "sphere" and int(self.angle * 10) % 2 == 0:
            for p in self.panels:
                px, py, z = self.project(p["pos"][0], p["pos"][1], p["pos"][2], ax*0.5, ay*0.5)
                w, h = 40, 20
                self.canvas.coords(p["rect"], px-w/2, py-h/2, px+w/2, py+h/2)
                self.canvas.coords(p["text"], px, py)
                self.canvas.itemconfig(p["rect"], outline=target_color)
                self.canvas.itemconfig(p["text"], fill=target_color, text=f"SYS_{random.randint(10,99)}")

        # 4. Multi-layered Core Pulse - Skip in Avatar Mode
        if self.mode == "sphere":
            for i, layer in enumerate(self.core_layers):
                cp = (15 + i*8) + (5 * math.sin(self.angle * (3+i)))
                self.canvas.coords(layer, self.cx-cp, self.cy-cp, self.cx+cp, self.cy+cp)
                self.canvas.itemconfig(layer, outline=target_color)

        # 5. Labels - Update positions
        for i, l in enumerate(self.labels_3d):
             px, py, z = self.project(l["p"][0] * 1.8, l["p"][1] * 1.8, l["p"][2] * 1.8, ax, ay)
             if z > -0.5:
                 self.canvas.itemconfig(self.label_items[i], state="normal", fill=target_color)
                 self.canvas.coords(self.label_items[i], px, py)
             else:
                 self.canvas.itemconfig(self.label_items[i], state="hidden")

        self.root.after(30, self.animate)

    def update_log(self, text):
        """Thread-safe log update."""
        self.msg_queue.put({"type": "log", "text": text})

    def process_queue(self):
        """Poll the message queue and update the UI (Main Thread Only)."""
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                
                if isinstance(msg, dict):
                    if msg.get("type") == "log":
                        text = msg.get("text", "")
                        if self.log_label:
                            self.log_label.config(text=text[:100])
                    elif msg.get("type") == "params":
                        data = msg.get("data", {})
                        self._apply_params(**data)
                elif isinstance(msg, str):
                    # Legacy support
                    if self.log_label:
                        self.log_label.config(text=msg[:100])
                        
        except queue.Empty:
            pass
        if self.root:
            self.root.after(100, self.process_queue)

    def on_enter(self, e):
        text = self.entry.get()
        self.entry.delete(0, tk.END)
        if text:
            # Route to agent
            async def _proc():
                if text.startswith("/"):
                    await self.agent.handle_command(text)
                else:
                    resp = await self.agent.think(text)
                    self.agent.speak(resp)
                    self.agent._save_turn(text, resp)
            asyncio.run_coroutine_threadsafe(_proc(), self.agent.loop)

    def start_drag(self, e):
        self.x, self.y = e.x, e.y
    def do_drag(self, e):
        self.root.geometry(f"+{self.root.winfo_x()+(e.x-self.x)}+{self.root.winfo_y()+(e.y-self.y)}")
