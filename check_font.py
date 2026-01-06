from tkinter import Tk, font
import os
from ctypes import windll

# 加载字体
font_path = os.path.abspath("font/SmileySans-Oblique.ttf")
FR_PRIVATE = 0x10
windll.gdi32.AddFontResourceExW(font_path, FR_PRIVATE, 0)

# 启动 Tkinter 并列出所有字体
root = Tk()
families = font.families()
print("Available Fonts:", families)

# 简单的过滤
for f in families:
    if "Smiley" in f or "得意" in f:
        print(f"FOUND: {f}")

root.destroy()
