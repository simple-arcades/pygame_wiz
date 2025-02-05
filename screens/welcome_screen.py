import pygame
import sys

from ..screen_manager import Screen
from ..constants import GREEN, YELLOW, RED, BLUE
from ..utils import log

class WelcomeScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.next_button_rect = pygame.Rect(
            app.bubble_rect.centerx - 220,
            app.bubble_rect.centery + 150,
            441,
            107,
        )
        self.next_button_selected = False
        self.next_button_hovered = False

        self.load_buttons()
        self.load_sounds()
        self.placeholder_images = self.define_placeholder_images()

    def load_buttons(self):
        # Using get_path to find images inside arcade_wizard/images/
        try:
            n_path = self.app.get_path("images","continue_normal_lg.png")
            h_path = self.app.get_path("images","continue_hover_lg.png")
            p_path = self.app.get_path("images","continue_pressed_lg.png")
            n = pygame.image.load(n_path).convert_alpha()
            h = pygame.image.load(h_path).convert_alpha()
            p = pygame.image.load(p_path).convert_alpha()
        except Exception as e:
            log(f"Failed to load WelcomeScreen buttons: {e}")
            n = pygame.Surface((441,107))
            n.fill(GREEN)
            h = pygame.Surface((441,107))
            h.fill(YELLOW)
            p = pygame.Surface((441,107))
            p.fill(RED)
        self.next_normal, self.next_hover, self.next_pressed = n, h, p

    def load_sounds(self):
        try:
            click_path = self.app.get_path("sounds","select.ogg")
            hover_path = self.app.get_path("sounds","hover.ogg")
            self.button_click_sound = pygame.mixer.Sound(click_path)
            self.button_click_sound.set_volume(0.5)
            self.button_hover_sound = pygame.mixer.Sound(hover_path)
            self.button_hover_sound.set_volume(0.1)
        except Exception as e:
            log(f"Failed to load WelcomeScreen sounds: {e}")
            self.button_click_sound = None
            self.button_hover_sound = None

    def define_placeholder_images(self):
        configs = [
            {
                "path": "welcome_arcade.png",
                "size": (1058,324),
                "pos": (
                    self.app.bubble_rect.left + 1419//2 - 529,
                    self.app.bubble_rect.top + 100,
                ),
            },
            {
                "path": "get_started.png",
                "size": (324,18),
                "pos": (
                    self.app.bubble_rect.left + 1419//2 - 162,
                    self.app.bubble_rect.top + 500,
                ),
            },
            {
                "path": "navigation_legend.png",
                "size": (896,56),
                "pos": (
                    self.app.bubble_rect.left + 1419//2 - 448,
                    self.app.bubble_rect.top + 740,
                ),
            },
            {
                "path": "page_indicator_1.png",
                "size": (212,18),
                "pos": (
                    self.app.bubble_rect.left + 1419//2 - 106,
                    self.app.bubble_rect.top + 880,
                ),
            }
        ]
        result = []
        for cfg in configs:
            try:
                img_path = self.app.get_path("images", cfg["path"])
                img = pygame.image.load(img_path).convert_alpha()
                img = pygame.transform.scale(img, cfg["size"])
            except Exception as e:
                log(f"Failed to load image {cfg['path']}: {e}")
                img = pygame.Surface(cfg["size"])
                img.fill(BLUE)
            result.append({"img": img, "pos": cfg["pos"]})
        return result

    def handle_events(self, events):
        super().handle_events(events)
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx,my = e.pos
                if self.next_button_rect.collidepoint(mx,my):
                    if self.button_click_sound:
                        self.button_click_sound.play()
                    self.app.screen_manager.change_screen("timezone")
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN:
                    if self.button_click_sound:
                        self.button_click_sound.play()
                    self.app.screen_manager.change_screen("timezone")
            elif e.type == pygame.JOYBUTTONDOWN:
                if e.button == 0:
                    if self.button_click_sound:
                        self.button_click_sound.play()
                    self.app.screen_manager.change_screen("timezone")
            elif e.type == pygame.JOYAXISMOTION:
                if e.axis == 1:
                    if e.value < -0.5:
                        self.next_button_selected = True
                        if self.button_hover_sound:
                            self.button_hover_sound.play()
                    elif e.value > 0.5:
                        self.next_button_selected = False

    def render(self, surface):
        self.render_background_and_bubble(surface)
        mx,my = pygame.mouse.get_pos()

        if self.next_button_rect.collidepoint(mx,my):
            self.next_button_hovered = True
        else:
            self.next_button_hovered = False

        if self.next_button_selected or self.next_button_hovered:
            if pygame.mouse.get_pressed()[0]:
                current = self.next_pressed
            else:
                current = self.next_hover
        else:
            current = self.next_normal

        surface.blit(current, self.next_button_rect)

        for p in self.placeholder_images:
            surface.blit(p["img"], p["pos"])