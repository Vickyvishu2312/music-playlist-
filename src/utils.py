import os

AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"}

def is_audio_file(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in AUDIO_EXTS

def pretty_title(filename: str) -> str:
    name, _ = os.path.splitext(filename)
    return " ".join(name.replace("-", " ").replace("_", " ").split())

def normalize_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))
