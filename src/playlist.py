from typing import Optional, Dict, List

class SongNode:
    def __init__(self, title: str, filepath: str):
        self.title: str = title
        self.filepath: str = filepath
        self.prev: Optional["SongNode"] = None
        self.next: Optional["SongNode"] = None

class Playlist:
    def __init__(self, name: str):
        self.name: str = name
        self.head: Optional[SongNode] = None
        self.tail: Optional[SongNode] = None
        self.length: int = 0

    def add_song(self, title: str, filepath: str):
        node = SongNode(title, filepath)
        if not self.head:
            self.head = self.tail = node
        else:
            assert self.tail is not None
            self.tail.next = node
            node.prev = self.tail
            self.tail = node
        self.length += 1

    def delete_song(self, title: str) -> bool:
        cur = self.head
        while cur:
            if cur.title == title:
                if cur.prev:
                    cur.prev.next = cur.next
                else:
                    self.head = cur.next
                if cur.next:
                    cur.next.prev = cur.prev
                else:
                    self.tail = cur.prev
                self.length -= 1
                return True
            cur = cur.next
        return False

    def search_song(self, title: str) -> Optional[SongNode]:
        cur = self.head
        while cur:
            if cur.title == title:
                return cur
            cur = cur.next
        return None

    def to_list(self) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        cur = self.head
        while cur:
            out.append({"title": cur.title, "filepath": cur.filepath})
            cur = cur.next
        return out

    def clear(self):
        self.head = self.tail = None
        self.length = 0

class PlaylistManager:
    def __init__(self):
        self.playlists: Dict[str, Playlist] = {}
        self.current: Optional[Playlist] = None

    def create_playlist(self, name: str) -> bool:
        name = name.strip()
        if not name:
            return False
        if name in self.playlists:
            return False
        pl = Playlist(name)
        self.playlists[name] = pl
        if self.current is None:
            self.current = pl
        return True

    def delete_playlist(self, name: str) -> bool:
        if name in self.playlists:
            was_current = (self.current and self.current.name == name)
            del self.playlists[name]
            if was_current:
                self.current = None
                # pick another if available
                if self.playlists:
                    first_name = sorted(self.playlists.keys())[0]
                    self.current = self.playlists[first_name]
            return True
        return False

    def switch_playlist(self, name: str) -> bool:
        if name in self.playlists:
            self.current = self.playlists[name]
            return True
        return False

    def rename_playlist(self, old_name: str, new_name: str) -> bool:
        new_name = new_name.strip()
        if not new_name or old_name not in self.playlists or new_name in self.playlists:
            return False
        pl = self.playlists.pop(old_name)
        pl.name = new_name
        self.playlists[new_name] = pl
        if self.current and self.current.name == old_name:
            self.current = pl
        return True

    def get_all_names(self) -> List[str]:
        return sorted(self.playlists.keys())
