import os
import sqlite3
from typing import Dict
from playlist import PlaylistManager
from utils import normalize_path

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "playlist.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
      CREATE TABLE IF NOT EXISTS playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
      )
    """)

    c.execute("""
      CREATE TABLE IF NOT EXISTS songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        filepath TEXT NOT NULL,
        FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
      )
    """)

    conn.commit()
    conn.close()

def _get_playlist_id(conn, name: str) -> int:
    c = conn.cursor()
    c.execute("SELECT id FROM playlists WHERE name = ?", (name,))
    row = c.fetchone()
    if row:
        return row[0]
    c.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
    conn.commit()
    return c.lastrowid

def save_all_playlists(pm: PlaylistManager):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Get existing playlists from DB
    c.execute("SELECT name FROM playlists")
    existing_names = {row[0] for row in c.fetchall()}

    current_names = set(pm.get_all_names())

    # ✅ Delete playlists that no longer exist in memory
    for name in existing_names - current_names:
        c.execute("DELETE FROM playlists WHERE name = ?", (name,))

    # Ensure all playlists exist in table and get ids
    name_to_id: Dict[str, int] = {}
    for name in pm.get_all_names():
        pid = _get_playlist_id(conn, name)
        name_to_id[name] = pid

    # Clear songs for each playlist and re-insert
    for name, pl in pm.playlists.items():
        pid = name_to_id[name]
        c.execute("DELETE FROM songs WHERE playlist_id = ?", (pid,))
        for item in pl.to_list():
            c.execute(
                "INSERT INTO songs (playlist_id, title, filepath) VALUES (?, ?, ?)",
                (pid, item["title"], normalize_path(item["filepath"]))
            )

    conn.commit()
    conn.close()

def load_all_playlists() -> PlaylistManager:
    init_db()
    pm = PlaylistManager()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id, name FROM playlists ORDER BY name ASC")
    rows = c.fetchall()

    # If no playlists, create a default one
    if not rows:
        pm.create_playlist("My Playlist")
        conn.close()
        return pm

    id_to_name = {}
    for pid, name in rows:
        pm.create_playlist(name)
        id_to_name[pid] = name

    # Load songs per playlist
    c.execute("SELECT playlist_id, title, filepath FROM songs ORDER BY id ASC")
    for pid, title, path in c.fetchall():
        name = id_to_name.get(pid)
        if name and name in pm.playlists:
            pm.playlists[name].add_song(title, path)

    # Set current playlist to first alphabetically
    names = pm.get_all_names()
    if names:
        pm.switch_playlist(names[0])

    conn.close()
    return pm
