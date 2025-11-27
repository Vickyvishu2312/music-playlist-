import tkinter as tk
import os
from database import init_db, load_all_playlists, save_all_playlists
from player import MusicPlayer
from gui import GUIManager

def ensure_directories():
    base = os.path.dirname(os.path.dirname(__file__))
    for folder in ["songs", "assets", "database"]:
        os.makedirs(os.path.join(base, folder), exist_ok=True)

def main():
    ensure_directories()
    init_db()

    pm = load_all_playlists()  # PlaylistManager with all playlists
    player = MusicPlayer()

    root = tk.Tk()
    app = GUIManager(root, pm, player, db_save_callback=save_all_playlists)
    root.mainloop()

if __name__ == "__main__":
    main()
