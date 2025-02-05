import pygame
import subprocess
import sys
import time

from ..screen_manager import Screen
from ..constants import GREEN, RED, BLUE
from ..utils import log, show_message

class EnterTimezoneScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.zones = self.build_zones()
        self.selected_zone_index = 0
        if self.zones:
            self.zones[self.selected_zone_index]["hovered"] = True

        self.click_sound = None
        self.hover_sound = None
        self.load_sounds()

        self.placeholder_images = []
        self.define_placeholder_images()

    def load_sounds(self):
        try:
            click_path = self.app.get_path("sounds","select.ogg")
            hover_path = self.app.get_path("sounds","hover.ogg")
            self.click_sound = pygame.mixer.Sound(click_path)
            self.click_sound.set_volume(0.5)
            self.hover_sound = pygame.mixer.Sound(hover_path)
            self.hover_sound.set_volume(0.1)
        except Exception as e:
            log(f"Failed to load EnterTimezoneScreen sounds: {e}")
            self.click_sound = None
            self.hover_sound = None

    def define_placeholder_images(self):
        configs = [
            {
                "path": "choose_timezone.png",
                "size": (822,239),
                "pos": (
                    self.app.bubble_rect.left + 1419//2 - 411,
                    self.app.bubble_rect.top + 100,
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
                "path": "page_indicator_2.png",
                "size": (212,18),
                "pos": (
                    self.app.bubble_rect.left + 1419//2 - 106,
                    self.app.bubble_rect.top + 880,
                ),
            },
        ]
        for cfg in configs:
            try:
                ip = self.app.get_path("images", cfg["path"])
                img = pygame.image.load(ip).convert_alpha()
                img = pygame.transform.scale(img, cfg["size"])
            except Exception as e:
                log(f"Failed to load image {cfg['path']}: {e}")
                img = pygame.Surface(cfg["size"])
                img.fill(BLUE)
            self.placeholder_images.append({"img": img, "pos": cfg["pos"]})

    def build_zones(self):
        data = [
            {
                "name": "Pacific",
                "tz": "America/Los_Angeles",
                "map_img": "map_western.png",
                "map_size": (272, 150),
                "btn_norm": "western_normal_lg.png",
                "btn_hov": "western_hover_lg.png",
            },
            {
                "name": "Mountain",
                "tz": "America/Denver",
                "map_img": "map_mountain.png",
                "map_size": (272, 150),
                "btn_norm": "mountain_normal_lg.png",
                "btn_hov": "mountain_hover_lg.png",
            },
            {
                "name": "Central",
                "tz": "America/Chicago",
                "map_img": "map_central.png",
                "map_size": (272, 150),
                "btn_norm": "central_normal_lg.png",
                "btn_hov": "central_hover_lg.png",
            },
            {
                "name": "Eastern",
                "tz": "America/New_York",
                "map_img": "map_eastern.png",
                "map_size": (272, 150),
                "btn_norm": "eastern_normal_lg.png",
                "btn_hov": "eastern_hover_lg.png",
            },
        ]
        map_x_positions = [85,411,737,1063]
        map_y = 420
        gap = 30

        zones = []
        for i,d in enumerate(data):
            try:
                mp = self.app.get_path("images", d["map_img"])
                map_surf = pygame.image.load(mp).convert_alpha()
                map_surf = pygame.transform.scale(map_surf, d["map_size"])
            except Exception as e:
                log(f"Failed to load map image {d['map_img']}: {e}")
                map_surf = pygame.Surface(d["map_size"])
                map_surf.fill(BLUE)

            ax_map = self.app.bubble_rect.left + map_x_positions[i]
            ay_map = self.app.bubble_rect.top + map_y

            try:
                bn_path = self.app.get_path("images", d["btn_norm"])
                bn = pygame.image.load(bn_path).convert_alpha()
                bh_path = self.app.get_path("images", d["btn_hov"])
                bh = pygame.image.load(bh_path).convert_alpha()
            except Exception as e:
                log(f"Failed to load button images for {d['name']}: {e}")
                bn = pygame.Surface((222,55))
                bn.fill((100,200,100))
                bh = pygame.Surface((222,55))
                bh.fill((200,100,200))

            btn_w = bn.get_width()
            btn_h = bn.get_height()
            map_w = d["map_size"][0]
            ax_btn = ax_map + (map_w//2) - (btn_w//2)
            ay_btn = ay_map + d["map_size"][1] + gap

            zones.append({
                "name": d["name"],
                "tz": d["tz"],
                "map_surf": map_surf,
                "map_x": ax_map,
                "map_y": ay_map,
                "btn_norm": bn,
                "btn_hov": bh,
                "btn_rect": pygame.Rect(ax_btn, ay_btn, btn_w, btn_h),
                "hovered": False,
            })
        return zones

    def handle_events(self, events):
        super().handle_events(events)
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx,my = e.pos
                for idx,zone in enumerate(self.zones):
                    if zone["btn_rect"].collidepoint(mx,my):
                        self.set_timezone(zone["tz"])
                        return

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_LEFT:
                    self.move_selection(-1)
                elif e.key == pygame.K_RIGHT:
                    self.move_selection(1)
                elif e.key == pygame.K_RETURN:
                    zone = self.zones[self.selected_zone_index]
                    self.set_timezone(zone["tz"])

            elif e.type == pygame.JOYBUTTONDOWN:
                if e.button == 0:
                    zone = self.zones[self.selected_zone_index]
                    self.set_timezone(zone["tz"])

    def move_selection(self, direction):
        if self.zones:
            self.zones[self.selected_zone_index]["hovered"] = False
            self.selected_zone_index = (self.selected_zone_index+direction)%len(self.zones)
            self.zones[self.selected_zone_index]["hovered"] = True
            if self.hover_sound:
                self.hover_sound.play()

    def set_timezone(self, timezone):
        log(f"Setting timezone to: {timezone}")
        try:
            subprocess.run(["sudo","timedatectl","set-timezone",timezone], check=True)
            log(f"Timezone set to {timezone}")
            show_message(self.app.display_surf,f"Timezone set to {timezone}", color=GREEN, timeout=2)
            pygame.time.wait(1000)
            self.app.screen_manager.change_screen("terms")
        except subprocess.CalledProcessError as e:
            log(f"Error setting timezone: {e}")
            show_message(self.app.display_surf, f"Error: {e}", color=RED, timeout=3)

    def render(self, surf):
        self.render_background_and_bubble(surf)
        for ph in self.placeholder_images:
            surf.blit(ph["img"], ph["pos"])

        mx,my = pygame.mouse.get_pos()
        for idx, zone in enumerate(self.zones):
            surf.blit(zone["map_surf"], (zone["map_x"],zone["map_y"]))
            hovered = zone["btn_rect"].collidepoint(mx,my) or zone["hovered"]
            current = zone["btn_hov"] if hovered else zone["btn_norm"]
            surf.blit(current, (zone["btn_rect"].x, zone["btn_rect"].y))