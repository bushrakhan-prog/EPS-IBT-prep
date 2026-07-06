"""
IBT Portal — Standalone Launcher
Run this file directly: python launcher.py
Or build into .exe: python build_exe.py

This file handles:
- Starting Flask in a background thread
- Opening the browser automatically
- Showing a system tray icon (optional)
- Clean shutdown on window close
"""

import sys
import os
import threading
import webbrowser
import time
import tkinter as tk
from tkinter import messagebox

# ── Path fix for PyInstaller ──────────────────────────────────────────────────
# When built as .exe, files are in a temp folder (_MEIPASS)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    # Also set working dir so database.db is saved next to the .exe
    os.chdir(os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(BASE_DIR)

# Add base dir to path so app.py can find templates/static
sys.path.insert(0, BASE_DIR)

# ── Import Flask app ──────────────────────────────────────────────────────────
from app import app, db, seed_db

PORT = 5000
URL  = f"http://localhost:{PORT}"

def run_flask():
    with app.app_context():
        db.create_all()
        seed_db()
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

def open_browser():
    time.sleep(1.5)
    webbrowser.open(URL)

# ── Tkinter control window ────────────────────────────────────────────────────
def launch_gui():
    root = tk.Tk()
    root.title("IBT Portal")
    root.geometry("380x220")
    root.resizable(False, False)
    root.configure(bg="#0f172a")

    # Center on screen
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    x = (root.winfo_screenwidth()  // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"+{x}+{y}")

    tk.Label(root, text="🎯 IBT Prep Portal", font=("Segoe UI", 16, "bold"),
             bg="#0f172a", fg="#ffffff").pack(pady=(24,4))

    tk.Label(root, text="School Preparation System is running",
             font=("Segoe UI", 9), bg="#0f172a", fg="#94a3b8").pack()

    status = tk.Label(root, text="⏳ Starting server...",
                      font=("Segoe UI", 9), bg="#0f172a", fg="#f59e0b")
    status.pack(pady=(14,0))

    url_label = tk.Label(root, text=URL, font=("Segoe UI", 10, "underline"),
                         bg="#0f172a", fg="#818cf8", cursor="hand2")
    url_label.pack(pady=(4,0))
    url_label.bind("<Button-1>", lambda e: webbrowser.open(URL))

    def open_btn():
        webbrowser.open(URL)

    def stop_btn():
        if messagebox.askokcancel("Stop Portal", "Are you sure you want to stop the IBT Portal?\n\nAll users will be disconnected."):
            root.destroy()
            os._exit(0)

    btn_frame = tk.Frame(root, bg="#0f172a")
    btn_frame.pack(pady=16)

    tk.Button(btn_frame, text="Open in Browser", command=open_btn,
              font=("Segoe UI", 9, "bold"), bg="#4f46e5", fg="white",
              relief="flat", padx=14, pady=6, cursor="hand2").pack(side="left", padx=6)

    tk.Button(btn_frame, text="Stop Portal", command=stop_btn,
              font=("Segoe UI", 9), bg="#1e293b", fg="#94a3b8",
              relief="flat", padx=14, pady=6, cursor="hand2").pack(side="left", padx=6)

    def update_status():
        status.config(text=f"✅ Running at {URL}", fg="#10b981")

    root.after(2000, update_status)
    root.protocol("WM_DELETE_WINDOW", stop_btn)
    root.mainloop()

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Open browser
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Show control window
    launch_gui()
