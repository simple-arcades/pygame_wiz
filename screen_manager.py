import pygame
import sys

from .constants import PHYSICAL_WIDTH, PHYSICAL_HEIGHT
from .utils import log

class Screen:
    def __init__(self, app):
        self.app = app
        self.font = self.app.font_NES_24

    def handle_events(self, events):
        for e in events:
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # Joystick => synthetic key events
            if self.app.joystick:
                if e.type == pygame.JOYAXISMOTION:
                    if e.axis == 0:
                        if e.value < -0.5:
                            self.handle_key_event(pygame.K_LEFT)
                        elif e.value > 0.5:
                            self.handle_key_event(pygame.K_RIGHT)
                    elif e.axis == 1:
                        if e.value < -0.5:
                            self.handle_key_event(pygame.K_UP)
                        elif e.value > 0.5:
                            self.handle_key_event(pygame.K_DOWN)
                elif e.type == pygame.JOYBUTTONDOWN:
                    if e.button == 0:  # 'A' => Enter
                        self.handle_key_event(pygame.K_RETURN)
                    elif e.button == 1:  # 'B' => Escape
                        self.handle_key_event(pygame.K_ESCAPE)
                    elif e.button == 2:  # 'X' => Tab
                        self.handle_key_event(pygame.K_TAB)

    def handle_key_event(self, key):
        event_down = pygame.event.Event(pygame.KEYDOWN, key=key)
        pygame.event.post(event_down)
        event_up = pygame.event.Event(pygame.KEYUP, key=key)
        pygame.event.post(event_up)

    def update(self):
        pass

    def render(self, surface):
        pass

    def render_background_and_bubble(self, surface):
        surface.blit(self.app.background, (0, 0))
        surface.blit(self.app.bubble_image, self.app.bubble_rect)


class ScreenManager:
    def __init__(self, app):
        self.app = app
        self.screens = {}
        self.active_screen = None

    def register_screen(self, name, screen_instance):
        self.screens[name] = screen_instance

    def change_screen(self, name):
        if name in self.screens:
            log(f"Changing screen to: {name}")
            self.active_screen = self.screens[name]

            # CLEAR the event queue to avoid "double presses"
            pygame.event.clear()
        else:
            log(f"Attempted to change to invalid screen: {name}")

    def handle_events(self, events):
        if self.active_screen:
            self.active_screen.handle_events(events)

    def update(self):
        if self.active_screen:
            self.active_screen.update()

    def render(self, surface):
        if self.active_screen:
            self.active_screen.render(surface)