import pygame
import subprocess
import threading
import queue
import time
import sys

from ..screen_manager import Screen
from ..constants import WHITE, YELLOW, GREEN, RED, AUTO_UPDATE_SCRIPT, PHYSICAL_WIDTH
from ..utils import log

class UpdateScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.font = self.app.font_NES_24
        self.placeholder_images = self.define_placeholder_images()

        self.status_message = "Checking for updates..."
        self.update_thread = None
        self.message_queue = queue.Queue()
        self.update_complete = False

        self.scan_updates()

    def define_placeholder_images(self):
        configs = [
            {
                "path": "update_screen.png",
                "size": (683,165),
                "pos": (
                    self.app.bubble_rect.centerx-342,
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
                "path": "page_indicator_5.png",
                "size": (212,18),
                "pos": (
                    self.app.bubble_rect.centerx-106,
                    self.app.bubble_rect.top+880,
                ),
            },
        ]
        result = []
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
        if self.update_complete:
            for e in events:
                if e.type in [pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN, pygame.JOYBUTTONDOWN]:
                    self.finish_update_flow()

    def scan_updates(self):
        def worker():
            self.message_queue.put(("info","Looking for updates..."))
            try:
                proc = subprocess.Popen(["sudo", AUTO_UPDATE_SCRIPT],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        text=True)
                for line in proc.stdout:
                    self.message_queue.put(("line", line.rstrip("\n")))
                proc.wait()
                rc = proc.returncode
                self.message_queue.put(("done", rc))
            except Exception as e:
                self.message_queue.put(("error", str(e)))

        self.update_thread = threading.Thread(target=worker, daemon=True)
        self.update_thread.start()

    def update(self):
        while not self.message_queue.empty():
            msg_type, content = self.message_queue.get()
            if msg_type=="info":
                self.status_message = content
            elif msg_type=="line":
                self.status_message = content
                log(f"UpdateScript: {content}")
            elif msg_type=="done":
                rc = content
                if rc==0:
                    self.status_message="Updates applied successfully. Press designated SELECT button to continue."
                else:
                    self.status_message=f"Update script failed (RC={rc})."
                self.update_complete=True
            elif msg_type=="error":
                self.status_message=f"Error: {content}"
                self.update_complete=True

    def finish_update_flow(self):
        self.app.screen_manager.change_screen("final")

    def render(self, surf):
        self.render_background_and_bubble(surf)
        for p in self.placeholder_images:
            surf.blit(p["img"], p["pos"])

        txt = self.font.render(self.status_message, True, BLACK)
        rect = txt.get_rect(center=(PHYSICAL_WIDTH//2, self.app.bubble_rect.centery))
        surf.blit(txt, rect)