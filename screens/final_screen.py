import pygame
import time
import sys

from ..screen_manager import Screen
from ..constants import PHYSICAL_WIDTH, PHYSICAL_HEIGHT
from ..utils import log

class FinalScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.placeholder_images = self.define_placeholder_images()
        self.font = self.app.font_NES_24
        self.final_message="Setup Complete!\nYour system will reboot."
        self.start_time=None
        self.done_action=False

    def define_placeholder_images(self):
        configs = [
            {
                "path": "setup_complete.png",
                "size": (500,165),
                "pos": (
                    self.app.bubble_rect.centerx-250,
                    self.app.bubble_rect.top+60,
                ),
            },
            {
                "path": "navigation_legend.png",
                "size": (896,56),
                "pos": (
                    self.app.bubble_rect.centerx-448,
                    self.app.bubble_rect.top+740,
                ),
            },
            {
                "path": "page_indicator_final.png",
                "size": (212,18),
                "pos": (
                    self.app.bubble_rect.centerx-106,
                    self.app.bubble_rect.top+880,
                ),
            },
        ]
        result=[]
        for cfg in configs:
            try:
                ip = self.app.get_path("images", cfg["path"])
                img = pygame.image.load(ip).convert_alpha()
                img = pygame.transform.scale(img, cfg["size"])
            except Exception as e:
                log(f"Failed to load image {cfg['path']}: {e}")
                img = pygame.Surface(cfg["size"])
                img.fill((0,0,255))
            result.append({"img": img, "pos": cfg["pos"]})
        return result

    def handle_events(self, events):
        super().handle_events(events)
        for e in events:
            if e.type in [pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN, pygame.JOYBUTTONDOWN]:
                self.finalize()

    def update(self):
        if self.start_time is None:
            self.start_time = pygame.time.get_ticks()

        if not self.done_action:
            elapsed = (pygame.time.get_ticks()-self.start_time)/1000.0
            if elapsed>5:
                self.done_action=True
                self.finalize()

    def finalize(self):
        
        import os, shutil
        try:
            splash_src = "/home/pi/RetroPie/custom_scripts/arcade_wizard/splashscreen/simple_arcades_intro.mp4"
            splash_dst = "/home/pi/RetroPie/splashscreens/simple_arcades_intro.mp4"
            shutil.move(splash_src, splash_dst)
            log(f"Moved {splash_src} -> {splash_dst}")
        except Exception as e:
            log(f"Failed to move splash video: {e}")        
        
        log("Final screen finalize: removing wizard from autostart and rebooting.")
        self.app.remove_wizard_from_autostart()
        self.app.create_setup_flag()
        self.app.reboot_system()

    def render(self, surf):
        self.render_background_and_bubble(surf)
        for ph in self.placeholder_images:
            surf.blit(ph["img"], ph["pos"])

        lines = self.final_message.split("\n")
        y = self.app.bubble_rect.centery
        for line in lines:
            txt = self.font.render(line,True,(0,200,0))
            rect = txt.get_rect(center=(PHYSICAL_WIDTH//2, y))
            surf.blit(txt, rect)
            y+=60
