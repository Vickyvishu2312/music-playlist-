import pygame

class MusicPlayer:
    def __init__(self):
        pygame.mixer.init()
        self.current_path = None

    def play(self, path: str):
        self.stop()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        self.current_path = path

    def pause(self):
        pygame.mixer.music.pause()

    def resume(self):
        pygame.mixer.music.unpause()

    def stop(self):
        pygame.mixer.music.stop()
        self.current_path = None

    def is_playing(self) -> bool:
        return pygame.mixer.music.get_busy()
