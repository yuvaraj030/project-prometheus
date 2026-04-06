
import sys
import os
import tkinter as tk
import threading
import time

# Pillow for JPG/JPEG support (PhotoImage only handles PNG/GIF)
try:
    from PIL import Image, ImageTk, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    from tkinter import PhotoImage

class AvatarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Digital Avatar")
        
        # Frameless and Always on Top
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        
        # Transparency (using black as key)
        self.root.wm_attributes("-transparentcolor", "black")
        self.root.configure(bg="black")
        
        # Avatar size
        self.avatar_size = (300, 400)
        
        # Load Images
        self.mode = "standard"
        try:
            if PIL_AVAILABLE:
                # === NEW: High-quality avatar (JPG/PNG via Pillow) ===
                if os.path.exists("avatar_idle.jpg"):
                    self._load_pil_avatar("avatar_idle.jpg")
                    self.mode = "sovereign"
                elif os.path.exists("anime_idle.png"):
                    self._load_anime_assets()
                    self.mode = "anime"
                elif os.path.exists("avatar_idle.png"):
                    self._load_orb_assets_pil()
                    self.mode = "orb"
                else:
                    raise FileNotFoundError("No avatar assets found")
            else:
                # Fallback: Tkinter PhotoImage (PNG only)
                if os.path.exists("anime_idle.png"):
                    self.img_idle = PhotoImage(file="anime_idle.png")
                    self.img_talking_1 = PhotoImage(file="anime_talking_1.png")
                    self.img_talking_2 = PhotoImage(file="anime_talking_2.png")
                    self.img_thinking = PhotoImage(file="anime_thinking.png")
                    self.mode = "anime"
                elif os.path.exists("avatar_idle.png"):
                    self.img_idle = PhotoImage(file="avatar_idle.png")
                    self.img_active = PhotoImage(file="avatar_active.png")
                    self.mode = "orb"
                else:
                    raise FileNotFoundError("No avatar assets found")
        except Exception as e:
            print(f"Error loading images: {e}")
            sys.exit(1)
            
        self.label = tk.Label(root, image=self.img_idle, bg="black", bd=0)
        self.label.pack()
        
        # Position bottom-right
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        w, h = self.avatar_size
        self.root.geometry(f"{w}x{h}+{screen_width - w - 50}+{screen_height - h - 50}")
        
        # Dragging
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        
        # Context Menu
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Disconnect Avatar", command=self.root.quit)
        self.root.bind("<Button-3>", self.show_menu)
        
        # Animation State
        self.current_state = "idle"
        self.animation_frame = 0
        self.glow_phase = 0.0
        self.animate()

        # Start input listener
        self.listener_thread = threading.Thread(target=self.listen_stdin, daemon=True)
        self.listener_thread.start()

    def _load_pil_avatar(self, path):
        """Load the high-quality sovereign avatar with state variations generated via Pillow."""
        img = Image.open(path).convert("RGBA")
        img = img.resize(self.avatar_size, Image.LANCZOS)
        
        # Idle state — base image
        self.pil_idle = img.copy()
        self.img_idle = ImageTk.PhotoImage(self.pil_idle)
        
        # Active/Thinking state — slight blue-purple tint + brightness boost
        enhancer = ImageEnhance.Brightness(img)
        bright = enhancer.enhance(1.15)
        enhancer2 = ImageEnhance.Color(bright)
        active = enhancer2.enhance(1.3)
        self.pil_active = active
        self.img_active = ImageTk.PhotoImage(self.pil_active)
        
        # Talking state 1 — warm glow
        enhancer = ImageEnhance.Brightness(img)
        talk1 = enhancer.enhance(1.2)
        enhancer2 = ImageEnhance.Color(talk1)
        self.pil_talking_1 = enhancer2.enhance(1.4)
        self.img_talking_1 = ImageTk.PhotoImage(self.pil_talking_1)
        
        # Talking state 2 — slightly dimmer (creates pulse effect)
        enhancer = ImageEnhance.Brightness(img)
        talk2 = enhancer.enhance(1.05)
        self.pil_talking_2 = talk2
        self.img_talking_2 = ImageTk.PhotoImage(self.pil_talking_2)
        
        # Thinking state
        self.pil_thinking = self.pil_active
        self.img_thinking = self.img_active

    def _load_anime_assets(self):
        """Load anime PNG assets via Pillow."""
        self.avatar_size = (300, 400)
        self.img_idle = ImageTk.PhotoImage(Image.open("anime_idle.png").resize(self.avatar_size, Image.LANCZOS))
        self.img_talking_1 = ImageTk.PhotoImage(Image.open("anime_talking_1.png").resize(self.avatar_size, Image.LANCZOS))
        self.img_talking_2 = ImageTk.PhotoImage(Image.open("anime_talking_2.png").resize(self.avatar_size, Image.LANCZOS))
        self.img_thinking = ImageTk.PhotoImage(Image.open("anime_thinking.png").resize(self.avatar_size, Image.LANCZOS))

    def _load_orb_assets_pil(self):
        """Load simple orb PNG assets via Pillow."""
        self.avatar_size = (200, 200)
        self.img_idle = ImageTk.PhotoImage(Image.open("avatar_idle.png").resize(self.avatar_size, Image.LANCZOS))
        self.img_active = ImageTk.PhotoImage(Image.open("avatar_active.png").resize(self.avatar_size, Image.LANCZOS))

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def set_state(self, state):
        self.current_state = state
        if state == "idle":
            self.label.configure(image=self.img_idle)
        elif state == "thinking" or state == "active":
            if hasattr(self, 'img_thinking'):
                self.label.configure(image=self.img_thinking)
            elif hasattr(self, 'img_active'):
                self.label.configure(image=self.img_active)
        elif state == "quit":
            self.root.quit()

    def animate(self):
        """Handle looping animations (talking) and sovereign glow pulse."""
        if self.current_state == "talking":
            self.animation_frame = (self.animation_frame + 1) % 2
            if hasattr(self, 'img_talking_1'):
                if self.animation_frame == 0:
                    self.label.configure(image=self.img_talking_1)
                else:
                    self.label.configure(image=self.img_talking_2)
        
        # Sovereign mode: subtle glow pulse when idle
        if self.mode == "sovereign" and self.current_state == "idle" and PIL_AVAILABLE:
            self.glow_phase += 0.05
            # Subtle brightness oscillation (0.97 — 1.03)
            factor = 1.0 + 0.03 * (0.5 + 0.5 * __import__('math').sin(self.glow_phase))
            try:
                enhanced = ImageEnhance.Brightness(self.pil_idle).enhance(factor)
                self._pulse_img = ImageTk.PhotoImage(enhanced)
                self.label.configure(image=self._pulse_img)
            except:
                pass
        
        self.root.after(200, self.animate)

    def listen_stdin(self):
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                cmd = line.strip()
                if cmd:
                    self.root.after(0, self.set_state, cmd)
            except:
                break

if __name__ == "__main__":
    root = tk.Tk()
    app = AvatarApp(root)
    root.mainloop()
