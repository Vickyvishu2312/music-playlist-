import os
import cv2
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
from playlist import PlaylistManager
from player import MusicPlayer
from utils import is_audio_file, pretty_title

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SONGS_DIR = os.path.join(BASE_DIR, "songs")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")


class VideoBackground:
    def __init__(self, canvas, video_path):
        self.canvas = canvas
        self.cap = cv2.VideoCapture(video_path)
        self.image_id = None
        self.update_frame()

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.resize(frame, (self.canvas.winfo_screenwidth(), self.canvas.winfo_screenheight()))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(Image.fromarray(frame))
            if self.image_id is None:
                self.image_id = self.canvas.create_image(0, 0, anchor="nw", image=img)
            else:
                self.canvas.itemconfig(self.image_id, image=img)
            self.canvas.image = img
        else:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.canvas.after(33, self.update_frame)


class GUIManager:
    def __init__(self, root: tk.Tk, pm: PlaylistManager, player: MusicPlayer, db_save_callback):
        self.root = root
        self.pm = pm
        self.player = player
        self.db_save = db_save_callback

        style = tb.Style("darkly")
        self.root = style.master
        self.root.title("Music Playlist Manager")
        self.root.state("zoomed")
        self.root.bind("<Escape>", lambda e: self.on_exit())

        # Canvas for background + widgets
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # Video background drawn on canvas
        video_path = os.path.join(ASSETS_DIR, "background.mp4")
        self.video_bg = VideoBackground(self.canvas, video_path)

        # Build layout
        self._build_layout()
        self._refresh_sidebar()
        self._refresh_song_list()

    def _build_layout(self):
        # Top bar
        self.top_bar = tb.Frame(self.root, padding=12)
        self.canvas.create_window(20, 20, anchor="nw", window=self.top_bar)
        tb.Label(self.top_bar, text="Playlists", font=("Segoe UI", 20)).pack(side="left")
        tb.Button(self.top_bar, text="Exit", bootstyle=DANGER, command=self.on_exit).pack(side="right")

        # Main area centered
        self.main_area = tb.Frame(self.root)
        self.canvas.create_window(
            self.root.winfo_screenwidth() // 2,
            self.root.winfo_screenheight() // 2,
            anchor="center",
            window=self.main_area
        )

        # Sidebar
        self.sidebar = tb.Frame(self.main_area, padding=8)
        self.sidebar.pack(side="left", fill="y")
        tb.Label(self.sidebar, text="Your Playlists", font=("Segoe UI", 14)).pack(anchor="w", pady=(0, 8))
        self.playlist_listbox = tk.Listbox(self.sidebar, height=18, font=("Segoe UI", 12))
        self.playlist_listbox.pack(fill="y", padx=4, pady=4)
        self.playlist_listbox.bind("<<ListboxSelect>>", lambda e: self._on_switch_playlist())
        tb.Button(self.sidebar, text="+ New", bootstyle=SUCCESS, command=self._new_playlist).pack(fill="x", pady=3)
        tb.Button(self.sidebar, text="Rename", bootstyle=SECONDARY, command=self._rename_playlist).pack(fill="x", pady=3)
        tb.Button(self.sidebar, text="Delete", bootstyle=WARNING, command=self._delete_playlist).pack(fill="x", pady=3)

        # Content
        self.content = tb.Frame(self.main_area, padding=8)
        self.content.pack(side="left", fill="both", expand=True)
        self.current_label = tb.Label(self.content, text=self._current_name() or "No playlist", font=("Segoe UI", 18))
        self.current_label.pack(anchor="w", pady=(0, 8))

        # Song list
        list_frame = tb.Frame(self.content)
        list_frame.pack(fill="both", expand=True)
        self.song_listbox = tk.Listbox(list_frame, font=("Segoe UI", 12))
        self.song_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = tb.Scrollbar(list_frame, orient="vertical", command=self.song_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.song_listbox.config(yscrollcommand=scrollbar.set)

        # Controls
        controls = tb.Frame(self.content, padding=8)
        controls.pack(fill="x")
        tb.Button(controls, text="Import from songs/", bootstyle=SUCCESS, command=self._import_all_from_songs).pack(side="left", padx=5)
        tb.Button(controls, text="Add Song", bootstyle=PRIMARY, command=self._add_song).pack(side="left", padx=5)
        tb.Button(controls, text="Delete Song", bootstyle=WARNING, command=self._delete_song).pack(side="left", padx=5)
        tb.Button(controls, text="Search", bootstyle=INFO, command=self._search_song).pack(side="left", padx=5)

        # Playback
        playback = tb.Frame(self.content, padding=8)
        playback.pack(fill="x", pady=(6, 0))
        tb.Button(playback, text="Play", bootstyle=SUCCESS, command=self._play_selected).pack(side="left", padx=5)
        tb.Button(playback, text="Pause", bootstyle=SECONDARY, command=self.player.pause).pack(side="left", padx=5)
        tb.Button(playback, text="Resume", bootstyle=INFO, command=self.player.resume).pack(side="left", padx=5)
        tb.Button(playback, text="Stop", bootstyle=DANGER, command=self.player.stop).pack(side="left", padx=5)
        tb.Button(playback, text="◀ Prev", bootstyle=SECONDARY, command=self._prev_song).pack(side="left", padx=5)
        tb.Button(playback, text="Next ▶", bootstyle=SECONDARY, command=self._next_song).pack(side="left", padx=5)

        # Status
        self.status = tb.Label(self.root, text="Ready", anchor="w")
        self.canvas.create_window(20, self.root.winfo_screenheight() - 40, anchor="nw", window=self.status)

    # ===== Playlist management =====
    def _refresh_sidebar(self):
        self.playlist_listbox.delete(0, tk.END)
        for name in self.pm.get_all_names():
            self.playlist_listbox.insert(tk.END, name)
        current = self._current_name()
        if current:
            for i in range(self.playlist_listbox.size()):
                if self.playlist_listbox.get(i) == current:
                    self.playlist_listbox.selection_clear(0, tk.END)
                    self.playlist_listbox.selection_set(i)
                    self.playlist_listbox.see(i)
                    break

    def _new_playlist(self):
        name = simpledialog.askstring("New Playlist", "Enter playlist name:")
        if not name:
            return
        if self.pm.create_playlist(name):
            self.db_save(self.pm)
            self._refresh_sidebar()
            self._refresh_song_list()
        else:
            messagebox.showerror("Error", "Invalid or duplicate playlist name.")

    def _rename_playlist(self):
        old = self._current_name()
        if not old:
            messagebox.showinfo("Info", "No playlist selected.")
            return
        new = simpledialog.askstring("Rename Playlist", f"Rename '{old}' to:")
        if not new:
            return
        if self.pm.rename_playlist(old, new):
            self.db_save(self.pm)
            self._refresh_sidebar()
            self._refresh_song_list()
        else:
            messagebox.showerror("Error", "Invalid name or already exists.")

    def _delete_playlist(self):
        name = self._current_name()
        if not name:
            messagebox.showinfo("Info", "No playlist selected.")
            return
        if not messagebox.askyesno("Confirm", f"Delete playlist '{name}'?"):
            return
        if self.pm.delete_playlist(name):
            self.db_save(self.pm)
            self._refresh_sidebar()
            self._refresh_song_list()
            self.current_label.config(text="No playlist")
            self.status.config(text="Playlist deleted")
        else:
            messagebox.showerror("Error", "Could not delete playlist.")

    def _on_switch_playlist(self):
        idxs = self.playlist_listbox.curselection()
        if not idxs:
            return
        name = self.playlist_listbox.get(idxs[0])
        if self.pm.switch_playlist(name):
            self._refresh_song_list()

    # ===== Song management =====
        # ===== Song management =====
    def _refresh_song_list(self):
        self.song_listbox.delete(0, tk.END)
        pl = self.pm.current
        self.current_label.config(text=self._current_name() or "No playlist")
        if not pl:
            self.status.config(text="No playlist selected")
            return
        for item in pl.to_list():
            self.song_listbox.insert(tk.END, item["title"])
        self.status.config(text=f"{pl.length} song(s) in '{pl.name}'")

    def _add_song(self):
        pl = self.pm.current
        if not pl:
            messagebox.showinfo("Info", "Create or select a playlist first.")
            return
        path = filedialog.askopenfilename(
            initialdir=SONGS_DIR,
            filetypes=[("Audio files", "*.mp3 *.wav *.ogg *.flac *.aac *.m4a")]
        )
        if not path:
            return
        if not is_audio_file(path):
            messagebox.showerror("Error", "Selected file is not a supported audio format.")
            return
        title = pretty_title(os.path.basename(path))
        pl.add_song(title, path)
        self._refresh_song_list()
        self.db_save(self.pm)

    def _delete_song(self):
        pl = self.pm.current
        if not pl:
            return
        idxs = self.song_listbox.curselection()
        if not idxs:
            messagebox.showinfo("Info", "Select a song to delete.")
            return
        title = self.song_listbox.get(idxs[0])
        if pl.delete_song(title):
            self._refresh_song_list()
            self.db_save(self.pm)
            if self.player.current_path:
                current_name = os.path.basename(self.player.current_path)
                if pretty_title(os.path.splitext(current_name)[0]) == title:
                    self.player.stop()
                    self.status.config(text="Stopped (song deleted)")
        else:
            messagebox.showerror("Error", f"Could not delete song '{title}'.")

    def _play_selected(self):
        pl = self.pm.current
        if not pl:
            return
        idxs = self.song_listbox.curselection()
        if not idxs:
            messagebox.showinfo("Info", "Select a song to play.")
            return
        title = self.song_listbox.get(idxs[0])
        node = pl.search_song(title)
        if node:
            self.player.play(node.filepath)
            self.status.config(text=f"Playing: {title}")

    def _search_song(self):
        pl = self.pm.current
        if not pl:
            return
        q = simpledialog.askstring("Search", "Enter song title:")
        if not q:
            return
        for i in range(self.song_listbox.size()):
            if q.lower() in self.song_listbox.get(i).lower():
                self.song_listbox.selection_clear(0, tk.END)
                self.song_listbox.selection_set(i)
                self.song_listbox.see(i)
                self.status.config(text=f"Found: {self.song_listbox.get(i)}")
                return
        messagebox.showinfo("Info", "No match found.")

    def _import_all_from_songs(self):
        pl = self.pm.current
        if not pl:
            messagebox.showinfo("Info", "Create or select a playlist first.")
            return
        added = 0
        for name in sorted(os.listdir(SONGS_DIR)):
            path = os.path.join(SONGS_DIR, name)
            if os.path.isfile(path) and is_audio_file(path):
                title = pretty_title(name)
                if not pl.search_song(title):
                    pl.add_song(title, path)
                    added += 1
        if added > 0:
            self.db_save(self.pm)
            self._refresh_song_list()
            messagebox.showinfo("Import", f"Imported {added} song(s) into '{pl.name}'")
        else:
            messagebox.showinfo("Import", "No new audio files found or all already added.")

    # ===== Playback helpers =====
    def _get_selected_index(self):
        sel = self.song_listbox.curselection()
        return sel[0] if sel else None

    def _select_and_play_by_index(self, index: int):
        if index < 0 or index >= self.song_listbox.size():
            return
        self.song_listbox.selection_clear(0, tk.END)
        self.song_listbox.selection_set(index)
        self.song_listbox.see(index)
        title = self.song_listbox.get(index)
        pl = self.pm.current
        if not pl:
            return
        node = pl.search_song(title)
        if node:
            self.player.play(node.filepath)
            self.status.config(text=f"Playing: {title}")

    def _next_song(self):
        idx = self._get_selected_index()
        if idx is None:
            if self.song_listbox.size() > 0:
                self._select_and_play_by_index(0)
            return
        next_idx = idx + 1
        if next_idx < self.song_listbox.size():
            self._select_and_play_by_index(next_idx)
        else:
            self.status.config(text="End of playlist")

    def _prev_song(self):
        idx = self._get_selected_index()
        if idx is None:
            size = self.song_listbox.size()
            if size > 0:
                self._select_and_play_by_index(size - 1)
            return
        prev_idx = idx - 1
        if prev_idx >= 0:
            self._select_and_play_by_index(prev_idx)
        else:
            self.status.config(text="Start of playlist")

    def _current_name(self):
        return self.pm.current.name if self.pm.current else None

    def on_exit(self):
        try:
            self.db_save(self.pm)
        except Exception:
            pass
        try:
            if self.player:
                self.player.stop()
        except Exception:
            pass
        self.root.destroy()
